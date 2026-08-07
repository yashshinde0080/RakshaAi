import torch
from typing import Optional, Tuple, List
from transformers.cache_utils import DynamicCache


class StatefulCache:
    """Cache for stateful/hybrid models with both full_attention and linear_attention layers.

    Supports:
    - Standard K/V cache (full_attention): key_cache/value_cache
    - Stateful cache (linear_attention/GatedDeltaNet): conv_states/recurrent_states
    - .update() protocol used by Qwen3_5Attention and similar
    - Direct list access used by Qwen3_5GatedDeltaNet and similar

    ponytail: cache lives on GPU (where layers run), no CPU offloading.
    Add device management if GPU memory pressure becomes a problem.
    """
    def __init__(self, config=None, num_layers: int = 0, layer_types: list = None):
        if layer_types is None and config is not None:
            layer_types = getattr(config, 'layer_types', None)
        if layer_types is None:
            layer_types = ['full_attention'] * num_layers

        self.layer_types = layer_types
        self.num_layers = len(layer_types)

        linear_indices = [i for i, t in enumerate(layer_types) if t == 'linear_attention']
        self.last_linear_layer = max(linear_indices) if linear_indices else -1
        self.transformer_layers = [i for i, t in enumerate(layer_types) if t == 'full_attention']

        self.key_cache = [None] * self.num_layers
        self.value_cache = [None] * self.num_layers
        self.conv_states = [None] * self.num_layers
        self.recurrent_states = [None] * self.num_layers
        self._seq_length = 0

    def update(self, key_states, value_states, layer_idx, cache_kwargs=None):
        if self.key_cache[layer_idx] is None:
            self.key_cache[layer_idx] = key_states
            self.value_cache[layer_idx] = value_states
        else:
            self.key_cache[layer_idx] = torch.cat([self.key_cache[layer_idx], key_states], dim=2)
            self.value_cache[layer_idx] = torch.cat([self.value_cache[layer_idx], value_states], dim=2)
        return self.key_cache[layer_idx], self.value_cache[layer_idx]

    @property
    def has_previous_state(self):
        if self.last_linear_layer >= 0:
            return self.conv_states[self.last_linear_layer] is not None
        return any(k is not None for k in self.key_cache)

    def get_seq_length(self, layer_idx: int = 0) -> int:
        if self.transformer_layers and layer_idx not in self.transformer_layers:
            layer_idx = self.transformer_layers[0]
        if layer_idx < len(self.key_cache) and self.key_cache[layer_idx] is not None:
            return self.key_cache[layer_idx].shape[2]
        for k in self.key_cache:
            if k is not None:
                return k.shape[2]
        return self._seq_length

    def clear(self):
        self.key_cache = [None] * self.num_layers
        self.value_cache = [None] * self.num_layers
        self.conv_states = [None] * self.num_layers
        self.recurrent_states = [None] * self.num_layers
        self._seq_length = 0

    def get_size_mb(self) -> float:
        total = 0
        for lst in (self.key_cache, self.value_cache, self.conv_states, self.recurrent_states):
            for t in lst:
                if t is not None:
                    total += t.nelement() * t.element_size()
        return total / (1024 ** 2)

    def get_max_length(self):
        return None

    def __len__(self):
        return self.num_layers

    def __getitem__(self, layer_idx):
        if layer_idx < len(self.key_cache) and self.key_cache[layer_idx] is not None:
            return self.key_cache[layer_idx], self.value_cache[layer_idx]
        return None

    def reorder_cache(self, beam_idx):
        pass  # ponytail: no beam search support, add if needed


