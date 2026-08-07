"""KV Cache for FullRAM Engine"""
from typing import Optional, Tuple, Any
import numpy as np


class KVCache:
    """Key-Value cache for transformer attention"""

    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        max_seq_len: int,
        dtype=np.float16,
        use_turboquant: bool = False,
        turboquant_config: Any = None,
    ):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.dtype = dtype
        self.use_turboquant = use_turboquant
        self.turboquant_config = turboquant_config

        if use_turboquant:
            from app.engines.shared.turboquant import TurboQuantKVCacheManager, TurboQuantConfig

            cfg = turboquant_config
            if isinstance(cfg, dict):
                cfg_obj = TurboQuantConfig(**cfg)
            elif cfg is None:
                cfg_obj = TurboQuantConfig()
            else:
                cfg_obj = cfg

            self.tq_manager = TurboQuantKVCacheManager(
                config=cfg_obj,
                num_layers=num_layers,
                num_heads=num_heads,
                head_dim=head_dim,
                device="cpu",
            )
        else:
            self.tq_manager = None
            # Pre-allocate cache
            cache_shape = (num_layers, 2, max_seq_len, num_heads, head_dim)
            self.cache = np.zeros(cache_shape, dtype=dtype)
            self.position = 0

    def update(
        self, layer_idx: int, key: np.ndarray, value: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Update cache with new key/value"""
        if self.use_turboquant and self.tq_manager is not None:
            import torch

            k_t = torch.from_numpy(key).unsqueeze(0)
            v_t = torch.from_numpy(value).unsqueeze(0)
            self.tq_manager.update(layer_idx, k_t, v_t)
            k_out, v_out = self.tq_manager.get(layer_idx)
            return k_out.squeeze(0).numpy(), v_out.squeeze(0).numpy()

        seq_len = key.shape[0]

        if self.position + seq_len > self.max_seq_len:
            # Sliding window - shift cache
            shift = seq_len
            self.cache[:, :, :-shift] = self.cache[:, :, shift:]
            self.position = self.max_seq_len - seq_len

        # Store new values
        self.cache[layer_idx, 0, self.position : self.position + seq_len] = key
        self.cache[layer_idx, 1, self.position : self.position + seq_len] = value

        k = self.cache[layer_idx, 0, : self.position + seq_len]
        v = self.cache[layer_idx, 1, : self.position + seq_len]
        return k, v

    def get(self, layer_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """Get cached key/value for layer"""
        if self.use_turboquant and self.tq_manager is not None:
            import torch

            k_out, v_out = self.tq_manager.get(layer_idx)
            if k_out is not None:
                return k_out.squeeze(0).numpy(), v_out.squeeze(0).numpy()
            return np.array([]), np.array([])

        return (
            self.cache[layer_idx, 0, : self.position],
            self.cache[layer_idx, 1, : self.position],
        )

    def clear(self):
        """Clear cache"""
        if self.use_turboquant and self.tq_manager is not None:
            self.tq_manager.clear()
            return
        self.cache.fill(0)
        self.position = 0

    def get_memory_usage(self) -> int:
        """Get cache memory usage in bytes"""
        if self.use_turboquant and self.tq_manager is not None:
            return int(self.tq_manager.get_size_mb() * 1024 * 1024)
        return self.cache.nbytes
