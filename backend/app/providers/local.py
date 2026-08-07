"""
Local Provider

Manages models stored on the local filesystem.
Used for pre-downloaded models and offline operation.
"""

import os
import json
import hashlib
import aiofiles
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import settings

from app.providers.base import (
    BaseProvider,
    ModelMetadata,
    ModelFile,
    ModelFormat,
    QuantizationType,
    DownloadProgress,
    ProgressCallback
)
from app.providers.exceptions import (
    ModelNotFoundError,
    DownloadError,
    ValidationError,
    StorageError
)


class LocalProvider(BaseProvider):
    """
    Local filesystem model provider.
    
    Manages models stored in a local directory structure.
    """
    
    provider_id = "local"
    provider_name = "Local Storage"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Default to the project models dir (portable USB); config can override.
        self.models_dir = Path(config.get("models_dir", settings.models_dir)) if config else settings.models_dir
        self.installed_dir = self.models_dir / "installed"
        self.cache_dir = self.models_dir / ".cache"
        
        # Metadata cache
        self._metadata_cache: Dict[str, ModelMetadata] = {}
    
    async def initialize(self) -> bool:
        """Initialize directories"""
        self.installed_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing models
        await self._scan_models()
        
        self._initialized = True
        return True
    
    async def cleanup(self):
        """Cleanup resources"""
        self._metadata_cache.clear()
        self._initialized = False
    
    async def _scan_models(self):
        """Scan installed models directory"""
        self._metadata_cache.clear()
        
        if not self.installed_dir.exists():
            return
        
        for model_dir in self.installed_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            metadata_path = model_dir / "metadata.json"
            
            if metadata_path.exists():
                try:
                    async with aiofiles.open(metadata_path, "r") as f:
                        data = json.loads(await f.read())
                    
                    metadata = await self._parse_metadata(data, model_dir)
                    self._metadata_cache[metadata.id] = metadata
                except Exception as e:
                    print(f"Warning: Failed to load metadata for {model_dir.name}: {e}")
                    continue
            else:
                # Try to infer metadata from files
                metadata = await self._infer_metadata(model_dir)
                if metadata:
                    self._metadata_cache[metadata.id] = metadata
    
    async def _parse_metadata(self, data: Dict[str, Any], model_dir: Path) -> ModelMetadata:
        """Parse metadata from JSON"""
        # Get files in directory
        files = await self._scan_model_files(model_dir)
        
        return ModelMetadata(
            id=data.get("id", model_dir.name),
            name=data.get("name", model_dir.name),
            provider=self.provider_id,
            family=data.get("family"),
            parameters=data.get("parameters"),
            description=data.get("description"),
            license=data.get("license"),
            author=data.get("author"),
            format=ModelFormat(data.get("format", "unknown")),
            quantizations_available=[
                QuantizationType(q) for q in data.get("quantizations", [])
            ],
            modes_supported=data.get("modes_supported", ["fullram", "layerstream"]),
            context_length=data.get("context_length"),
            files=files,
            tags=data.get("tags", []),
            source_url=data.get("source_url"),
            repo_id=data.get("repo_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            extra={"local_path": str(model_dir)}
        )
    
    async def _infer_metadata(self, model_dir: Path) -> Optional[ModelMetadata]:
        """Infer metadata from directory contents"""
        files = await self._scan_model_files(model_dir)
        
        if not files:
            return None
        
        # Get main model file
        main_file = max(files, key=lambda f: f.size_bytes)
        
        # Detect format
        model_format = main_file.format
        
        # Extract info from directory name
        name = model_dir.name
        
        return ModelMetadata(
            id=name,
            name=name,
            provider=self.provider_id,
            format=model_format,
            files=files,
            modes_supported=["fullram", "layerstream"],
            extra={"local_path": str(model_dir)}
        )
    
    async def _scan_model_files(self, model_dir: Path) -> List[ModelFile]:
        """Scan directory for model files"""
        files = []
        
        for file_path in model_dir.iterdir():
            if not file_path.is_file():
                continue
            
            # Skip metadata and hidden files
            if file_path.name.startswith(".") or file_path.suffix == ".json":
                continue
            
            # Detect format
            suffix = file_path.suffix.lower()
            if suffix == ".gguf":
                format_type = ModelFormat.GGUF
            elif suffix == ".ggml":
                format_type = ModelFormat.GGML
            elif suffix == ".safetensors":
                format_type = ModelFormat.SAFETENSORS
            elif suffix in (".bin", ".pt", ".pth"):
                format_type = ModelFormat.PYTORCH
            else:
                continue
            
            # Detect quantization from filename
            quantization = self._detect_quantization(file_path.name)
            
            files.append(ModelFile(
                filename=file_path.name,
                size_bytes=file_path.stat().st_size,
                format=format_type,
                quantization=quantization
            ))
        
        return files
    
    def _detect_quantization(self, filename: str) -> Optional[QuantizationType]:
        """Detect quantization from filename"""
        filename_lower = filename.lower()
        
        patterns = {
            "q8_0": QuantizationType.Q8_0,
            "q6_k": QuantizationType.Q6_K,
            "q5_k_m": QuantizationType.Q5_K_M,
            "q5_k_s": QuantizationType.Q5_K_S,
            "q5_0": QuantizationType.Q5_0,
            "q4_k_m": QuantizationType.Q4_K_M,
            "q4_k_s": QuantizationType.Q4_K_S,
            "q4_0": QuantizationType.Q4_0,
            "q3_k_m": QuantizationType.Q3_K_M,
            "q3_k_s": QuantizationType.Q3_K_S,
            "q2_k": QuantizationType.Q2_K,
            "f16": QuantizationType.F16,
            "f32": QuantizationType.F32,
        }
        
        for pattern, quant in patterns.items():
            if pattern in filename_lower:
                return quant
        
        return QuantizationType.UNKNOWN
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelMetadata]:
        """Search local models"""
        await self._scan_models()
        
        query_lower = query.lower()
        results = []
        
        for model_id, metadata in self._metadata_cache.items():
            # Simple text matching
            if (
                query_lower in model_id.lower() or
                query_lower in metadata.name.lower() or
                (metadata.family and query_lower in metadata.family.lower()) or
                any(query_lower in tag.lower() for tag in metadata.tags)
            ):
                results.append(metadata)
        
        # Apply filters
        if filters:
            if filters.get("format"):
                target_format = ModelFormat(filters["format"])
                results = [r for r in results if r.format == target_format]
            
            if filters.get("max_size_gb"):
                max_size = filters["max_size_gb"]
                results = [r for r in results if r.total_size_gb <= max_size]
        
        return results[:limit]
    
    async def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model information"""
        await self._scan_models()
        
        if model_id in self._metadata_cache:
            return self._metadata_cache[model_id]
        
        # Try to find by normalized name
        normalized = model_id.lower().replace(":", "-").replace("/", "-")
        
        for cached_id, metadata in self._metadata_cache.items():
            if cached_id.lower() == normalized:
                return metadata
        
        return None
    
    async def list_files(self, model_id: str) -> List[ModelFile]:
        """List files for a model"""
        metadata = await self.get_model_info(model_id)
        
        if metadata:
            return metadata.files
        
        return []
    
    async def download(
        self,
        model_id: str,
        destination: Path,
        filename: Optional[str] = None,
        quantization: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Path:
        """
        For local provider, this copies/moves files to destination.
        """
        metadata = await self.get_model_info(model_id)
        
        if not metadata:
            raise ModelNotFoundError(model_id, self.provider_id)
        
        source_dir = Path(metadata.extra.get("local_path", ""))
        
        if not source_dir.exists():
            raise ModelNotFoundError(model_id, self.provider_id)
        
        # Select file
        if filename:
            target_file = next((f for f in metadata.files if f.filename == filename), None)
        elif quantization:
            target_file = metadata.get_file_by_quant(quantization)
        else:
            target_file = metadata.get_best_file()
        
        if not target_file:
            raise ModelNotFoundError(model_id, self.provider_id)
        
        source_path = source_dir / target_file.filename
        dest_path = Path(destination) / target_file.filename
        
        # Check if source exists
        if not source_path.exists():
            raise ModelNotFoundError(model_id, self.provider_id)
        
        # Create destination directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check disk space
        file_size = source_path.stat().st_size
        free_space = shutil.disk_usage(dest_path.parent).free
        
        if file_size > free_space:
            raise StorageError(
                message="Insufficient disk space",
                path=str(dest_path),
                required_space_gb=file_size / (1024**3),
                available_space_gb=free_space / (1024**3)
            )
        
        # Copy file with progress
        progress = DownloadProgress(
            model_id=model_id,
            filename=target_file.filename,
            status="downloading",
            bytes_total=file_size,
            bytes_downloaded=0
        )
        
        try:
            chunk_size = 8 * 1024 * 1024  # 8MB
            bytes_copied = 0
            
            async with aiofiles.open(source_path, "rb") as src:
                async with aiofiles.open(dest_path, "wb") as dst:
                    while chunk := await src.read(chunk_size):
                        await dst.write(chunk)
                        bytes_copied += len(chunk)
                        
                        progress.bytes_downloaded = bytes_copied
                        if progress_callback:
                            progress_callback(progress)
            
            progress.status = "complete"
            if progress_callback:
                progress_callback(progress)
            
            return dest_path
            
        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            if progress_callback:
                progress_callback(progress)
            
            # Cleanup partial file
            if dest_path.exists():
                dest_path.unlink()
            
            raise DownloadError(
                message=f"Copy failed: {str(e)}",
                model_id=model_id,
                provider=self.provider_id
            )
    
    async def verify(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """Verify file integrity"""
        if not file_path.exists():
            return False
        
        if not expected_checksum:
            # Just check file exists and has content
            return file_path.stat().st_size > 0
        
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest().lower() == expected_checksum.lower()
    
    async def add_model(
        self,
        source_path: Path,
        model_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModelMetadata:
        """Add a model to local storage"""
        model_dir = self.installed_dir / model_id.replace(":", "-").replace("/", "-")
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy or move file
        if source_path.is_file():
            dest_path = model_dir / source_path.name
            shutil.copy2(source_path, dest_path)
        elif source_path.is_dir():
            for file in source_path.iterdir():
                if file.is_file():
                    shutil.copy2(file, model_dir / file.name)
        
        # Create metadata
        meta = metadata or {}
        meta["id"] = model_id
        meta["name"] = meta.get("name", model_id)
        meta["created_at"] = datetime.now().isoformat()
        
        # Save metadata
        metadata_path = model_dir / "metadata.json"
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(meta, indent=2))
        
        # Refresh cache
        await self._scan_models()
        
        return self._metadata_cache.get(model_id)
    
    async def remove_model(self, model_id: str) -> bool:
        """Remove a model from local storage"""
        metadata = await self.get_model_info(model_id)
        
        if not metadata:
            return False
        
        model_dir = Path(metadata.extra.get("local_path", ""))
        
        if model_dir.exists():
            shutil.rmtree(model_dir)
        
        self._metadata_cache.pop(model_id, None)
        
        return True
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information"""
        usage = shutil.disk_usage(self.models_dir)
        
        total_models_size = sum(
            m.total_size_bytes for m in self._metadata_cache.values()
        )
        
        return {
            "models_dir": str(self.models_dir),
            "total_disk_gb": usage.total / (1024**3),
            "used_disk_gb": usage.used / (1024**3),
            "free_disk_gb": usage.free / (1024**3),
            "models_count": len(self._metadata_cache),
            "models_size_gb": total_models_size / (1024**3)
        }
    
    def supports_resume(self) -> bool:
        return False  # Local copy doesn't support resume