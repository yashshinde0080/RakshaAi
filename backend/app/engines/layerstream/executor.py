"""LayerStream Execution Engine - TRUE Memory-Bounded Layer-by-Layer inference"""
import asyncio
import time
import os
import gc
from typing import Dict, Any, AsyncGenerator, Optional

import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
from accelerate import init_empty_weights

from app.engines.base import BaseEngine
from .introspection import ModelIntrospector
from .splitter import WeightSplitter
from .layer_executor import LayerExecutor
from .sampler import Sampler

_STREAM_WINDOW = 8  # tokens; BPE subword merges stay local to a few tokens


def _stream_delta(tokenizer, all_tokens, emitted, window=_STREAM_WINDOW) -> str:
    """Return the newly decodable text for the latest token.

    ``tokenizer.decode`` of a growing token list is not prefix-stable for BPE
    tokenizers: a space/subword can be absorbed into a merge once more tokens
    arrive (e.g. "\u2581wor" + "ld" -> " world"), so ``full[len(prev):]`` slicing
    can drop or duplicate deltas. Instead decode a rolling window (merges stay
    inside it) and strip the already-emitted text via longest-overlap matching.
    """
    recent = tokenizer.decode(all_tokens[-window:], skip_special_tokens=True)
    if not emitted:
        return recent
    limit = min(len(recent), len(emitted))
    # Cap the overlap at the decode length of the window's earlier tokens: the
    # newest token's text can only be a suffix of ``emitted`` by coincidence
    # (repeated words like "yes yes yes" emit identical pieces), so absorbing
    # it would silently drop the delta. Earlier-token text is always emitted.
    earlier = tokenizer.decode(all_tokens[-window:-1], skip_special_tokens=True)
    limit = min(limit, len(earlier))
    # Overlap can never exceed len(recent); match against the emitted tail only
    # so per-token cost stays O(window), not O(len(emitted)).
    tail = emitted[-limit:]
    overlap = 0
    for i in range(1, limit + 1):
        # Full scan, no early break: ``endswith`` is NOT monotone in ``i`` (e.g.
        # recent = ", won't, can't, I" matches emitted's tail only at i=1 and
        # i=10), so breaking at the first miss under-reports the overlap and
        # re-emits already-sent text. Keep the true maximum instead.
        if tail.endswith(recent[:i]):
            overlap = i
    if overlap:
        return recent[overlap:]
    # No stable overlap (e.g. byte-fallback rewrites): emit just the newest
    # token rather than re-emitting the whole window.
    new_text = tokenizer.decode(all_tokens[-1:], skip_special_tokens=True)
    return new_text if new_text and not emitted.endswith(new_text) else ""

