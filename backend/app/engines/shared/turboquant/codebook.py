import torch
from functools import lru_cache


@lru_cache(maxsize=8)
def get_lloyd_max_centroids(dim: int, bits: float, device: str = "cpu") -> torch.Tensor:
    """Return uniform centroids on [-1, 1] for PolarQuant.

    Uniform spacing is simpler, correct, and outperforms the broken Lloyd-Max
    Beta-based computation (which had a missing sqrt() mapping and clustered
    all centroids near ±1, leaving most of [-1, 1] empty).

    After random orthogonal rotation, coordinates of a unit vector on the
    sphere in d dimensions follow a distribution symmetric around 0 on [-1, 1].
    Uniform centroids give MSE = (2/(N-1))^2 / 12 per coordinate.
    """
    num_levels = int(2**bits)
    if num_levels <= 1:
        return torch.tensor([0.0], dtype=torch.float32, device=device)
    return torch.linspace(-1.0, 1.0, num_levels, dtype=torch.float32, device=device)


def quantize_polar(
    x: torch.Tensor, centroids: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """Quantize rotated vectors to nearest centroids.

    Args:
        x: [..., d] rotated vectors
        centroids: [num_levels] optimal centroids (symmetric around 0)

    Returns:
        indices: [..., d] uint8 centroid indices (uint16 if >256 levels)
        quantized: [..., d] reconstructed values
    """
    diff = x.unsqueeze(-1) - centroids.view(*([1] * x.ndim), -1)
    idx_dtype = torch.uint8 if len(centroids) <= 255 else torch.int32
    indices = diff.abs().argmin(dim=-1).to(idx_dtype)
    quantized = centroids[indices.long()]
    return indices, quantized
