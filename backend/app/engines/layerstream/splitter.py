import os
import gc
import json
import torch
from transformers import AutoModelForCausalLM
from safetensors.torch import save_file

from .introspection import ModelIntrospector
from .quant_config import QuantConfig


def _quantize_int8(state_dict: dict) -> dict:
    """Per-tensor symmetric INT8 quantization. Returns quantized + scale tensors."""
    quantized = {}
    for key, tensor in state_dict.items():
        if tensor.dtype in (torch.float16, torch.float32, torch.bfloat16):
            scale = tensor.abs().max() / 127.0
            if scale < 1e-10:
                quantized[key] = tensor.to(torch.int8)
            else:
                quantized[key] = torch.clamp(
                    torch.round(tensor / scale), -128, 127
                ).to(torch.int8)
            quantized[f"{key}.scale"] = scale.view(1).to(torch.float32)
        else:
            quantized[key] = tensor
            scale_key = f"{key}.scale"
            if scale_key in state_dict:
                quantized[scale_key] = state_dict[scale_key]
    return quantized


class WeightSplitter:
    def __init__(self, model_id: str, output_dir: str = "layers", quant_method: str = "none"):
        self.model_id = model_id
        self.output_dir = output_dir
        self.quant_method = quant_method
        os.makedirs(output_dir, exist_ok=True)

    def split_and_save(self, dtype=torch.float16):
        """
        Loads the full model into CPU RAM precisely once and saves the core components
        into separate safetensors files.
        """
        print(f"Loading full model '{self.model_id}' to CPU for splitting...")
        # Load full model to CPU
        kwargs = {
            "device_map": "cpu",
            "dtype": dtype,
            "low_cpu_mem_usage": True,
            "trust_remote_code": True,
            "ignore_mismatched_sizes": True
        }

        
        if str(self.model_id).endswith(".gguf") or str(self.model_id).endswith(".gguf.enc"):
            model_dir = os.path.dirname(self.model_id)
            kwargs["gguf_file"] = os.path.basename(self.model_id)
            model = AutoModelForCausalLM.from_pretrained(model_dir, **kwargs)
        else:
            # torch < 2.6 refuses .bin checkpoints (CVE-2025-32434); convert to safetensors first
            from app.engines.shared.safetensors import ensure_safetensors
            ensure_safetensors(self.model_id)
            model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)
        
        components = ModelIntrospector.detect_model_components(model)

        quant_method = self.quant_method
        # Only int8 is currently implemented; others need dedicated quant/dequant kernels
        if quant_method not in ("none", "int8"):
            raise ValueError(
                f"quant_method '{quant_method}' not yet implemented. "
                f"Available: none, int8"
            )
        quant_cfg = QuantConfig(quant_method=quant_method, bits=8 if quant_method == "int8" else 16)
        quant_cfg.save(os.path.join(self.output_dir, "quant_config.json"))

        def _maybe_quant(sd):
            return _quantize_int8(sd) if quant_method == "int8" else sd

        print("Saving embed...")
        save_file(_maybe_quant(components['embed'].state_dict()), os.path.join(self.output_dir, "embed.safetensors"))
        
        print(f"Saving {len(components['layers'])} layers...")
        for i, layer in enumerate(components['layers']):
            save_file(_maybe_quant(layer.state_dict()), os.path.join(self.output_dir, f"layer_{i}.safetensors"))

        if components['norm'] is not None:
            print("Saving final norm...")
            save_file(_maybe_quant(components['norm'].state_dict()), os.path.join(self.output_dir, "norm.safetensors"))

        print("Saving lm_head...")
        save_file(_maybe_quant(components['lm_head'].state_dict()), os.path.join(self.output_dir, "lm_head.safetensors"))
        
        # Save config
        model.config.save_pretrained(self.output_dir)
        
        # Copy tokenizer if it exists in source dir
        import shutil
        tokenizer_files = [
            "tokenizer.json", "tokenizer_config.json", "vocab.json", 
            "merges.txt", "special_tokens_map.json", "added_tokens.json",
            "tokenizer.model"
        ]
        
        source_dir = self.model_id
        if os.path.isfile(source_dir):
            source_dir = os.path.dirname(source_dir)
            
        for tf in tokenizer_files:
            src = os.path.join(source_dir, tf)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(self.output_dir, tf))
        
        # Clean up full model from RAM
        del model
        gc.collect()
        print(f"Splitting complete. Files saved to {self.output_dir}/")
