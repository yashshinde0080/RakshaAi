import torch
from functools import lru_cache


@lru_cache(maxsize=4)
def get_rotation_matrix(dim: int, device: str = "cpu", seed: int = 42) -> torch.Tensor:
    """Generate random orthogonal matrix R ∈ O(dim) via QR decomposition.

    Cached per (dim, device) — shared across all layers/models.
    """
    torch.manual_seed(seed)
    A = torch.randn(dim, dim, device=device, dtype=torch.float32)
    Q, R = torch.linalg.qr(A)
    D = torch.diag(torch.sign(torch.diag(R)))
    return Q @ D


def apply_rotation(x: torch.Tensor, R: torch.Tensor) -> torch.Tensor:
    """Apply rotation: x̃ = x @ R.T (R is orthogonal, so R.T = R^-1)

    Args:
        x: [..., d] input vectors
        R: [d, d] orthogonal matrix

    Returns:
        [..., d] rotated vectors
    """
    return x.to(dtype=R.dtype) @ R.T


def inverse_rotation(x_tilde: torch.Tensor, R: torch.Tensor) -> torch.Tensor:
    """Recover original: x = x̃ @ R"""
    return x_tilde @ R
