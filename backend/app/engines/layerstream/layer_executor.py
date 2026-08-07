import os
import time
import inspect
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional

from .loader import LayerWeightLoader
from .kv_cache import KVCacheManager, HFProxyCache, StatefulCache
from .benchmark import BenchmarkTracker

class LayerExecutor:
    """Orchestrates IO, KV, and isolated GPU forward passes safely."""
    def __init__(self, components: Dict[str, Any], config: Any, weights_dir: str, device: str,
                 turboquant_config: Optional[dict] = None, layer_types: Optional[list] = None):
        self.components = components
        self.config = config
        self.weights_dir = weights_dir
        self.device = torch.device(device)
        self.num_layers = len(components['layers'])

        # CPU Optimization: float16 is very slow on many CPUs.
        # Use bfloat16 or float32 for CPU-only runs.
        self.compute_dtype = torch.float16 if self.device.type == "cuda" else torch.float32

        self.loader = LayerWeightLoader(weights_dir)
        self.tracker = BenchmarkTracker()

        # Detect hybrid/stateful models (e.g. Qwen3.5 with linear_attention + full_attention)
        # layer_types is passed from executor.py which checks both full config and text_config
        if layer_types is None:
            layer_types = getattr(config, 'layer_types', None)
        self._is_hybrid = layer_types is not None and 'linear_attention' in layer_types

        # TurboQuant or standard KV cache
        self.turboquant_config = turboquant_config
        if self._is_hybrid:
            # Hybrid models use StatefulCache that lives on GPU — handles both
            # full_attention (key_cache/value_cache) and linear_attention (conv_states/recurrent_states)
            self.cache = StatefulCache(config=config, num_layers=self.num_layers, layer_types=layer_types)
            self.kv_manager = None
            if turboquant_config is not None:
                print("TurboQuant skipped: hybrid/stateful model uses StatefulCache instead")
            self._hf_cache_factory = lambda: self.cache
        elif turboquant_config is not None:
            from app.engines.shared.turboquant import TurboQuantKVCacheManager, TurboQuantHFProxyCache
            tq_config = turboquant_config if hasattr(turboquant_config, 'bits_per_coord') else type('obj', (object,), {'bits_per_coord': 3.5, 'qjl_dim': 128, 'enable_polarquant': True, 'enable_qjl': True, 'rotation_type': 'random', 'codebook_type': 'beta_lloyd_max', 'device': device, 'collect_stats': False})()
            # Use config object
            from app.engines.shared.turboquant import TurboQuantConfig
            if isinstance(turboquant_config, dict):
                tq_cfg = TurboQuantConfig(**turboquant_config)
            else:
                tq_cfg = turboquant_config
            tq_cfg.device = device
            head_dim = config.hidden_size // config.num_attention_heads
            self.kv_manager = TurboQuantKVCacheManager(
                config=tq_cfg,
                num_layers=self.num_layers,
                num_heads=config.num_attention_heads,
                head_dim=head_dim,
                device=device
            )
            self._hf_cache_factory = lambda: TurboQuantHFProxyCache(self.kv_manager)
        else:
            self.kv_manager = KVCacheManager()
            self._hf_cache_factory = lambda: HFProxyCache(self.kv_manager)
        
        self.layer_paths = [os.path.join(weights_dir, f"layer_{i}.safetensors") for i in range(self.num_layers)]
        self.embed_path = os.path.join(weights_dir, "embed.safetensors")
        self.norm_path = os.path.join(weights_dir, "norm.safetensors")
        self.lm_head_path = os.path.join(weights_dir, "lm_head.safetensors")
    
    def _create_attention_mask(self, input_shape: tuple, past_length: int, dtype: torch.dtype) -> torch.Tensor:
        """Architecture-aware attention mask mapping."""
        batch_size, seq_length = input_shape
        mask = torch.full((batch_size, 1, seq_length, seq_length + past_length), torch.finfo(dtype).min, device=self.device)
        
        causal_mask = torch.tril(torch.ones((seq_length, seq_length), device=self.device))
        if past_length > 0:
            past_mask = torch.ones((seq_length, past_length), device=self.device)
            full_mask = torch.cat([past_mask, causal_mask], dim=-1)
        else:
            full_mask = causal_mask
            
        full_mask = full_mask.unsqueeze(0).unsqueeze(0).expand(batch_size, 1, seq_length, seq_length + past_length)
        mask = torch.where(full_mask == 1.0, torch.tensor(0.0, device=self.device, dtype=dtype), mask)
        return mask

    def assign_weights(self, module: nn.Module, state_dict: dict):
        """Ultra-fast weight assignment with vGPU/CUDA awareness."""
        for name, _ in module.named_parameters():
            if name in state_dict:
                parts = name.split('.')
                parent = module
                for part in parts[:-1]:
                    parent = getattr(parent, part)
                attr = parts[-1]
                # vGPU/CUDA optimization: use non_blocking=True to overlap copy with next disk read
                dev_tensor = state_dict[name].to(self.device, dtype=self.compute_dtype, non_blocking=True)
                parent._parameters[attr] = nn.Parameter(dev_tensor, requires_grad=False)
                
        for name, buf in module.named_buffers():
            parts = name.split('.')
            parent = module
            for part in parts[:-1]:
                parent = getattr(parent, part)
            attr = parts[-1]
            
            if name in state_dict:
                dev_tensor = state_dict[name].to(self.device, non_blocking=True)
                parent._buffers[attr] = dev_tensor
            elif buf is not None and buf.device.type == 'meta':
                # Handle RoPE and other buffers specifically for CUDA/vGPU
                if "inv_freq" in attr:
                    dim = buf.shape[0] * 2
                    base = getattr(self.config, "rope_theta", 10000.0)
                    inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2, dtype=torch.float32, device=self.device) / dim))
                    parent._buffers[attr] = inv_freq
                else:
                    if getattr(buf, 'dtype', None) in [torch.int, torch.long, torch.bool]:
                        parent._buffers[attr] = torch.zeros_like(buf, device=self.device)
                    else:
                        parent._buffers[attr] = torch.zeros_like(buf, device=self.device, dtype=self.compute_dtype)

    def offload_weights(self, module: nn.Module):
        """Immediately destroys dense parameters to isolate VRAM peak values."""
        for name, param in module.named_parameters():
            parts = name.split('.')
            parent = module
            for part in parts[:-1]:
                parent = getattr(parent, part)
            attr = parts[-1]
            parent._parameters[attr] = nn.Parameter(torch.empty(0, device="cpu", dtype=param.dtype), requires_grad=False)
            
        for name, buf in module.named_buffers():
            if buf is not None and buf.numel() > 1000:
                parts = name.split('.')
                parent = module
                for part in parts[:-1]:
                    parent = getattr(parent, part)
                attr = parts[-1]
                parent._buffers[attr] = torch.empty(0, device="cpu", dtype=buf.dtype)

    def execute_forward(self, input_ids: torch.Tensor, mode: str = "decode") -> torch.Tensor:
        """Executes full discrete unspooling: modes are prefill / decode."""
        compute_start = time.perf_counter()
        batch_size, seq_length = input_ids.shape

        if self._is_hybrid:
            past_length = self.cache.get_seq_length(0)
        else:
            past_length = 0 if mode == "prefill" else self.kv_manager.get_seq_length(0)
            
        max_context = getattr(self.config, "max_position_embeddings", 4096)
        if past_length + seq_length > max_context:
            raise ValueError(f"Context length limits exceeded. Try generating fewer tokens.")
        
        t0 = time.perf_counter()
        embed_dict = self.loader.get_weights(self.embed_path)
        self.tracker.record_layer_load(time.perf_counter() - t0)
        
        embed = self.components['embed']
        self.assign_weights(embed, embed_dict)
        hidden_states = embed(input_ids)
        
        if hasattr(self, "DEBUG") and self.DEBUG:
            print(f"DEBUG: execute_forward embed max: {hidden_states.max().item()}")
        self.offload_weights(embed)
        
        # Removed aggressive CUDA sync/empty_cache here for speed.
        # The allocator handles fragmentation naturally.

        position_ids = torch.arange(past_length, past_length + seq_length, dtype=torch.long, device=self.device).unsqueeze(0)
        cache_position = torch.arange(past_length, past_length + seq_length, dtype=torch.long, device=self.device)
        attention_mask = self._create_attention_mask((batch_size, seq_length), past_length, hidden_states.dtype)
        
        # Pre-compute RoPE if required by newer transformers
        position_embeddings = None
        rotary_emb = self.components.get("rotary_emb")
        if rotary_emb is not None:
             # Ensure rotary_emb buffers are in the right place
             rotary_emb.to(self.device)
             # Modern transformers expect (cos, sin) tuple
             # Note: Some architectures differ, but this is the standard for Qwen2/Llama3
             res = rotary_emb(hidden_states, position_ids)
             if isinstance(res, tuple):
                 # Return (cos, sin) as-is from the rotary_emb module.
                 # Modern transformers (4.46+) expect these to be broadcastable 
                 # to (batch, num_heads, seq, head_dim).
                 # Standard Qwen2RotaryEmbedding returns (batch, seq, head_dim).
                 position_embeddings = res
             else:
                 position_embeddings = res
        
        if self._is_hybrid:
            hf_cache = self.cache
        else:
            hf_cache = self._hf_cache_factory()

        # Main layer loop
        for i, layer in enumerate(self.components['layers']):
            t0 = time.perf_counter()
            next_idx = i + 1
            # Enable prefetching for both prefill and decode to maintain pipeline speed
            if next_idx < self.num_layers:
                self.loader.prefetch_async(self.layer_paths[next_idx])
            
            layer_dict = self.loader.get_weights(self.layer_paths[i])
            self.tracker.record_layer_load(time.perf_counter() - t0)
            self.assign_weights(layer, layer_dict)
            
            # Dynamic introspective signature dispatching
            sig = inspect.signature(layer.forward)
            kwargs = {}
            if "position_ids" in sig.parameters:
                kwargs["position_ids"] = position_ids
            if "attention_mask" in sig.parameters:
                kwargs["attention_mask"] = attention_mask
            
            if "use_cache" in sig.parameters:
                kwargs["use_cache"] = True
            # Support both old (past_key_value) and new (past_key_values) param names
            if "past_key_values" in sig.parameters:
                kwargs["past_key_values"] = hf_cache
            elif "past_key_value" in sig.parameters:
                kwargs["past_key_value"] = hf_cache
                
            if "cache_position" in sig.parameters:
                kwargs["cache_position"] = cache_position
            if "position_embeddings" in sig.parameters:
                kwargs["position_embeddings"] = position_embeddings
                
            layer_outputs = layer(hidden_states, **kwargs)
            
            # sync_back only needed for HFProxyCache (standard model with CPU offloading)
            if not self._is_hybrid:
                hf_cache.conv_states.sync_back()
                hf_cache.recurrent_states.sync_back()
            
            if isinstance(layer_outputs, tuple):
                hidden_states = layer_outputs[0]
            else:
                hidden_states = layer_outputs
            if hasattr(self, "DEBUG") and self.DEBUG:
                print(f"DEBUG: layer {i} max: {hidden_states.max().item()}")
            
            self.offload_weights(layer)
            
            # REMOVED: torch.cuda.empty_cache() and synchronize() in inner loop
            # These were the primary bottlenecks for LayerStream generation speed.
            # We only record VRAM usage here.
            self.tracker.update_vram()
            
        norm = self.components['norm']
        if norm is not None:
            t0 = time.perf_counter()
            norm_dict = self.loader.get_weights(self.norm_path)
            self.tracker.record_layer_load(time.perf_counter() - t0)
            self.assign_weights(norm, norm_dict)
            hidden_states = norm(hidden_states)
            self.offload_weights(norm)
            self.tracker.update_vram()

        lm_head = self.components['lm_head']
        t0 = time.perf_counter()
        lm_head_dict = self.loader.get_weights(self.lm_head_path)
        self.tracker.record_layer_load(time.perf_counter() - t0)
        self.assign_weights(lm_head, lm_head_dict)
        
        last_hidden_state = hidden_states[:, -1:, :]
        logits = lm_head(last_hidden_state)
        self.offload_weights(lm_head)
        self.tracker.update_vram()
        
        self.tracker.record_compute(time.perf_counter() - compute_start)
        if self._is_hybrid:
            self.tracker.set_kv_cache_size(self.cache.get_size_mb())
            self.cache._seq_length = past_length + seq_length
        else:
            self.tracker.set_kv_cache_size(self.kv_manager.get_size_mb())
            self.kv_manager.seq_length = past_length + seq_length
        return logits
