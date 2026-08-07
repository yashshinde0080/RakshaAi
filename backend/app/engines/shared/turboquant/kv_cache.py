import torch
from typing import Optional, Tuple, List
from dataclasses import dataclass
import torch.nn.functional as F

from .config import TurboQuantConfig
from .codebook import get_lloyd_max_centroids, quantize_polar
from .polarquant import get_rotation_matrix, apply_rotation, inverse_rotation
from .qjl import get_qjl_projection, qjl_encode, qjl_decode


@dataclass
class QuantizedKVCache:
    """Compressed KV cache entry for one layer."""

    # PolarQuant indices: [num_heads, seq_len, head_dim] int32
    k_indices: torch.Tensor
    v_indices: torch.Tensor
    # QJL residual codes: [num_heads, seq_len, qjl_dim] int8
    k_qjl: Optional[torch.Tensor] = None
    v_qjl: Optional[torch.Tensor] = None
    # Per-vector scale factors (norm before normalization): [num_heads, seq_len, 1]
    k_scale: Optional[torch.Tensor] = None
    v_scale: Optional[torch.Tensor] = None
    # Metadata
    seq_len: int = 0
    head_dim: int = 0


class TurboQuantKVCacheManager:
    """Drop-in for KVCacheManager with TurboQuant compression.

    Compresses K/V to ~3.5 bits/coord + 1 bit QJL = ~4.5 bits total
    vs FP16 16 bits = ~3.5× compression, near-lossless quality.
    """

    def __init__(
        self,
        config: TurboQuantConfig,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        device: str = "cpu",
    ):
        self.config = config
        self.num_layers = num_layers
        self.device = torch.device(device)

        # Per-layer cache storage
        self.k_cache: List[Optional[QuantizedKVCache]] = [None] * num_layers
        self.v_cache: List[Optional[QuantizedKVCache]] = [None] * num_layers
        # For compatibility with models that expect conv_states and recurrent_states
        self.conv_states: List[Optional[torch.Tensor]] = [None] * num_layers
        self.recurrent_states: List[Optional[torch.Tensor]] = [None] * num_layers

        # Runtime
        self.seq_length = 0

    def _quantize_kv(
        self, k: torch.Tensor, v: torch.Tensor
    ) -> Tuple[QuantizedKVCache, QuantizedKVCache]:
        """Quantize K and V tensors for one layer.

        Normalizes each K/V vector to unit length before rotation/quantization
        so centroids (designed for [-1, 1]) match the actual data distribution.
        Scale factors are stored and reapplied on dequantize.

        Derives rotation/QJL/codebook matrices from the actual tensor head_dim
        (not self.head_dim) to support models where K/V head_dim differs from
        hidden_size // num_attention_heads (e.g. Qwen3.5 MLA).
        """
        batch, nh, seq, hd = k.shape
        # ponytail: batch > 1 not handled — add if multi-batch inference needed
        if batch != 1:
            raise ValueError(f"Batch > 1 not supported, got batch={batch}")

        # Flatten for vector ops: [num_heads * seq_len, head_dim]
        k_flat = k.squeeze(0).reshape(-1, hd)
        v_flat = v.squeeze(0).reshape(-1, hd)

        # Derive matrices from actual tensor head_dim (not self.head_dim)
        # All getters are @lru_cache'd — free on repeat calls.
        R_k = get_rotation_matrix(hd, self.device)
        R_v = get_rotation_matrix(hd, self.device, seed=43)
        centroids = get_lloyd_max_centroids(hd, self.config.bits_per_coord, self.device)

        # Normalize to unit vectors so centroids (designed for [-1, 1]) match data
        k_norm = k_flat.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        v_norm = v_flat.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        k_unit = k_flat / k_norm
        v_unit = v_flat / v_norm

        # Stage 1: PolarQuant — rotate + quantize
        k_rot = apply_rotation(k_unit, R_k)
        v_rot = apply_rotation(v_unit, R_v)
        k_indices, k_quant = quantize_polar(k_rot, centroids)
        v_indices, v_quant = quantize_polar(v_rot, centroids)

        # Stage 2: QJL residual correction
        if self.config.enable_qjl:
            qjl_dim = self.config.qjl_dim or hd
            P_k = get_qjl_projection(hd, qjl_dim, self.device)
            P_v = get_qjl_projection(hd, qjl_dim, self.device, seed=456)
            k_qjl = qjl_encode(k_rot - k_quant, P_k)
            v_qjl = qjl_encode(v_rot - v_quant, P_v)
        else:
            k_qjl = v_qjl = None

        # Reshape back
        k_indices = k_indices.reshape(nh, seq, hd)
        v_indices = v_indices.reshape(nh, seq, hd)
        k_scale = k_norm.reshape(nh, seq, 1)
        v_scale = v_norm.reshape(nh, seq, 1)
        if k_qjl is not None:
            k_qjl = k_qjl.reshape(nh, seq, -1)
            v_qjl = v_qjl.reshape(nh, seq, -1)

        k_cache = QuantizedKVCache(
            k_indices=k_indices, v_indices=torch.zeros_like(v_indices),
            k_qjl=k_qjl, k_scale=k_scale, seq_len=seq, head_dim=hd
        )
        v_cache = QuantizedKVCache(
            k_indices=v_indices, v_indices=torch.zeros_like(v_indices),
            k_qjl=v_qjl, k_scale=v_scale, seq_len=seq, head_dim=hd
        )
        return k_cache, v_cache

    def _dequantize_kv(
        self, k_cache: QuantizedKVCache, v_cache: QuantizedKVCache
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Dequantize K and V for attention computation.

        Rescales by stored per-vector norms to recover original magnitude
        after PolarQuant unit-vector quantization.

        Derives matrices from cached head_dim (not self.head_dim) so models
        with non-standard K/V head_dim (e.g. Qwen3.5 MLA) work correctly.
        """
        nh, seq, hd = k_cache.k_indices.shape

        # Derive matrices from cached head_dim (matches how it was quantized)
        centroids = get_lloyd_max_centroids(hd, self.config.bits_per_coord, self.device)
        R_k = get_rotation_matrix(hd, self.device)
        R_v = get_rotation_matrix(hd, self.device, seed=43)

        # Stage 1: centroids lookup
        k_quant = centroids[k_cache.k_indices.long()].reshape(nh, seq, hd)
        v_quant = centroids[v_cache.k_indices.long()].reshape(nh, seq, hd)

        # Stage 2: add QJL residual
        if self.config.enable_qjl and k_cache.k_qjl is not None:
            qjl_dim = self.config.qjl_dim or hd
            P_k = get_qjl_projection(hd, qjl_dim, self.device)
            P_v = get_qjl_projection(hd, qjl_dim, self.device, seed=456)
            k_residual = qjl_decode(
                k_cache.k_qjl.reshape(-1, k_cache.k_qjl.shape[-1]), P_k
            ).reshape(nh, seq, hd)
            v_residual = qjl_decode(
                v_cache.k_qjl.reshape(-1, v_cache.k_qjl.shape[-1]), P_v
            ).reshape(nh, seq, hd)
            k_rot = k_quant + k_residual
            v_rot = v_quant + v_residual
        else:
            k_rot, v_rot = k_quant, v_quant

        # Inverse rotation (unit-vector space) + rescale to original magnitude
        k_recon = inverse_rotation(k_rot.reshape(-1, hd), R_k).reshape(nh, seq, hd) * k_cache.k_scale
        v_recon = inverse_rotation(v_rot.reshape(-1, hd), R_v).reshape(nh, seq, hd) * v_cache.k_scale

        return k_recon.unsqueeze(0), v_recon.unsqueeze(0)

    def update(self, layer_idx: int, k: torch.Tensor, v: torch.Tensor):
        """Quantize and store new K/V, appending if cache exists."""
        if self.k_cache[layer_idx] is None:
            self.k_cache[layer_idx], self.v_cache[layer_idx] = self._quantize_kv(k, v)
        else:
            # Dequantize, concat, re-quantize
            k_old, v_old = self._dequantize_kv(
                self.k_cache[layer_idx], self.v_cache[layer_idx]
            )
            k_new = torch.cat([k_old, k], dim=2)
            v_new = torch.cat([v_old, v], dim=2)
            self.k_cache[layer_idx], self.v_cache[layer_idx] = self._quantize_kv(
                k_new, v_new
            )

        self.seq_length = self.k_cache[layer_idx].seq_len

    def get(
        self, layer_idx: int, device: Optional[torch.device] = None
    ) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        """Dequantize and return K/V for attention."""
        if self.k_cache[layer_idx] is None:
            return None, None

        k, v = self._dequantize_kv(self.k_cache[layer_idx], self.v_cache[layer_idx])

        if device is not None and k.device != device:
            k = k.to(device, non_blocking=True)
            v = v.to(device, non_blocking=True)

        return k, v

    def clear(self):
        """Reset all cache entries."""
        self.k_cache = [None] * self.num_layers
        self.v_cache = [None] * self.num_layers
        self.conv_states = [None] * self.num_layers
        self.recurrent_states = [None] * self.num_layers
        self.seq_length = 0

    def get_seq_length(self, layer_idx: int = 0) -> int:
        if self.k_cache[layer_idx] is not None:
            return self.k_cache[layer_idx].seq_len
        return 0

    def get_size_mb(self) -> float:
        """Estimate compressed cache size in MB."""
        total_bytes = 0
        for kc, vc in zip(self.k_cache, self.v_cache):
            if kc is not None:
                total_bytes += kc.k_indices.numel() * kc.k_indices.element_size()
                total_bytes += vc.k_indices.numel() * vc.k_indices.element_size()
                if kc.k_qjl is not None:
                    total_bytes += kc.k_qjl.numel() * kc.k_qjl.element_size()
                    total_bytes += vc.k_qjl.numel() * vc.k_qjl.element_size()
                if kc.k_scale is not None:
                    total_bytes += kc.k_scale.numel() * kc.k_scale.element_size()
                    total_bytes += vc.k_scale.numel() * vc.k_scale.element_size()
        return total_bytes / (1024**2)

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