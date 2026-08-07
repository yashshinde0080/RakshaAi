"""
USB Bundle Provider

Handles model bundles from USB drives and portable storage.
Supports encrypted and signed model packages for secure offline distribution.
"""

import asyncio
import aiofiles
import hashlib
import json
import zipfile
import tarfile
import shutil
import struct
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO, Tuple
from datetime import datetime
from dataclasses import dataclass
import os

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


@dataclass
class BundleInfo:
    """Information about a model bundle"""
    path: Path
    format: str  # zip, tar.gz, sovereign
    size_bytes: int
    model_id: str
    metadata: Dict[str, Any]
    checksum: Optional[str] = None
    signature: Optional[bytes] = None
    encrypted: bool = False


class USBBundleProvider(BaseProvider):
    """
    USB/Portable Bundle Provider.
    
    Manages model bundles from removable storage:
    - .zip bundles
    - .tar.gz bundles
    - .sovereign custom encrypted bundles
    
    Bundle structure:
    model_bundle/
    ├── metadata.json
    ├── model.gguf (or model.gguf.enc if encrypted)
    ├── checksum.sha256
    └── signature.sig (optional)
    """
    
    provider_id = "usb_bundle"
    provider_name = "USB Bundle"
    
    # Supported bundle extensions
    BUNDLE_EXTENSIONS = [".zip", ".tar.gz", ".tgz", ".sovereign", ".bundle"]
    
    # Magic bytes for sovereign bundle format
    SOVEREIGN_MAGIC = b"SVAI"
    SOVEREIGN_VERSION = 1
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        self.scan_paths: List[Path] = []
        
        if config:
            # Paths to scan for bundles
            scan_paths = config.get("scan_paths", [])
            self.scan_paths = [Path(p) for p in scan_paths]
            
            # Encryption key (for encrypted bundles)
            self.encryption_key = config.get("encryption_key")
            
            # Signature verification key
            self.verify_key = config.get("verify_key")
        
        # Cache of discovered bundles
        self._bundles: Dict[str, BundleInfo] = {}
    
    async def initialize(self) -> bool:
        """Initialize and scan for bundles"""
        await self._scan_bundles()
        self._initialized = True
        return True
    
    async def cleanup(self):
        """Cleanup"""
        self._bundles.clear()
        self._initialized = False
    
    def add_scan_path(self, path: Path):
        """Add a path to scan for bundles"""
        path = Path(path)
        if path not in self.scan_paths:
            self.scan_paths.append(path)
    
    def remove_scan_path(self, path: Path):
        """Remove a scan path"""
        path = Path(path)
        if path in self.scan_paths:
            self.scan_paths.remove(path)
    
    async def refresh(self):
        """Refresh bundle list"""
        await self._scan_bundles()
    
    async def _scan_bundles(self):
        """Scan all paths for model bundles"""
        self._bundles.clear()
        
        for scan_path in self.scan_paths:
            if not scan_path.exists():
                continue
            
            # Scan for bundle files
            for ext in self.BUNDLE_EXTENSIONS:
                pattern = f"*{ext}"
                for bundle_path in scan_path.glob(pattern):
                    if bundle_path.is_file():
                        try:
                            bundle_info = await self._parse_bundle(bundle_path)
                            if bundle_info:
                                self._bundles[bundle_info.model_id] = bundle_info
                        except Exception as e:
                            print(f"Warning: Failed to parse bundle {bundle_path}: {e}")
            
            # Also scan for unpacked bundle directories
            for subdir in scan_path.iterdir():
                if subdir.is_dir():
                    metadata_path = subdir / "metadata.json"
                    if metadata_path.exists():
                        try:
                            bundle_info = await self._parse_directory_bundle(subdir)
                            if bundle_info:
                                self._bundles[bundle_info.model_id] = bundle_info
                        except Exception as e:
                            print(f"Warning: Failed to parse directory bundle {subdir}: {e}")
    
    async def _parse_bundle(self, bundle_path: Path) -> Optional[BundleInfo]:
        """Parse bundle file and extract metadata"""
        suffix_lower = "".join(bundle_path.suffixes).lower()
        
        try:
            if suffix_lower == ".zip":
                return await self._parse_zip_bundle(bundle_path)
            elif suffix_lower in (".tar.gz", ".tgz"):
                return await self._parse_tar_bundle(bundle_path)
            elif suffix_lower == ".sovereign":
                return await self._parse_sovereign_bundle(bundle_path)
            elif suffix_lower == ".bundle":
                return await self._parse_generic_bundle(bundle_path)
        except Exception as e:
            print(f"Warning: Failed to parse bundle {bundle_path}: {e}")
        
        return None
    
    async def _parse_zip_bundle(self, bundle_path: Path) -> Optional[BundleInfo]:
        """Parse ZIP bundle"""
        try:
            with zipfile.ZipFile(bundle_path, 'r') as zf:
                # Look for metadata.json
                metadata = {}
                checksum = None
                
                for name in zf.namelist():
                    basename = os.path.basename(name)
                    
                    if basename == "metadata.json":
                        with zf.open(name) as f:
                            metadata = json.loads(f.read().decode('utf-8'))
                    
                    elif basename == "checksum.sha256":
                        with zf.open(name) as f:
                            checksum = f.read().decode('utf-8').strip().split()[0]
                
                if not metadata:
                    # Try to infer from filename
                    model_id = bundle_path.stem
                    metadata = {"id": model_id, "name": model_id}
                
                return BundleInfo(
                    path=bundle_path,
                    format="zip",
                    size_bytes=bundle_path.stat().st_size,
                    model_id=metadata.get("id", bundle_path.stem),
                    metadata=metadata,
                    checksum=checksum,
                    encrypted=metadata.get("encrypted", False)
                )
        except zipfile.BadZipFile:
            return None
    
    async def _parse_tar_bundle(self, bundle_path: Path) -> Optional[BundleInfo]:
        """Parse TAR.GZ bundle"""
        try:
            with tarfile.open(bundle_path, 'r:gz') as tf:
                metadata = {}
                checksum = None
                
                for member in tf.getmembers():
                    basename = os.path.basename(member.name)
                    
                    if basename == "metadata.json":
                        f = tf.extractfile(member)
                        if f:
                            metadata = json.loads(f.read().decode('utf-8'))
                    
                    elif basename == "checksum.sha256":
                        f = tf.extractfile(member)
                        if f:
                            checksum = f.read().decode('utf-8').strip().split()[0]
                
                if not metadata:
                    model_id = bundle_path.stem.replace(".tar", "")
                    metadata = {"id": model_id, "name": model_id}
                
                return BundleInfo(
                    path=bundle_path,
                    format="tar.gz",
                    size_bytes=bundle_path.stat().st_size,
                    model_id=metadata.get("id", bundle_path.stem),
                    metadata=metadata,
                    checksum=checksum,
                    encrypted=metadata.get("encrypted", False)
                )
        except tarfile.TarError:
            return None
    
    async def _parse_sovereign_bundle(self, bundle_path: Path) -> Optional[BundleInfo]:
        """
        Parse custom .sovereign bundle format.
        
        Sovereign Bundle Format:
        - 4 bytes: Magic ("SVAI")
        - 1 byte: Version
        - 1 byte: Flags (bit 0: encrypted, bit 1: signed)
        - 4 bytes: Metadata length
        - N bytes: Metadata (JSON)
        - 32 bytes: Model checksum (SHA256)
        - 64 bytes: Signature (optional, if signed)
        - Rest: Model data (possibly encrypted)
        """
        async with aiofiles.open(bundle_path, 'rb') as f:
            # Read header
            magic = await f.read(4)
            if magic != self.SOVEREIGN_MAGIC:
                return None
            
            version = struct.unpack('B', await f.read(1))[0]
            if version > self.SOVEREIGN_VERSION:
                print(f"Warning: Unsupported sovereign bundle version: {version}")
                return None
            
            flags = struct.unpack('B', await f.read(1))[0]
            is_encrypted = bool(flags & 0x01)
            is_signed = bool(flags & 0x02)
            
            metadata_length = struct.unpack('>I', await f.read(4))[0]
            metadata_bytes = await f.read(metadata_length)
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            
            checksum = (await f.read(32)).hex()
            
            signature = None
            if is_signed:
                signature = await f.read(64)
            
            return BundleInfo(
                path=bundle_path,
                format="sovereign",
                size_bytes=bundle_path.stat().st_size,
                model_id=metadata.get("id", bundle_path.stem),
                metadata=metadata,
                checksum=checksum,
                signature=signature,
                encrypted=is_encrypted
            )
    
    async def _parse_generic_bundle(self, bundle_path: Path) -> Optional[BundleInfo]:
        """Parse generic .bundle file (try as zip first, then tar)"""
        result = await self._parse_zip_bundle(bundle_path)
        if result:
            return result
        
        result = await self._parse_tar_bundle(bundle_path)
        if result:
            return result
        
        return None
    
    async def _parse_directory_bundle(self, dir_path: Path) -> Optional[BundleInfo]:
        """Parse unpacked bundle directory"""
        metadata_path = dir_path / "metadata.json"
        
        if not metadata_path.exists():
            return None
        
        async with aiofiles.open(metadata_path, 'r') as f:
            metadata = json.loads(await f.read())
        
        # Look for checksum
        checksum = None
        checksum_path = dir_path / "checksum.sha256"
        if checksum_path.exists():
            async with aiofiles.open(checksum_path, 'r') as f:
                checksum = (await f.read()).strip().split()[0]
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size for f in dir_path.rglob("*") if f.is_file()
        )
        
        return BundleInfo(
            path=dir_path,
            format="directory",
            size_bytes=total_size,
            model_id=metadata.get("id", dir_path.name),
            metadata=metadata,
            checksum=checksum,
            encrypted=metadata.get("encrypted", False)
        )
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelMetadata]:
        """Search for bundles"""
        await self._scan_bundles()
        
        query_lower = query.lower()
        results = []
        
        for model_id, bundle in self._bundles.items():
            # Simple text matching
            name = bundle.metadata.get("name", model_id)
            family = bundle.metadata.get("family", "")
            tags = bundle.metadata.get("tags", [])
            
            if (
                query_lower in model_id.lower() or
                query_lower in name.lower() or
                query_lower in family.lower() or
                any(query_lower in tag.lower() for tag in tags)
            ):
                metadata = self._bundle_to_metadata(bundle)
                results.append(metadata)
        
        return results[:limit]
    
    async def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model information from bundle"""
        await self._scan_bundles()
        
        bundle = self._bundles.get(model_id)
        
        if not bundle:
            # Try normalized name
            normalized = model_id.lower().replace(":", "-").replace("/", "-")
            for bid, b in self._bundles.items():
                if bid.lower() == normalized:
                    bundle = b
                    break
        
        if bundle:
            return self._bundle_to_metadata(bundle)
        
        return None
    
    def _bundle_to_metadata(self, bundle: BundleInfo) -> ModelMetadata:
        """Convert BundleInfo to ModelMetadata"""
        meta = bundle.metadata
        
        # Get files from metadata or scan bundle
        files = []
        
        for file_data in meta.get("files", []):
            files.append(ModelFile(
                filename=file_data.get("filename", ""),
                size_bytes=file_data.get("size_bytes", 0),
                checksum=file_data.get("checksum"),
                format=ModelFormat(file_data.get("format", "gguf")),
                quantization=QuantizationType(file_data.get("quantization", "unknown"))
                    if file_data.get("quantization") else None
            ))
        
        # If no files in metadata, create one for the main model
        if not files:
            files.append(ModelFile(
                filename=f"{bundle.model_id}.gguf",
                size_bytes=bundle.size_bytes,
                checksum=bundle.checksum,
                format=ModelFormat.GGUF
            ))
        
        return ModelMetadata(
            id=bundle.model_id,
            name=meta.get("name", bundle.model_id),
            provider=self.provider_id,
            family=meta.get("family"),
            parameters=meta.get("parameters"),
            description=meta.get("description"),
            license=meta.get("license"),
            author=meta.get("author"),
            format=ModelFormat(meta.get("format", "gguf")),
            files=files,
            quantizations_available=[
                QuantizationType(q) for q in meta.get("quantizations", [])
            ],
            modes_supported=meta.get("modes_supported", ["fullram", "layerstream"]),
            context_length=meta.get("context_length"),
            tags=meta.get("tags", []),
            extra={
                "bundle_path": str(bundle.path),
                "bundle_format": bundle.format,
                "encrypted": bundle.encrypted
            }
        )
    
    async def list_files(self, model_id: str) -> List[ModelFile]:
        """List files in bundle"""
        info = await self.get_model_info(model_id)
        return info.files if info else []
    
    async def download(
        self,
        model_id: str,
        destination: Path,
        filename: Optional[str] = None,
        quantization: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Path:
        """
        Extract model from bundle to destination.
        
        For USB bundles, "download" means extract.
        """
        bundle = self._bundles.get(model_id)
        
        if not bundle:
            raise ModelNotFoundError(model_id, self.provider_id)
        
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        
        progress = DownloadProgress(
            model_id=model_id,
            filename=filename or f"{model_id}.gguf",
            status="downloading",
            bytes_total=bundle.size_bytes
        )
        
        try:
            if bundle.format == "zip":
                output_path = await self._extract_zip(
                    bundle, destination, filename, quantization, progress, progress_callback
                )
            elif bundle.format == "tar.gz":
                output_path = await self._extract_tar(
                    bundle, destination, filename, quantization, progress, progress_callback
                )
            elif bundle.format == "sovereign":
                output_path = await self._extract_sovereign(
                    bundle, destination, filename, progress, progress_callback
                )
            elif bundle.format == "directory":
                output_path = await self._copy_from_directory(
                    bundle, destination, filename, quantization, progress, progress_callback
                )
            else:
                raise DownloadError(
                    message=f"Unsupported bundle format: {bundle.format}",
                    model_id=model_id,
                    provider=self.provider_id
                )
            
            # Verify if checksum available
            progress.status = "verifying"
            if progress_callback:
                progress_callback(progress)
            
            if bundle.checksum:
                is_valid = await self.verify(output_path, bundle.checksum)
                if not is_valid:
                    output_path.unlink()
                    raise ValidationError(
                        message="Checksum verification failed",
                        model_id=model_id,
                        provider=self.provider_id
                    )
            
            progress.status = "complete"
            progress.bytes_downloaded = progress.bytes_total
            if progress_callback:
                progress_callback(progress)
            
            return output_path
            
        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            if progress_callback:
                progress_callback(progress)
            raise
    
    async def _extract_zip(
        self,
        bundle: BundleInfo,
        destination: Path,
        filename: Optional[str],
        quantization: Optional[str],
        progress: DownloadProgress,
        callback: Optional[ProgressCallback]
    ) -> Path:
        """Extract from ZIP bundle"""
        with zipfile.ZipFile(bundle.path, 'r') as zf:
            # Find the model file
            model_file = None
            
            for name in zf.namelist():
                basename = os.path.basename(name)
                
                # Skip metadata files
                if basename in ("metadata.json", "checksum.sha256", "signature.sig"):
                    continue
                
                # Match by filename or quantization
                if filename and basename == filename:
                    model_file = name
                    break
                elif quantization and quantization.lower() in basename.lower():
                    model_file = name
                    break
                elif basename.endswith(".gguf"):
                    model_file = name
            
            if not model_file:
                raise ModelNotFoundError(bundle.model_id, self.provider_id)
            
            # Get file info
            info = zf.getinfo(model_file)
            progress.bytes_total = info.file_size
            progress.filename = os.path.basename(model_file)
            
            # Extract with progress
            output_path = destination / os.path.basename(model_file)
            
            with zf.open(model_file) as src:
                async with aiofiles.open(output_path, 'wb') as dst:
                    chunk_size = 8 * 1024 * 1024
                    
                    while True:
                        chunk = src.read(chunk_size)
                        if not chunk:
                            break
                        
                        await dst.write(chunk)
                        progress.bytes_downloaded += len(chunk)
                        
                        if callback:
                            callback(progress)
            
            return output_path
    
    async def _extract_tar(
        self,
        bundle: BundleInfo,
        destination: Path,
        filename: Optional[str],
        quantization: Optional[str],
        progress: DownloadProgress,
        callback: Optional[ProgressCallback]
    ) -> Path:
        """Extract from TAR.GZ bundle"""
        with tarfile.open(bundle.path, 'r:gz') as tf:
            # Find the model file
            model_member = None
            
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                
                basename = os.path.basename(member.name)
                
                # Skip metadata files
                if basename in ("metadata.json", "checksum.sha256", "signature.sig"):
                    continue
                
                # Match by filename or quantization
                if filename and basename == filename:
                    model_member = member
                    break
                elif quantization and quantization.lower() in basename.lower():
                    model_member = member
                    break
                elif basename.endswith(".gguf"):
                    model_member = member
            
            if not model_member:
                raise ModelNotFoundError(bundle.model_id, self.provider_id)
            
            progress.bytes_total = model_member.size
            progress.filename = os.path.basename(model_member.name)
            
            # Extract with progress
            output_path = destination / os.path.basename(model_member.name)
            
            src = tf.extractfile(model_member)
            if not src:
                raise DownloadError(
                    message="Failed to extract file from archive",
                    model_id=bundle.model_id,
                    provider=self.provider_id
                )
            
            async with aiofiles.open(output_path, 'wb') as dst:
                chunk_size = 8 * 1024 * 1024
                
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    
                    await dst.write(chunk)
                    progress.bytes_downloaded += len(chunk)
                    
                    if callback:
                        callback(progress)
            
            return output_path
    
    async def _extract_sovereign(
        self,
        bundle: BundleInfo,
        destination: Path,
        filename: Optional[str],
        progress: DownloadProgress,
        callback: Optional[ProgressCallback]
    ) -> Path:
        """Extract from sovereign bundle format"""
        output_filename = filename or f"{bundle.model_id}.gguf"
        output_path = destination / output_filename
        
        async with aiofiles.open(bundle.path, 'rb') as f:
            # Skip header
            await f.read(4)  # Magic
            await f.read(1)  # Version
            flags = struct.unpack('B', await f.read(1))[0]
            is_encrypted = bool(flags & 0x01)
            is_signed = bool(flags & 0x02)
            
            metadata_length = struct.unpack('>I', await f.read(4))[0]
            await f.read(metadata_length)  # Skip metadata
            await f.read(32)  # Skip checksum
            
            if is_signed:
                await f.read(64)  # Skip signature
            
            # Calculate model data size
            current_pos = await f.tell() if hasattr(f, 'tell') else (
                4 + 1 + 1 + 4 + metadata_length + 32 + (64 if is_signed else 0)
            )
            model_size = bundle.size_bytes - current_pos
            progress.bytes_total = model_size
            
            # Read and write model data
            if is_encrypted and self.encryption_key:
                # Decrypt as we read
                output_path = await self._extract_encrypted_data(
                    f, output_path, model_size, progress, callback
                )
            else:
                async with aiofiles.open(output_path, 'wb') as dst:
                    chunk_size = 8 * 1024 * 1024
                    bytes_read = 0
                    
                    while bytes_read < model_size:
                        to_read = min(chunk_size, model_size - bytes_read)
                        chunk = await f.read(to_read)
                        
                        if not chunk:
                            break
                        
                        await dst.write(chunk)
                        bytes_read += len(chunk)
                        progress.bytes_downloaded = bytes_read
                        
                        if callback:
                            callback(progress)
        
        return output_path
    
    async def _extract_encrypted_data(
        self,
        src,
        output_path: Path,
        size: int,
        progress: DownloadProgress,
        callback: Optional[ProgressCallback]
    ) -> Path:
        """Extract and decrypt data"""
        try:
            from cryptography.fernet import Fernet
            
            # Derive key from encryption key
            import base64
            import hashlib
            
            key_hash = hashlib.sha256(self.encryption_key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_hash)
            fernet = Fernet(fernet_key)
            
            # Read all encrypted data
            encrypted_data = await src.read(size)
            
            # Decrypt
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Write decrypted data
            async with aiofiles.open(output_path, 'wb') as dst:
                await dst.write(decrypted_data)
            
            progress.bytes_downloaded = len(decrypted_data)
            if callback:
                callback(progress)
            
            return output_path
            
        except ImportError:
            raise DownloadError(
                message="cryptography package required for encrypted bundles",
                provider=self.provider_id
            )
    
    async def _copy_from_directory(
        self,
        bundle: BundleInfo,
        destination: Path,
        filename: Optional[str],
        quantization: Optional[str],
        progress: DownloadProgress,
        callback: Optional[ProgressCallback]
    ) -> Path:
        """Copy model from unpacked directory bundle"""
        source_dir = bundle.path
        
        # Find model file
        model_file = None
        
        for file_path in source_dir.iterdir():
            if not file_path.is_file():
                continue
            
            if file_path.name in ("metadata.json", "checksum.sha256", "signature.sig"):
                continue
            
            if filename and file_path.name == filename:
                model_file = file_path
                break
            elif quantization and quantization.lower() in file_path.name.lower():
                model_file = file_path
                break
            elif file_path.suffix == ".gguf":
                model_file = file_path
        
        if not model_file:
            raise ModelNotFoundError(bundle.model_id, self.provider_id)
        
        progress.bytes_total = model_file.stat().st_size
        progress.filename = model_file.name
        
        output_path = destination / model_file.name
        
        # Copy with progress
        async with aiofiles.open(model_file, 'rb') as src:
            async with aiofiles.open(output_path, 'wb') as dst:
                chunk_size = 8 * 1024 * 1024
                
                while True:
                    chunk = await src.read(chunk_size)
                    if not chunk:
                        break
                    
                    await dst.write(chunk)
                    progress.bytes_downloaded += len(chunk)
                    
                    if callback:
                        callback(progress)
        
        return output_path
    
    async def verify(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """Verify file checksum"""
        if not expected_checksum:
            return True
        
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest().lower() == expected_checksum.lower()
    
    async def create_bundle(
        self,
        model_path: Path,
        output_path: Path,
        metadata: Dict[str, Any],
        format: str = "zip",
        encrypt: bool = False,
        sign: bool = False
    ) -> Path:
        """
        Create a model bundle for distribution.
        
        Args:
            model_path: Path to model file
            output_path: Output bundle path
            metadata: Model metadata
            format: Bundle format (zip, tar.gz, sovereign)
            encrypt: Whether to encrypt the model
            sign: Whether to sign the bundle
            
        Returns:
            Path to created bundle
        """
        if format == "zip":
            return await self._create_zip_bundle(
                model_path, output_path, metadata
            )
        elif format == "tar.gz":
            return await self._create_tar_bundle(
                model_path, output_path, metadata
            )
        elif format == "sovereign":
            return await self._create_sovereign_bundle(
                model_path, output_path, metadata, encrypt, sign
            )
        else:
            raise ValueError(f"Unsupported bundle format: {format}")
    
    async def _create_zip_bundle(
        self,
        model_path: Path,
        output_path: Path,
        metadata: Dict[str, Any]
    ) -> Path:
        """Create ZIP bundle"""
        output_path = output_path.with_suffix(".zip")
        
        # Calculate checksum
        sha256 = hashlib.sha256()
        async with aiofiles.open(model_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add model file
            zf.write(model_path, model_path.name)
            
            # Add metadata
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Add checksum
            zf.writestr("checksum.sha256", f"{checksum}  {model_path.name}\n")
        
        return output_path
    
    async def _create_tar_bundle(
        self,
        model_path: Path,
        output_path: Path,
        metadata: Dict[str, Any]
    ) -> Path:
        """Create TAR.GZ bundle"""
        output_path = output_path.with_suffix(".tar.gz")
        
        # Calculate checksum
        sha256 = hashlib.sha256()
        async with aiofiles.open(model_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        
        with tarfile.open(output_path, 'w:gz') as tf:
            # Add model file
            tf.add(model_path, model_path.name)
            
            # Add metadata
            metadata_bytes = json.dumps(metadata, indent=2).encode('utf-8')
            metadata_info = tarfile.TarInfo(name="metadata.json")
            metadata_info.size = len(metadata_bytes)
            tf.addfile(metadata_info, fileobj=__import__('io').BytesIO(metadata_bytes))
            
            # Add checksum
            checksum_bytes = f"{checksum}  {model_path.name}\n".encode('utf-8')
            checksum_info = tarfile.TarInfo(name="checksum.sha256")
            checksum_info.size = len(checksum_bytes)
            tf.addfile(checksum_info, fileobj=__import__('io').BytesIO(checksum_bytes))
        
        return output_path
    
    async def _create_sovereign_bundle(
        self,
        model_path: Path,
        output_path: Path,
        metadata: Dict[str, Any],
        encrypt: bool = False,
        sign: bool = False
    ) -> Path:
        """Create sovereign bundle format"""
        output_path = output_path.with_suffix(".sovereign")
        
        # Calculate checksum
        sha256 = hashlib.sha256()
        async with aiofiles.open(model_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        checksum_bytes = bytes.fromhex(sha256.hexdigest())
        
        # Prepare metadata
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        
        # Flags
        flags = 0
        if encrypt:
            flags |= 0x01
        if sign:
            flags |= 0x02
        
        async with aiofiles.open(output_path, 'wb') as f:
            # Write header
            await f.write(self.SOVEREIGN_MAGIC)
            await f.write(struct.pack('B', self.SOVEREIGN_VERSION))
            await f.write(struct.pack('B', flags))
            await f.write(struct.pack('>I', len(metadata_bytes)))
            await f.write(metadata_bytes)
            await f.write(checksum_bytes)
            
            # Signature placeholder (if signing)
            if sign:
                # TODO: Implement actual signing
                await f.write(b'\x00' * 64)
            
            # Write model data
            async with aiofiles.open(model_path, 'rb') as model_file:
                if encrypt and self.encryption_key:
                    # Encrypt model data
                    data = await model_file.read()
                    encrypted = await self._encrypt_data(data)
                    await f.write(encrypted)
                else:
                    # Write raw data
                    while chunk := await model_file.read(8 * 1024 * 1024):
                        await f.write(chunk)
        
        return output_path
    
    async def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using encryption key"""
        try:
            from cryptography.fernet import Fernet
            import base64
            
            key_hash = hashlib.sha256(self.encryption_key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_hash)
            fernet = Fernet(fernet_key)
            
            return fernet.encrypt(data)
        except ImportError:
            raise RuntimeError("cryptography package required for encryption")
    
    def supports_resume(self) -> bool:
        return False
    
    async def get_available_drives(self) -> List[Dict[str, Any]]:
        """Get list of available USB/removable drives"""
        import platform
        
        drives = []
        
        if platform.system() == "Windows":
            import ctypes
            import string
            
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive_path = f"{letter}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    
                    # 2 = Removable, 3 = Fixed, 4 = Network, 5 = CD-ROM, 6 = RAM disk
                    if drive_type == 2:  # Removable
                        try:
                            usage = shutil.disk_usage(drive_path)
                            drives.append({
                                "path": drive_path,
                                "type": "removable",
                                "total_gb": usage.total / (1024**3),
                                "free_gb": usage.free / (1024**3)
                            })
                        except:
                            pass
                
                bitmask >>= 1
        
        elif platform.system() == "Linux":
            # Check /media and /mnt for mounted drives
            for mount_point in ["/media", "/mnt"]:
                mount_path = Path(mount_point)
                if mount_path.exists():
                    for user_dir in mount_path.iterdir():
                        if user_dir.is_dir():
                            for drive in user_dir.iterdir():
                                if drive.is_dir():
                                    try:
                                        usage = shutil.disk_usage(drive)
                                        drives.append({
                                            "path": str(drive),
                                            "type": "removable",
                                            "total_gb": usage.total / (1024**3),
                                            "free_gb": usage.free / (1024**3)
                                        })
                                    except:
                                        pass
        
        elif platform.system() == "Darwin":  # macOS
            volumes_path = Path("/Volumes")
            if volumes_path.exists():
                for volume in volumes_path.iterdir():
                    if volume.is_dir() and volume.name != "Macintosh HD":
                        try:
                            usage = shutil.disk_usage(volume)
                            drives.append({
                                "path": str(volume),
                                "type": "removable",
                                "total_gb": usage.total / (1024**3),
                                "free_gb": usage.free / (1024**3)
                            })
                        except:
                            pass
        
        return drives