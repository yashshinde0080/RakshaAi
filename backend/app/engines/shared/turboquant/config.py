from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class TurboQuantConfig:
    """Configuration for TurboQuant KV cache compression.

    Controls the PolarQuant + QJL two-stage pipeline for ~6× KV cache
    compression with near-lossless quality at 3.5 bits/channel.
    """

    # Quantization bits per coordinate (3.5 = lossless, 2.5 = near-lossless)
    bits_per_coord: float = 3.5

    # QJL residual correction dimension (None = auto = head_dim)
    qjl_dim: Optional[int] = None

    # Enable/disable stages
    enable_polarquant: bool = True
    enable_qjl: bool = True

    # Rotation matrix strategy
    rotation_type: Literal["random", "hadamard"] = "random"

    # Codebook type for scalar quantizer
    codebook_type: str = "beta_lloyd_max"

    # Device for quantization ops
    device: str = "cpu"

    # Collect debug stats
    collect_stats: bool = False

    def __post_init__(self):
        if self.qjl_dim is None:
            self.qjl_dim = 128  # Default head_dim, overridden at runtime
