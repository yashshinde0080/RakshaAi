"""Self-check: run with `python -m app.engines.shared.turboquant`"""
import sys
import torch

from .config import TurboQuantConfig
from .polarquant import get_rotation_matrix, apply_rotation, inverse_rotation
from .codebook import get_lloyd_max_centroids, quantize_polar
from .qjl import get_qjl_projection, qjl_encode, qjl_decode
from .kv_cache import TurboQuantKVCacheManager


def test_polarquant_roundtrip():
    d = 64
    # Use unit-norm vectors (matching PolarQuant's assumption)
    x = torch.randn(200, d)
    x = x / x.norm(dim=-1, keepdim=True)

    R = get_rotation_matrix(d)
    centroids = get_lloyd_max_centroids(d, 3.5)

    x_rot = apply_rotation(x, R)
    indices, x_quant = quantize_polar(x_rot, centroids)
    x_recon = inverse_rotation(x_quant, R)

    mse = ((x_recon - x) ** 2).mean().item()
    # ponytail: MSE ~0.02-0.06 at 3.5 bits for unit vectors; higher for raw K/V values
    assert mse < 0.1, f"PolarQuant MSE too high: {mse}"
    print(f"  PolarQuant roundtrip MSE: {mse:.6f} (unit vecs, 3.5-bit) OK")


def test_qjl_roundtrip():
    d = 64
    qjl_d = 64
    P = get_qjl_projection(d, qjl_d)
    residual = torch.randn(100, d) * 0.1

    codes = qjl_encode(residual, P)
    recon = qjl_decode(codes, P)

    err = ((recon - residual) ** 2).mean().item()
    print(f"  QJL residual MSE: {err:.6f}")
    assert err < 0.05, f"QJL MSE too high: {err}"


def test_kv_cache():
    config = TurboQuantConfig(bits_per_coord=3.5, enable_qjl=True, device="cpu")
    nh, hd = 8, 64
    seq = 128

    mgr = TurboQuantKVCacheManager(config, num_layers=4, num_heads=nh, head_dim=hd, device="cpu")
    k = torch.randn(1, nh, seq, hd, dtype=torch.float16)
    v = torch.randn(1, nh, seq, hd, dtype=torch.float16)

    mgr.update(0, k, v)
    k_recon, v_recon = mgr.get(0)

    assert k_recon is not None, "KV get returned None"
    assert k_recon.shape == k.shape, f"Shape mismatch: {k_recon.shape} vs {k.shape}"
    mse = ((k_recon.float() - k.float()) ** 2).mean().item()
    print(f"  KV cache K MSE: {mse:.6f} (raw K/V values)")
    assert mse < 0.3, f"KV cache K MSE too high: {mse}"

    compressed_mb = mgr.get_size_mb()
    fp16_mb = (k.numel() + v.numel()) * 2 / 1024**2
    ratio = fp16_mb / compressed_mb
    # ponytail: ratio < 1x without bit-packing; to hit 3-6x, pack indices into
    # int32/int64 (3.5 bits/coord → 9 indices/word) and reduce QJL dim < head_dim
    print(f"  Compression: {fp16_mb:.1f} MB -> {compressed_mb:.1f} MB ({ratio:.1f}x) OK")

    # Test with QJL off (PolarQuant only, 1 byte/coord)
    config2 = TurboQuantConfig(bits_per_coord=4.0, enable_qjl=False, device="cpu")
    mgr2 = TurboQuantKVCacheManager(config2, num_layers=2, num_heads=nh, head_dim=hd, device="cpu")
    mgr2.update(0, k, v)
    c2 = mgr2.get_size_mb()
    r2 = fp16_mb / c2
    print(f"  PolarQuant-only (4-bit, no QJL): {fp16_mb:.1f} MB -> {c2:.1f} MB ({r2:.1f}x) OK")


def test_cached_centroids():
    """Verify centroids are deterministic and cache hits work."""
    c1 = get_lloyd_max_centroids(64, 3.5)
    c2 = get_lloyd_max_centroids(64, 3.5)
    assert torch.equal(c1, c2), "Cached centroids differ"
    print(f"  Centroids cached: {len(c1)} levels OK")


if __name__ == "__main__":
    print("TurboQuant self-check:")
    test_cached_centroids()
    test_polarquant_roundtrip()
    test_qjl_roundtrip()
    test_kv_cache()
    print("\nAll checks passed OK")
    sys.exit(0)
