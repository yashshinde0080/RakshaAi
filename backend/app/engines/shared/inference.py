"""Shared Inference Utilities"""
import numpy as np
from typing import Optional, Tuple


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Compute softmax"""
    exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


def apply_rope(
    x: np.ndarray,
    positions: np.ndarray,
    theta: float = 10000.0
) -> np.ndarray:
    """Apply Rotary Position Embedding"""
    seq_len, num_heads, head_dim = x.shape
    
    # Compute frequencies
    freqs = 1.0 / (theta ** (np.arange(0, head_dim, 2) / head_dim))
    
    # Compute rotation angles
    t = positions[:, np.newaxis]  # [seq_len, 1]
    angles = t * freqs[np.newaxis, :]  # [seq_len, head_dim/2]
    
    # Apply rotation
    cos_angles = np.cos(angles)
    sin_angles = np.sin(angles)
    
    x_reshaped = x.reshape(seq_len, num_heads, head_dim // 2, 2)
    x_real = x_reshaped[..., 0]
    x_imag = x_reshaped[..., 1]
    
    out_real = x_real * cos_angles[:, np.newaxis, :] - x_imag * sin_angles[:, np.newaxis, :]
    out_imag = x_real * sin_angles[:, np.newaxis, :] + x_imag * cos_angles[:, np.newaxis, :]
    
    return np.stack([out_real, out_imag], axis=-1).reshape(seq_len, num_heads, head_dim)


def attention(
    query: np.ndarray,
    key: np.ndarray,
    value: np.ndarray,
    mask: Optional[np.ndarray] = None,
    scale: Optional[float] = None
) -> np.ndarray:
    """Compute scaled dot-product attention"""
    if scale is None:
        scale = 1.0 / np.sqrt(query.shape[-1])
    
    # Compute attention scores
    scores = np.matmul(query, key.transpose(-2, -1)) * scale
    
    # Apply mask
    if mask is not None:
        scores = np.where(mask, scores, -1e9)
    
    # Softmax
    weights = softmax(scores, axis=-1)
    
    # Apply to values
    return np.matmul(weights, value)


def layer_norm(
    x: np.ndarray,
    weight: np.ndarray,
    bias: Optional[np.ndarray] = None,
    eps: float = 1e-5
) -> np.ndarray:
    """Apply layer normalization"""
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    
    normalized = (x - mean) / np.sqrt(var + eps)
    
    if bias is not None:
        return weight * normalized + bias
    return weight * normalized


def rms_norm(
    x: np.ndarray,
    weight: np.ndarray,
    eps: float = 1e-5
) -> np.ndarray:
    """Apply RMS normalization"""
    rms = np.sqrt(np.mean(x ** 2, axis=-1, keepdims=True) + eps)
    return weight * (x / rms)