class LayerStreamEngine(BaseEngine):
    """Refactored streaming engine: completely decoupling computation phases dynamically"""
    
    def __init__(self, model_path: str, hardware: Dict[str, Any], memory_manager: Any, quant_method: str = "none",
                 turboquant_config: Any = None):
        super().__init__(model_path, hardware, memory_manager)
        self.mode = "layerstream"
        self.quant_method = quant_method
        self.turboquant_config = turboquant_config

        self.tokenizer = None
        self.model = None
        self.config = None
        self.components = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.weights_dir = ""
        self.layer_executor = None

    async def load(self):
        """Prepare meta scaffolding"""
        start_time = time.time()
        
        from app.config import settings
        self.weights_dir = os.path.join(str(settings.workspace_dir / "offload_cache"), os.path.basename(self.model_path.rstrip("/\\")))
        os.makedirs(self.weights_dir, exist_ok=True)
        
        if not os.path.exists(os.path.join(self.weights_dir, "embed.safetensors")):
            print(f"Components absents. Synchronizing AutoSplitter logic on cpu...")
            splitter = WeightSplitter(self.model_path, self.weights_dir, quant_method=self.quant_method)
            await asyncio.to_thread(splitter.split_and_save, torch.float16)
        else:
            # Maybe it was split but tokenizer wasn't copied (old version)
            # Try to copy if they exist in source
            tokenizer_files = ["tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"]
            missing = [f for f in tokenizer_files if not os.path.exists(os.path.join(self.weights_dir, f))]
            if missing:
                source_dir = self.model_path
                if os.path.isfile(source_dir): source_dir = os.path.dirname(source_dir)
                import shutil
                for tf in tokenizer_files:
                    src = os.path.join(source_dir, tf)
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(self.weights_dir, tf))

        try:
            tok_kwargs = {
                "trust_remote_code": True,
                "local_files_only": True
            }
            # Try loading from weights_dir first (preferred for split models)
            if os.path.exists(os.path.join(self.weights_dir, "tokenizer_config.json")):
                tok_dir = self.weights_dir
            elif self.model_path.endswith(".gguf") or self.model_path.endswith(".gguf.enc"):
                tok_kwargs["gguf_file"] = os.path.basename(self.model_path)
                tok_dir = os.path.dirname(self.model_path)
            else:
                tok_dir = self.model_path
            
            self.tokenizer = AutoTokenizer.from_pretrained(tok_dir, **tok_kwargs)
        except Exception:
            # Fallback to source
            tok_kwargs.pop("local_files_only", None)
            if self.model_path.endswith(".gguf") or self.model_path.endswith(".gguf.enc"):
                tok_dir = os.path.dirname(self.model_path)
            else:
                tok_dir = self.model_path
            self.tokenizer = AutoTokenizer.from_pretrained(tok_dir, **tok_kwargs)
            
        if not self.tokenizer.pad_token:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        self.config = AutoConfig.from_pretrained(self.weights_dir, trust_remote_code=True)
        # Force eager attention to simplify manual layer execution in modern transformers
        self.config._attn_implementation = "eager"
        
        # For LayerStream, we need the text config for things like max_position_embeddings
        # Multimodal models nest text params under text_config
        self.ls_config = self.config
        if hasattr(self.config, "text_config"):
            self.ls_config = self.config.text_config
            self.ls_config._attn_implementation = "eager"
        
        with init_empty_weights():
            # Try AutoModelForCausalLM first (standard text models)
            # Fall back to AutoModel for multimodal/non-standard architectures
            try:
                self.model = AutoModelForCausalLM.from_config(self.config, trust_remote_code=True)
            except Exception:
                from transformers import AutoModel
                self.model = AutoModel.from_config(self.config, trust_remote_code=True)
            
        self.components = ModelIntrospector.detect_model_components(self.model)

        # Determine TurboQuant config: explicit arg > settings > disabled
        tq_config = self.turboquant_config
        if tq_config is None:
            from app.config import settings as sov_settings
            if sov_settings.turboquant_enabled:
                tq_config = {
                    "bits_per_coord": sov_settings.turboquant_bits,
                    "enable_qjl": sov_settings.turboquant_qjl_enabled,
                    "rotation_type": sov_settings.turboquant_rotation,
                }

        # Detect hybrid architecture (e.g. Qwen3.5 linear_attention + full_attention)
        # Check both the full config and text_config — layer_types may live on either
        layer_types = getattr(self.config, 'layer_types', None)
        if layer_types is None:
            layer_types = getattr(self.ls_config, 'layer_types', None)

        self.layer_executor = LayerExecutor(
            self.components, self.ls_config, self.weights_dir, self.device,
            turboquant_config=tq_config, layer_types=layer_types,
        )
        
        self.loaded = True
        self.stats["load_time"] = time.time() - start_time
        print(f"Loaded {self.model_path} LayerStream in {self.stats['load_time']:.1f}s")

    
    async def unload(self):
        """Garbage collection enforcement"""
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        if self.layer_executor:
            self.layer_executor.loader.clear_cache()
            if self.layer_executor._is_hybrid:
                self.layer_executor.cache.clear()
            else:
                self.layer_executor.kv_manager.clear()
            self.layer_executor = None
        self.components = {}
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        self.loaded = False

    async def generate(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Runs the two-phase computation engine independently maintaining context bounds"""
        if not self.loaded:
            raise RuntimeError("Engine not loaded")
            
        start_time = time.perf_counter()
        
        # Extract parameters
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        
        # Protect against async unloading race conditions
        tokenizer = self.tokenizer
        executor = self.layer_executor
        if not tokenizer or not executor:
            raise RuntimeError("Engine dependencies have been unloaded.")
        eos_id = tokenizer.eos_token_id  # may be None for some tokenizers
            
        # Wipe residual memory structures safely
        if executor._is_hybrid:
            executor.cache.clear()
        else:
            executor.kv_manager.clear()
        
        # Support Chat Template
        if isinstance(input_data, list):
            # Assume chat messages
            prompt = tokenizer.apply_chat_template(input_data, tokenize=False, add_generation_prompt=True)
        elif isinstance(input_data, dict) and "messages" in input_data:
            prompt = tokenizer.apply_chat_template(input_data["messages"], tokenize=False, add_generation_prompt=True)
        else:
            prompt = input_data if isinstance(input_data, str) else input_data.get("prompt", "")
            
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)
        prompt_tokens = input_ids.shape[1]
        generated_tokens = []
        
        def _gen_loop():
            with torch.inference_mode():
                # Phase 1: Context Prefill
                # Spools states and layers exclusively across CPU IO
                logits = executor.execute_forward(input_ids, mode="prefill")
                next_token = Sampler.sample(logits, temperature, top_p)
                generated_tokens.append(next_token.item())
                
                # Phase 2: Decoded Token Generation
                # Avoid disk IO exclusively polling RAM tensors onto active layer execution
                current_input = next_token
                for _ in range(max_tokens - 1):
                    if eos_id is not None and next_token.item() == eos_id:
                        break
                        
                    logits = executor.execute_forward(current_input, mode="decode")
                    next_token = Sampler.sample(logits, temperature, top_p)
                    generated_tokens.append(next_token.item())
                    current_input = next_token
                    
            return generated_tokens
            
        output_ids = await asyncio.to_thread(_gen_loop)
        
        output_text = tokenizer.decode(output_ids, skip_special_tokens=True)
        completion_tokens = len(output_ids)
        elapsed = time.perf_counter() - start_time
        
        stats = executor.tracker.get_stats()
        stats["tokens_per_second"] = completion_tokens / elapsed if elapsed > 0 else 0
        self.stats.update(stats)
        
        # Resolve task dynamically for metadata
        from app.core.task_resolver import TaskResolver
        task_info = TaskResolver.resolve(self.model_path)
        
        return {
            "model_name": self.model_path.split("/")[-1] if "/" in self.model_path else self.model_path.split("\\")[-1],
            "task_type": task_info.get("task_type", "causal_lm"),
            "mode": self.mode,
            "input": "provided inputs", 
            "output": output_text,
            "confidence": "1.0000",
            "metadata": {
                "ram_usage": f"{stats['peak_ram_mb'] / 1024:.2f}GB",
                "latency": f"{elapsed:.3f}s",
                "tokens_generated": str(completion_tokens)
            }
        }

    async def generate_stream(self, input_data: Any, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Provides async telemetry while unspooling context cleanly"""
        if not self.loaded:
            raise RuntimeError("Engine not loaded")
            
        tokenizer = self.tokenizer
        executor = self.layer_executor
        if not tokenizer or not executor:
            yield {"token": "", "finish_reason": "error"}
            return
        eos_id = tokenizer.eos_token_id  # may be None for some tokenizers
            
        # Support Chat Template
        if isinstance(input_data, list):
            # Assume chat messages
            prompt = tokenizer.apply_chat_template(input_data, tokenize=False, add_generation_prompt=True)
        elif isinstance(input_data, dict) and "messages" in input_data:
            prompt = tokenizer.apply_chat_template(input_data["messages"], tokenize=False, add_generation_prompt=True)
        else:
            prompt = input_data if isinstance(input_data, str) else input_data.get("prompt", "")
            
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
            
        if executor._is_hybrid:
            executor.cache.clear()
        else:
            executor.kv_manager.clear()
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)
        
        with torch.inference_mode():
            # Initial prompt flush
            logits = await asyncio.to_thread(executor.execute_forward, input_ids, mode="prefill")
            next_token = Sampler.sample(logits, temperature, top_p)
            
            all_tokens = [next_token.item()]
            decoded_text = tokenizer.decode(all_tokens, skip_special_tokens=True)
            
            yield {
                "token": decoded_text,
                "finish_reason": None,
                "layers_loaded": executor.num_layers
            }
            
            current_input = next_token
            truncated = False
            for _ in range(max_tokens - 1):
                if not self.tokenizer or not self.layer_executor:
                    break   # Stop generation cleanly if engine gets unloaded externally
                    
                if eos_id is not None and next_token.item() == eos_id:
                    break
                    
                logits = await asyncio.to_thread(executor.execute_forward, current_input, mode="decode")
                next_token = Sampler.sample(logits, temperature, top_p)
                
                all_tokens.append(next_token.item())
                
                # Rolling-window overlap delta — robust to subword merges that
                # would otherwise drop/duplicate text with prefix slicing.
                token_text = _stream_delta(tokenizer, all_tokens, decoded_text)
                if token_text:
                    decoded_text += token_text
                    yield {
                        "token": token_text,
                        "finish_reason": None,
                        "layers_loaded": executor.num_layers
                    }
                current_input = next_token
            else:
                # Loop exhausted all max_tokens iterations without EOS — the
                # generation was truncated, so report "length" not "stop".
                truncated = True
                
        yield {
            "token": "",
            "finish_reason": "length" if truncated else "stop"
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        if self.layer_executor:
            stats = self.layer_executor.tracker.get_stats()
            return {
                "ram_used_gb": stats["peak_ram_mb"] / 1024,
                "layers_loaded": self.layer_executor.num_layers,
                "layer_memory_mb": 0,
                "kv_cache_mb": stats["kv_cache_size_mb"],
                "peak_vram_mb": stats["peak_vram_mb"]
            }
        return {}
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "memory": self.get_memory_usage()
        }