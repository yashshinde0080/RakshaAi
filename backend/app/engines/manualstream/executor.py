"""True Manual Layer Streaming Prototype Engine"""
import asyncio
import time
import os
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Optional

import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
import psutil

from app.engines.base import BaseEngine

class ManualStreamEngine(BaseEngine):
    """True manual layer-by-layer streaming prototype using PyTorch (like airllm)"""
    
    def __init__(self, model_path: str, hardware: Dict[str, Any], memory_manager: Any):
        super().__init__(model_path, hardware, memory_manager)
        self.mode = "manualstream"
        
        self.tokenizer = None
        self.model = None
        self.config = None
        self.state_dict_path = None
        self.device = "cpu"  # Keep it simple for CPU streaming prototype
        
    async def load(self):
        """Initialize engine skeleton for manual streaming"""
        start_time = time.time()
        
        from accelerate import init_empty_weights
        
        print("Initializing True Manual Layer Stream Prototype...")
        
        # 1. Load config only
        self.config = AutoConfig.from_pretrained(
            self.model_path, 
            trust_remote_code=True,
            local_files_only=True
        )
        
        # 2. Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, 
            trust_remote_code=True,
            local_files_only=True
        )
        
        # 3. Handle model weights path (assume standard HuggingFace format for simple prototype)
        model_dir = Path(self.model_path)
        if (model_dir / "pytorch_model.bin").exists():
            self.state_dict_path = model_dir / "pytorch_model.bin"
        elif (model_dir / "model.safetensors").exists():
            self.state_dict_path = model_dir / "model.safetensors"
        else:
            bins = list(model_dir.rglob("*.bin"))
            sts = list(model_dir.rglob("*.safetensors"))
            if bins:
                self.state_dict_path = bins[0]
            elif sts:
                self.state_dict_path = sts[0]
            else:
                self.state_dict_path = self.model_path
                
        # 4. Load Model Skeleton Without Weights
        with init_empty_weights():
            self.model = AutoModelForCausalLM.from_config(self.config, trust_remote_code=True)
            self.model.eval()
            
        if not self.tokenizer.pad_token:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        self.loaded = True
        self.stats["load_time"] = time.time() - start_time
        print(f"Loaded skeleton for {self.model_path} in Manual LayerStream mode in {self.stats['load_time']:.1f}s")
    
    async def unload(self):
        """Cleanup engine"""
        if self.model:
            del self.model
            self.model = None
            
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
            
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        self.loaded = False
        
    def _layer_stream_forward(self, input_ids: torch.Tensor, past_key_values: Optional[tuple] = None):
        """Manual per-layer forward pass"""
        import gc
        
        # Load state dict lazily
        # Note: Prototype implementation. Assumes single state dict file and Llama-style architecture.
        is_safetensors = str(self.state_dict_path).endswith('.safetensors')
        if is_safetensors:
            from safetensors.torch import load_file
            state_dict = load_file(self.state_dict_path, device="cpu")
        else:
            state_dict = torch.load(self.state_dict_path, map_location="cpu")
            
        # Try to find the inner base model
        base_model_name = getattr(self.config, "model_type", "model")
        base_model = getattr(self.model, base_model_name, self.model.model)
        
        # Load embedding weights
        embed_name = f"{base_model_name}.embed_tokens.weight"
        if embed_name in state_dict:
            base_model.embed_tokens.weight.data = state_dict[embed_name]
        elif "model.embed_tokens.weight" in state_dict:
            base_model.embed_tokens.weight.data = state_dict["model.embed_tokens.weight"]
        
        hidden_states = base_model.embed_tokens(input_ids)
        
        # Unload embed
        base_model.embed_tokens.weight.data = torch.empty(0)
            
        new_past_key_values = []
        
        # Manually iterate over transformer blocks
        for i, layer in enumerate(base_model.layers):
            
            # Load layer weights
            for name, param in layer.named_parameters():
                key1 = f"{base_model_name}.layers.{i}.{name}"
                key2 = f"model.layers.{i}.{name}"
                if key1 in state_dict:
                    param.data = state_dict[key1]
                elif key2 in state_dict:
                    param.data = state_dict[key2]
                
            layer_past = past_key_values[i] if past_key_values is not None else None
            
            # Forward
            with torch.no_grad():
                layer_outputs = layer(
                    hidden_states, 
                    past_key_value=layer_past,
                    use_cache=True
                )
                
            hidden_states = layer_outputs[0]
            new_past_key_values.append(layer_outputs[1])
            
            # Unload layer weights
            for param in layer.parameters():
                param.data = torch.empty(0)
                
        # Final norm and lm_head
        norm_name = f"{base_model_name}.norm.weight"
        if norm_name in state_dict:
            base_model.norm.weight.data = state_dict[norm_name]
        elif "model.norm.weight" in state_dict:
            base_model.norm.weight.data = state_dict["model.norm.weight"]
            
        if "lm_head.weight" in state_dict:
            self.model.lm_head.weight.data = state_dict["lm_head.weight"]
            
        hidden_states = base_model.norm(hidden_states)
        logits = self.model.lm_head(hidden_states)
        
        # Cleanup
        base_model.norm.weight.data = torch.empty(0)
        self.model.lm_head.weight.data = torch.empty(0)
            
        del state_dict
        gc.collect()
        
        return logits, tuple(new_past_key_values)
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """Generate completion via manual layer streaming"""
        if not self.loaded:
            raise RuntimeError("Engine not loaded")
        
        start_time = time.perf_counter()
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"]
        prompt_tokens = input_ids.shape[1]
        
        generated_ids = []
        past_key_values = None
        eos_id = self.tokenizer.eos_token_id  # may be None for some tokenizers
        
        def _generate_loop():
            nonlocal input_ids, past_key_values
            
            for index in range(max_tokens):
                print(f"Generating token {index + 1}/{max_tokens}...")
                with torch.no_grad():
                    logits, past_key_values = self._layer_stream_forward(input_ids, past_key_values)
                
                # Get next token from logits
                next_token_logits = logits[:, -1, :]
                
                if temperature > 0:
                    next_token_logits = next_token_logits / temperature
                    probs = torch.softmax(next_token_logits, dim=-1)
                    next_token = torch.multinomial(probs, num_samples=1)
                else:
                    next_token = torch.argmax(next_token_logits, dim=-1).unsqueeze(0)
                    
                generated_ids.append(next_token.item())
                input_ids = next_token # Pass only the newly generated token
                
                if eos_id is not None and next_token.item() == eos_id:
                    break
                    
            return generated_ids
            
        output_ids = await asyncio.to_thread(_generate_loop)
        
        output_text = self.tokenizer.decode(output_ids, skip_special_tokens=True)
        completion_tokens = len(output_ids)
        elapsed = time.perf_counter() - start_time
        
        return {
            "text": output_text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "time_seconds": elapsed,
            "tokens_per_second": completion_tokens / elapsed if elapsed > 0 else 0,
            "finish_reason": "stop"
        }
        
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Not efficiently supported for manual streaming prototype without extreme complexity. Fallback to basic generation."""
        # This is a prototype so we just yield the final result simulating a stream.
        res = await self.generate(prompt, max_tokens, temperature, top_p)
        yield {
            "token": res["text"],
            "finish_reason": "stop"
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        process = psutil.Process()
        return {
            "ram_used_gb": process.memory_info().rss / (1024**3),
            "kv_cache_mb": 0
        }
