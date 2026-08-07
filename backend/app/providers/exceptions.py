"""
Provider Exceptions

Custom exceptions for model provider operations.
"""

from typing import Optional, Dict, Any


class ProviderError(Exception):
    """Base exception for all provider errors"""
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.provider:
            return f"[{self.provider}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "provider": self.provider,
            "details": self.details
        }


class ModelNotFoundError(ProviderError):
    """Model not found in provider"""
    
    def __init__(
        self,
        model_id: str,
        provider: Optional[str] = None,
        suggestions: Optional[list] = None
    ):
        self.model_id = model_id
        self.suggestions = suggestions or []
        super().__init__(
            message=f"Model not found: {model_id}",
            provider=provider,
            details={"model_id": model_id, "suggestions": self.suggestions}
        )


class DownloadError(ProviderError):
    """Error during model download"""
    
    def __init__(
        self,
        message: str,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        resumable: bool = False,
        bytes_downloaded: int = 0
    ):
        self.model_id = model_id
        self.resumable = resumable
        self.bytes_downloaded = bytes_downloaded
        super().__init__(
            message=message,
            provider=provider,
            details={
                "model_id": model_id,
                "resumable": resumable,
                "bytes_downloaded": bytes_downloaded
            }
        )


class ValidationError(ProviderError):
    """Model validation failed (checksum, format, etc.)"""
    
    def __init__(
        self,
        message: str,
        model_id: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        provider: Optional[str] = None
    ):
        self.model_id = model_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            message=message,
            provider=provider,
            details={
                "model_id": model_id,
                "expected": expected,
                "actual": actual
            }
        )


class AuthenticationError(ProviderError):
    """Authentication failed"""
    
    def __init__(
        self,
        message: str = "Authentication required",
        provider: Optional[str] = None,
        requires_token: bool = True
    ):
        self.requires_token = requires_token
        super().__init__(
            message=message,
            provider=provider,
            details={"requires_token": requires_token}
        )


class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            provider=provider,
            details={"retry_after": retry_after}
        )


class UnsupportedFormatError(ProviderError):
    """Model format not supported"""
    
    def __init__(
        self,
        format_found: str,
        supported_formats: list,
        provider: Optional[str] = None
    ):
        self.format_found = format_found
        self.supported_formats = supported_formats
        super().__init__(
            message=f"Unsupported format: {format_found}. Supported: {supported_formats}",
            provider=provider,
            details={
                "format_found": format_found,
                "supported_formats": supported_formats
            }
        )


class StorageError(ProviderError):
    """Storage-related error (disk full, permissions, etc.)"""
    
    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        required_space_gb: Optional[float] = None,
        available_space_gb: Optional[float] = None
    ):
        self.path = path
        self.required_space_gb = required_space_gb
        self.available_space_gb = available_space_gb
        super().__init__(
            message=message,
            details={
                "path": path,
                "required_space_gb": required_space_gb,
                "available_space_gb": available_space_gb
            }
        )