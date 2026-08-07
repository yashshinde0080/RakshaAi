"""
Model Providers Package

Provides unified interface for fetching models from various sources:
- HuggingFace Hub
- Local filesystem
- Enterprise private repositories
- USB/portable bundles
"""

from app.providers.base import BaseProvider, ModelMetadata, DownloadProgress
from app.providers.huggingface import HuggingFaceProvider
from app.providers.local import LocalProvider
from app.providers.enterprise_repo import EnterpriseRepoProvider
from app.providers.usb_bundle import USBBundleProvider
from app.providers.registry import ProviderRegistry, get_provider
from app.providers.exceptions import (
    ProviderError,
    ModelNotFoundError,
    DownloadError,
    ValidationError,
    AuthenticationError,
    RateLimitError
)

__all__ = [
    # Base
    "BaseProvider",
    "ModelMetadata",
    "DownloadProgress",
    
    # Providers
    "HuggingFaceProvider",
    "LocalProvider",
    "EnterpriseRepoProvider",
    "USBBundleProvider",
    
    # Registry
    "ProviderRegistry",
    "get_provider",
    
    # Exceptions
    "ProviderError",
    "ModelNotFoundError",
    "DownloadError",
    "ValidationError",
    "AuthenticationError",
    "RateLimitError",
]