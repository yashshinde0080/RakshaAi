"""
Base Provider Interface

Abstract base class defining the interface all model providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncIterator, Callable
from pathlib import Path
from datetime import datetime
from enum import Enum


class ModelFormat(Enum):
    """Supported model formats"""
    GGUF = "gguf"
    GGML = "ggml"
    SAFETENSORS = "safetensors"
    PYTORCH = "pytorch"
    UNKNOWN = "unknown"


class QuantizationType(Enum):
    """Common quantization types"""
    F32 = "F32"
    F16 = "F16"
    Q8_0 = "Q8_0"
    Q6_K = "Q6_K"
    Q5_K_M = "Q5_K_M"
    Q5_K_S = "Q5_K_S"
    Q5_0 = "Q5_0"
    Q4_K_M = "Q4_K_M"
    Q4_K_S = "Q4_K_S"
    Q4_0 = "Q4_0"
    Q3_K_M = "Q3_K_M"
    Q3_K_S = "Q3_K_S"
    Q2_K = "Q2_K"
    IQ4_NL = "IQ4_NL"
    IQ4_XS = "IQ4_XS"
    IQ3_M = "IQ3_M"
    IQ3_S = "IQ3_S"
    IQ2_M = "IQ2_M"
    IQ2_S = "IQ2_S"
    UNKNOWN = "unknown"


@dataclass
class ModelFile:
    """Information about a model file"""
    filename: str
    size_bytes: int
    url: Optional[str] = None
    checksum: Optional[str] = None
    checksum_type: str = "sha256"
    quantization: Optional[QuantizationType] = None
    format: ModelFormat = ModelFormat.UNKNOWN
    
    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 ** 2)


@dataclass
class ModelMetadata:
    """Complete model metadata"""
    id: str
    name: str
    provider: str
    
    # Model info
    family: Optional[str] = None
    parameters: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    author: Optional[str] = None
    
    # Files
    files: List[ModelFile] = field(default_factory=list)
    
    # Technical details
    format: ModelFormat = ModelFormat.UNKNOWN
    quantizations_available: List[QuantizationType] = field(default_factory=list)
    context_length: Optional[int] = None
    embedding_size: Optional[int] = None
    
    # Compatibility
    modes_supported: List[str] = field(default_factory=lambda: ["fullram", "layerstream"])
    min_ram_gb: Optional[float] = None
    recommended_ram_gb: Optional[float] = None
    
    # Source info
    source_url: Optional[str] = None
    repo_id: Optional[str] = None
    revision: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Additional metadata
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def get_file_by_quant(self, quant: str) -> Optional[ModelFile]:
        """Get file matching quantization"""
        quant_upper = quant.upper().replace("-", "_")
        for f in self.files:
            if f.quantization and f.quantization.value.upper() == quant_upper:
                return f
            if quant.lower() in f.filename.lower():
                return f
        return None
    
    def get_best_file(self, max_size_gb: Optional[float] = None) -> Optional[ModelFile]:
        """Get best file within size constraints"""
        valid_files = self.files
        
        if max_size_gb:
            valid_files = [f for f in valid_files if f.size_gb <= max_size_gb]
        
        if not valid_files:
            return None
        
        # Prefer Q4_K_M as default
        for f in valid_files:
            if f.quantization == QuantizationType.Q4_K_M:
                return f
        
        # Return largest that fits
        return max(valid_files, key=lambda f: f.size_bytes)
    
    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)
    
    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 ** 3)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "family": self.family,
            "parameters": self.parameters,
            "description": self.description,
            "license": self.license,
            "author": self.author,
            "format": self.format.value,
            "quantizations_available": [q.value for q in self.quantizations_available],
            "context_length": self.context_length,
            "modes_supported": self.modes_supported,
            "min_ram_gb": self.min_ram_gb,
            "recommended_ram_gb": self.recommended_ram_gb,
            "source_url": self.source_url,
            "repo_id": self.repo_id,
            "files": [
                {
                    "filename": f.filename,
                    "size_bytes": f.size_bytes,
                    "size_gb": f.size_gb,
                    "quantization": f.quantization.value if f.quantization else None,
                    "checksum": f.checksum
                }
                for f in self.files
            ],
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class DownloadProgress:
    """Download progress information"""
    model_id: str
    filename: str
    status: str  # pending, downloading, verifying, complete, error
    
    bytes_downloaded: int = 0
    bytes_total: int = 0
    
    speed_bytes_per_sec: float = 0
    eta_seconds: Optional[float] = None
    
    error: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        if self.bytes_total == 0:
            return 0
        return (self.bytes_downloaded / self.bytes_total) * 100
    
    @property
    def downloaded_gb(self) -> float:
        return self.bytes_downloaded / (1024 ** 3)
    
    @property
    def total_gb(self) -> float:
        return self.bytes_total / (1024 ** 3)
    
    @property
    def speed_mb_per_sec(self) -> float:
        return self.speed_bytes_per_sec / (1024 ** 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "filename": self.filename,
            "status": self.status,
            "progress": self.progress_percent,
            "bytes_downloaded": self.bytes_downloaded,
            "bytes_total": self.bytes_total,
            "downloaded_gb": round(self.downloaded_gb, 3),
            "total_gb": round(self.total_gb, 3),
            "speed_mb_s": round(self.speed_mb_per_sec, 2),
            "eta_seconds": self.eta_seconds,
            "error": self.error
        }


# Type alias for progress callback
ProgressCallback = Callable[[DownloadProgress], None]


class BaseProvider(ABC):
    """
    Abstract base class for model providers.
    
    All providers must implement these methods to integrate with
    the model management system.
    """
    
    # Provider identification
    provider_id: str = "base"
    provider_name: str = "Base Provider"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config or {}
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the provider (authenticate, verify connectivity, etc.)
        
        Returns:
            True if initialization successful
        """
        self._initialized = True
        return True
    
    async def cleanup(self):
        """Cleanup provider resources"""
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelMetadata]:
        """
        Search for models.
        
        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters (format, size, etc.)
            
        Returns:
            List of matching model metadata
        """
        pass
    
    @abstractmethod
    async def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def list_files(self, model_id: str) -> List[ModelFile]:
        """
        List available files for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of available files
        """
        pass
    
    @abstractmethod
    async def download(
        self,
        model_id: str,
        destination: Path,
        filename: Optional[str] = None,
        quantization: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Path:
        """
        Download a model file.
        
        Args:
            model_id: Model identifier
            destination: Destination directory
            filename: Specific file to download (optional)
            quantization: Preferred quantization (optional)
            progress_callback: Progress callback function
            
        Returns:
            Path to downloaded file
        """
        pass
    
    @abstractmethod
    async def verify(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """
        Verify downloaded file integrity.
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum (optional)
            
        Returns:
            True if file is valid
        """
        pass
    
    # ==================== Optional Methods ====================
    
    async def get_download_url(
        self,
        model_id: str,
        filename: str
    ) -> Optional[str]:
        """
        Get direct download URL for a file.
        
        Args:
            model_id: Model identifier
            filename: File name
            
        Returns:
            Download URL or None
        """
        return None
    
    async def check_updates(
        self,
        model_id: str,
        current_revision: Optional[str] = None
    ) -> bool:
        """
        Check if model has updates available.
        
        Args:
            model_id: Model identifier
            current_revision: Current local revision
            
        Returns:
            True if updates available
        """
        return False
    
    async def get_recommended_quantization(
        self,
        model_id: str,
        available_ram_gb: float
    ) -> Optional[str]:
        """
        Get recommended quantization based on available RAM.
        
        Args:
            model_id: Model identifier
            available_ram_gb: Available RAM in GB
            
        Returns:
            Recommended quantization string
        """
        files = await self.list_files(model_id)
        
        # Sort by size descending
        gguf_files = [f for f in files if f.format == ModelFormat.GGUF]
        gguf_files.sort(key=lambda f: f.size_bytes, reverse=True)
        
        for f in gguf_files:
            # Need ~1.4x model size in RAM
            if f.size_gb * 1.4 <= available_ram_gb:
                if f.quantization:
                    return f.quantization.value
        
        # Return smallest if nothing fits
        if gguf_files:
            smallest = min(gguf_files, key=lambda f: f.size_bytes)
            if smallest.quantization:
                return smallest.quantization.value
        
        return "Q4_K_M"  # Default
    
    def supports_resume(self) -> bool:
        """Whether provider supports download resume"""
        return False
    
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming downloads"""
        return True
    
    def requires_authentication(self) -> bool:
        """Whether provider requires authentication"""
        return False
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.provider_id})>"