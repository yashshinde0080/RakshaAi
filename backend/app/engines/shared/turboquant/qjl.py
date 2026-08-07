import torch
from functools import lru_cache


@lru_cache(maxsize=4)
def get_qjl_projection(
    dim: int, qjl_dim: int, device: str = "cpu", seed: int = 123
) -> torch.Tensor:
    """Generate ±1 projection matrix for QJL (Rademacher).

    Args:
        dim: input dimension (head_dim)
        qjl_dim: projection dimension
        device: target device
        seed: rng seed for reproducibility

    Returns:
        [qjl_dim, dim] float32 projection matrix, normalized by sqrt(qjl_dim)
    """
    torch.manual_seed(seed)
    P = (torch.randint(0, 2, (qjl_dim, dim), device=device, dtype=torch.int8) * 2 - 1).to(
        torch.float32
    )
    return P / (qjl_dim**0.5)


def qjl_encode(residual: torch.Tensor, P: torch.Tensor) -> torch.Tensor:
    """Encode residual to 1-bit QJL sketch.

    Args:
        residual: [..., d] float32 residual vectors
        P: [qjl_dim, d] projection matrix

    Returns:
        [..., qjl_dim] int8 values in {-1, +1}
    """
    projected = residual @ P.T
    return torch.sign(projected).to(torch.int8)


def qjl_decode(qjl_codes: torch.Tensor, P: torch.Tensor) -> torch.Tensor:
    """Reconstruct residual approximation from QJL codes (unbiased estimator).

    Unbiased property: E[qjl_decode(qjl_encode(r))] ≈ r
    Requires division by the projection dimension.
    """
    qjl_dim = P.shape[0]
    return qjl_codes.to(torch.float32) @ P / qjl_dim