class KVCacheManager:
    """Manages KV cache strictly on CPU with O(1 layer) GPU footprint."""
    def __init__(self):
        self.key_cache: List[Optional[torch.Tensor]] = []
        self.value_cache: List[Optional[torch.Tensor]] = []
        self.conv_states: List[Optional[torch.Tensor]] = []
        self.recurrent_states: List[Optional[torch.Tensor]] = []
        self.seq_length: int = 0
        
    def ensure_layer(self, layer_idx: int):
        while len(self.key_cache) <= layer_idx:
            self.key_cache.append(None)
            self.value_cache.append(None)
            self.conv_states.append(None)
            self.recurrent_states.append(None)
            
    def get(self, layer_idx: int, device: Optional[torch.device] = None) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        if layer_idx < len(self.key_cache):
            k = self.key_cache[layer_idx]
            v = self.value_cache[layer_idx]
            if k is not None and v is not None:
                # vGPU/CUDA Optimization: Move to cache/compute device only when needed
                if device is not None and k.device != device:
                    return k.to(device, non_blocking=True), v.to(device, non_blocking=True)
                return k, v
        return None
        
    def set(self, layer_idx: int, kv: Tuple[torch.Tensor, torch.Tensor]):
        self.ensure_layer(layer_idx)
        k, v = kv
        # Optimization: Keep on GPU for speed. Weights are offloaded, but KV cache
        # residency on GPU is critical for latency in streaming engines.
        self.key_cache[layer_idx] = k
        self.value_cache[layer_idx] = v
        
    def clear(self):
        self.key_cache = []
        self.value_cache = []
        self.conv_states = []
        self.recurrent_states = []
        self.seq_length = 0
        
    def get_seq_length(self, layer_idx: int = 0) -> int:
        return self.seq_length
        
    def get_size_mb(self) -> float:
        total_bytes = 0
        for lst in (self.key_cache, self.value_cache, self.conv_states, self.recurrent_states):
            for t in lst:
                if t is not None:
                    total_bytes += t.nelement() * t.element_size()
        return total_bytes / (1024 ** 2)

    @classmethod
    def create(cls, mode: str = "standard", **kwargs):
        """Factory: create a KVCacheManager or TurboQuant variant."""
        if mode == "turboquant":
            from app.engines.shared.turboquant import TurboQuantKVCacheManager, TurboQuantConfig
            config = kwargs.pop('turboquant_config', {})
            if isinstance(config, dict):
                cfg = TurboQuantConfig(**config)
            else:
                cfg = config
            return TurboQuantKVCacheManager(cfg, **kwargs)
        return cls()


class ProxyList:
    def __init__(self, manager: KVCacheManager, attr_name: str):
        self.manager = manager
        self.attr_name = attr_name
        self._active_views = {}
        
    def __getitem__(self, i: int):
        self.manager.ensure_layer(i)
        lst = getattr(self.manager, self.attr_name)
        val = lst[i]
        if val is not None:
            # Fallback for CPU runs: don't force to CUDA if we are explicitly on CPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            view = val.to(device)
            self._active_views[i] = view
            return view
        return None
        
    def __setitem__(self, i: int, val):
        self.manager.ensure_layer(i)
        lst = getattr(self.manager, self.attr_name)
        if val is not None:
            self._active_views[i] = val
            lst[i] = val.detach().cpu()
        else:
            if i in self._active_views:
                del self._active_views[i]
            lst[i] = None

    def sync_back(self):
        lst = getattr(self.manager, self.attr_name)
        for i, view in self._active_views.items():
            if view is not None:
                # Keep on original device for speed if possible
                lst[i] = view.detach()
        self._active_views.clear()

class HFProxyCache(DynamicCache):
    """Interface to map layer-local KV tuple seamlessly into transformers.DynamicCache"""
    def __init__(self, manager: KVCacheManager):
        super().__init__()
        self.manager = manager
        self.conv_states = ProxyList(manager, "conv_states")
        self.recurrent_states = ProxyList(manager, "recurrent_states")
        
    @property
    def has_previous_state(self):
        return self.manager.get_seq_length(0) > 0 or (len(self.manager.conv_states) > 0 and any(c is not None for c in self.manager.conv_states))
        
    def update(
        self,
        key_states: torch.Tensor,
        value_states: torch.Tensor,
        layer_idx: int,
        cache_kwargs=None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # Intelligent Update: Detects vGPU vs Dedicated GPU vs CPU
        compute_device = key_states.device
        past_kv = self.manager.get(layer_idx, device=compute_device)
        
        if past_kv is not None:
            prev_k, prev_v = past_kv
            k_new = torch.cat([prev_k, key_states], dim=-2)
            v_new = torch.cat([prev_v, value_states], dim=-2)
        else:
            k_new = key_states
            v_new = value_states
            
        self.manager.set(layer_idx, (k_new, v_new))
        return k_new, v_new
        
    def get_seq_length(self, layer_idx: int = 0) -> int:
        if layer_idx < len(self.manager.key_cache) and self.manager.key_cache[layer_idx] is not None:
            return self.manager.key_cache[layer_idx].shape[-2]
        for k in self.manager.key_cache:
            if k is not None:
                return k.shape[-2]
        return self.manager.get_seq_length(layer_idx)
        
    def get_max_length(self) -> Optional[int]:
        return None
    
    def __len__(self):
        return len(self.manager.key_cache)
    
    def __getitem__(self, layer_idx: int):
        kv = self.manager.get(layer_idx)
        if kv is not None:
            return kv
        return None
