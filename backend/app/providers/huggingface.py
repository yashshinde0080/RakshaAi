"""
HuggingFace Provider

Downloads models from HuggingFace Hub.
Supports GGUF models from TheBloke and other quantized model repos.
"""

import asyncio
import aiohttp
import aiofiles
import hashlib
import os
import re
import ssl
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

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
    AuthenticationError,
    RateLimitError
)


class HuggingFaceProvider(BaseProvider):
    """
    HuggingFace Hub model provider.
    
    Fetches GGUF quantized models from HuggingFace repositories.
    """
    
    provider_id = "huggingface"
    provider_name = "HuggingFace Hub"
    
    API_BASE = "https://huggingface.co/api"
    DOWNLOAD_BASE = "https://huggingface.co"
    
    # Common GGUF repos patterns
    GGUF_REPO_PATTERNS = [
        r".*-GGUF$",
        r".*-gguf$",
        r".*\.gguf$"
    ]
    
    # Quantization patterns in filenames
    QUANT_PATTERNS = {
        QuantizationType.F32: [r"[._-]f32[._-]", r"[._-]fp32[._-]"],
        QuantizationType.F16: [r"[._-]f16[._-]", r"[._-]fp16[._-]"],
        QuantizationType.Q8_0: [r"[._-]q8[._-]?0[._-]", r"[._-]Q8_0"],
        QuantizationType.Q6_K: [r"[._-]q6[._-]?k[._-]", r"[._-]Q6_K"],
        QuantizationType.Q5_K_M: [r"[._-]q5[._-]?k[._-]?m[._-]", r"[._-]Q5_K_M"],
        QuantizationType.Q5_K_S: [r"[._-]q5[._-]?k[._-]?s[._-]", r"[._-]Q5_K_S"],
        QuantizationType.Q5_0: [r"[._-]q5[._-]?0[._-]", r"[._-]Q5_0"],
        QuantizationType.Q4_K_M: [r"[._-]q4[._-]?k[._-]?m[._-]", r"[._-]Q4_K_M"],
        QuantizationType.Q4_K_S: [r"[._-]q4[._-]?k[._-]?s[._-]", r"[._-]Q4_K_S"],
        QuantizationType.Q4_0: [r"[._-]q4[._-]?0[._-]", r"[._-]Q4_0"],
        QuantizationType.Q3_K_M: [r"[._-]q3[._-]?k[._-]?m[._-]", r"[._-]Q3_K_M"],
        QuantizationType.Q3_K_S: [r"[._-]q3[._-]?k[._-]?s[._-]", r"[._-]Q3_K_S"],
        QuantizationType.Q2_K: [r"[._-]q2[._-]?k[._-]", r"[._-]Q2_K"],
        QuantizationType.IQ4_NL: [r"[._-]iq4[._-]?nl[._-]", r"[._-]IQ4_NL"],
        QuantizationType.IQ4_XS: [r"[._-]iq4[._-]?xs[._-]", r"[._-]IQ4_XS"],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.token = config.get("token") if config else None
        self.mirror = config.get("mirror") if config else None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize HTTP session with optional custom CA bundle."""
        headers = {
            "User-Agent": "SovereignAI/1.0"
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        ca_bundle = os.environ.get("SOVEREIGN_CA_BUNDLE")
        if ca_bundle:
            ssl_context = ssl.create_default_context(cafile=ca_bundle)
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        else:
            connector = aiohttp.TCPConnector()

        self._session = aiohttp.ClientSession(headers=headers, connector=connector)
        self._initialized = True
        return True
    
    async def cleanup(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
    
    def _get_api_url(self, endpoint: str) -> str:
        """Get API URL with optional mirror"""
        base = self.mirror or self.API_BASE
        return f"{base}{endpoint}"
    
    def _get_download_url(self, repo_id: str, filename: str, revision: str = "main") -> str:
        """Get download URL for a file"""
        base = self.mirror or self.DOWNLOAD_BASE
        return f"{base}/{repo_id}/resolve/{revision}/{filename}"
    
    def _detect_quantization(self, filename: str) -> Optional[QuantizationType]:
        """Detect quantization from filename"""
        filename_lower = filename.lower()
        
        for quant, patterns in self.QUANT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return quant
        
        return QuantizationType.UNKNOWN
    
    def _detect_format(self, filename: str) -> ModelFormat:
        """Detect model format from filename"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(".gguf"):
            return ModelFormat.GGUF
        elif filename_lower.endswith(".ggml"):
            return ModelFormat.GGML
        elif filename_lower.endswith(".safetensors"):
            return ModelFormat.SAFETENSORS
        elif filename_lower.endswith(".bin") or filename_lower.endswith(".pt"):
            return ModelFormat.PYTORCH
        
        return ModelFormat.UNKNOWN
    
    def _parse_model_name(self, model_id: str) -> tuple:
        """Parse model ID into family and size"""
        # Handle formats like "llama3:8b" or "meta-llama/Meta-Llama-3-8B"
        if ":" in model_id:
            parts = model_id.split(":")
            family = parts[0].lower()
            size = parts[1].lower() if len(parts) > 1 else ""
        elif "/" in model_id:
            repo_name = model_id.split("/")[-1]
            # Extract family and size from repo name
            family = repo_name.lower()
            size = ""
            
            # Try to extract size
            size_match = re.search(r"(\d+[bB])", repo_name)
            if size_match:
                size = size_match.group(1).lower()
        else:
            family = model_id.lower()
            size = ""
        
        return family, size
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelMetadata]:
        """
        Search for models on HuggingFace.
        
        Prioritizes GGUF repositories.
        """
        if not self._session:
            await self.initialize()
        
        # Build search query
        search_params = {
            "search": query,
            "limit": limit * 2,  # Fetch more to filter
            "filter": "gguf",
            "sort": "downloads",
            "direction": -1
        }
        
        # Add filters
        if filters:
            if filters.get("author"):
                search_params["author"] = filters["author"]
        
        try:
            url = self._get_api_url("/models")
            async with self._session.get(url, params=search_params) as response:
                if response.status == 401:
                    raise AuthenticationError(provider=self.provider_id)
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        provider=self.provider_id,
                        retry_after=int(retry_after) if retry_after else None
                    )
                elif response.status != 200:
                    return []
                
                data = await response.json()
        except aiohttp.ClientError as e:
            raise DownloadError(
                message=f"Search failed: {str(e)}",
                provider=self.provider_id
            )
        
        results = []
        
        for item in data[:limit]:
            repo_id = item.get("id", "")
            
            # Check if GGUF repo
            is_gguf = any(
                re.match(pattern, repo_id)
                for pattern in self.GGUF_REPO_PATTERNS
            ) or "gguf" in repo_id.lower()
            
            if not is_gguf:
                continue
            
            metadata = ModelMetadata(
                id=repo_id,
                name=repo_id.split("/")[-1],
                provider=self.provider_id,
                author=item.get("author"),
                description=item.get("description"),
                license=item.get("license"),
                tags=item.get("tags", []),
                source_url=f"https://huggingface.co/{repo_id}",
                repo_id=repo_id,
                format=ModelFormat.GGUF,
                updated_at=datetime.fromisoformat(item["lastModified"].replace("Z", "+00:00"))
                    if item.get("lastModified") else None
            )
            
            results.append(metadata)
        
        return results
    
    async def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """Get detailed model information"""
        if not self._session:
            await self.initialize()
        
        # Handle short-form model IDs
        repo_id = model_id
        if ":" in model_id:
            # Convert "llama3:8b" to search query
            family, size = self._parse_model_name(model_id)
            search_results = await self.search(f"{family} {size} GGUF", limit=5)
            
            if search_results:
                repo_id = search_results[0].repo_id
            else:
                raise ModelNotFoundError(model_id, self.provider_id)
        
        try:
            url = self._get_api_url(f"/models/{repo_id}")
            async with self._session.get(url) as response:
                if response.status == 404:
                    raise ModelNotFoundError(model_id, self.provider_id)
                elif response.status == 401:
                    raise AuthenticationError(provider=self.provider_id)
                elif response.status != 200:
                    return None
                
                data = await response.json()
        except aiohttp.ClientError as e:
            raise DownloadError(
                message=f"Failed to get model info: {str(e)}",
                model_id=model_id,
                provider=self.provider_id
            )
        
        # Get files
        files = await self.list_files(repo_id)
        
        # Extract quantizations
        quantizations = list(set(
            f.quantization for f in files
            if f.quantization and f.quantization != QuantizationType.UNKNOWN
        ))
        
        # Parse family and parameters
        family, params = self._parse_model_name(repo_id)
        
        metadata = ModelMetadata(
            id=model_id,
            name=data.get("id", "").split("/")[-1],
            provider=self.provider_id,
            family=family,
            parameters=params or data.get("config", {}).get("model_type"),
            author=data.get("author"),
            description=data.get("description") or data.get("cardData", {}).get("description"),
            license=data.get("license") or data.get("cardData", {}).get("license"),
            tags=data.get("tags", []),
            source_url=f"https://huggingface.co/{repo_id}",
            repo_id=repo_id,
            format=ModelFormat.GGUF,
            files=files,
            quantizations_available=quantizations,
            context_length=data.get("config", {}).get("max_position_embeddings"),
            updated_at=datetime.fromisoformat(data["lastModified"].replace("Z", "+00:00"))
                if data.get("lastModified") else None,
            extra={"downloads": data.get("downloads", 0)}
        )
        
        return metadata
    
    async def list_files(self, model_id: str) -> List[ModelFile]:
        """List available files for a model"""
        if not self._session:
            await self.initialize()
        
        # Handle short-form model IDs
        repo_id = model_id
        if ":" in model_id and "/" not in model_id:
            info = await self.get_model_info(model_id)
            if info:
                repo_id = info.repo_id
            else:
                return []
        
        try:
            url = self._get_api_url(f"/models/{repo_id}/tree/main")
            async with self._session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
        except aiohttp.ClientError:
            return []
        
        siblings = data if isinstance(data, list) else []
        files = []
        
        for sibling in siblings:
            if sibling.get("type", "file") != "file":
                continue
                
            filename = sibling.get("path", "")
            
            # Skip non-model files
            if not filename.endswith((".gguf", ".ggml", ".bin", ".safetensors")):
                continue
            
            # Actual size might be in LFS info for large files
            size = sibling.get("lfs", {}).get("size", sibling.get("size", 0))
            if size < 10 * 1024 * 1024:  # < 10MB (kept lower just in case of tiny models)
                continue
            
            file_format = self._detect_format(filename)
            quantization = self._detect_quantization(filename)
            
            model_file = ModelFile(
                filename=filename,
                size_bytes=size,
                url=self._get_download_url(repo_id, filename),
                checksum=sibling.get("lfs", {}).get("oid"),
                checksum_type="sha256",
                format=file_format,
                quantization=quantization
            )
            
            files.append(model_file)
        
        # Sort by size (largest first)
        files.sort(key=lambda f: f.size_bytes, reverse=True)
        
        return files
    
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
            model_id: Model ID or repo ID
            destination: Destination directory
            filename: Specific file to download
            quantization: Preferred quantization (e.g., "Q4_K_M")
            progress_callback: Progress callback function
            
        Returns:
            Path to downloaded file
        """
        if not self._session:
            await self.initialize()
        
        # Get model info
        info = await self.get_model_info(model_id)
        if not info or not info.files:
            raise ModelNotFoundError(model_id, self.provider_id)
        
        # Handle full repository download
        if quantization == "":
            return await self.download_repo(model_id, destination, progress_callback)
            
        # Select file to download
        if filename:
            target_file = next((f for f in info.files if f.filename == filename), None)
        elif quantization:
            target_file = info.get_file_by_quant(quantization)
            if not target_file:
                target_file = info.get_best_file()
        else:
            target_file = info.get_best_file()
        
        if not target_file:
            raise ModelNotFoundError(
                model_id,
                self.provider_id,
                suggestions=[f.filename for f in info.files[:5]]
            )
        
        # Prepare destination
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        
        output_path = destination / target_file.filename
        cache_path = destination / f".{target_file.filename}.part"
        
        # Check for existing partial download
        start_byte = 0
        if cache_path.exists():
            start_byte = cache_path.stat().st_size
        
        # Download URL
        download_url = target_file.url or self._get_download_url(
            info.repo_id,
            target_file.filename
        )
        
        # Progress tracking
        progress = DownloadProgress(
            model_id=model_id,
            filename=target_file.filename,
            status="downloading",
            bytes_total=target_file.size_bytes,
            bytes_downloaded=start_byte
        )
        
        try:
            headers = {}
            if start_byte > 0:
                headers["Range"] = f"bytes={start_byte}-"
            
            async with self._session.get(download_url, headers=headers) as response:
                if response.status == 416:
                    # Range not satisfiable - file already complete
                    cache_path.rename(output_path)
                    progress.status = "complete"
                    progress.bytes_downloaded = target_file.size_bytes
                    if progress_callback:
                        progress_callback(progress)
                    return output_path
                
                if response.status not in (200, 206):
                    raise DownloadError(
                        message=f"Download failed: HTTP {response.status}",
                        model_id=model_id,
                        provider=self.provider_id
                    )
                
                # Update total size from response if available
                content_length = response.headers.get("Content-Length")
                if content_length:
                    if start_byte > 0:
                        progress.bytes_total = start_byte + int(content_length)
                    else:
                        progress.bytes_total = int(content_length)
                
                # Download with progress
                mode = "ab" if start_byte > 0 else "wb"
                chunk_size = 8 * 1024 * 1024  # 8MB chunks
                last_update = time.time()
                bytes_since_update = 0
                
                async with aiofiles.open(cache_path, mode) as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await f.write(chunk)
                        progress.bytes_downloaded += len(chunk)
                        bytes_since_update += len(chunk)
                        
                        # Update progress every second
                        now = time.time()
                        if now - last_update >= 1.0:
                            elapsed = now - last_update
                            progress.speed_bytes_per_sec = bytes_since_update / elapsed
                            
                            remaining = progress.bytes_total - progress.bytes_downloaded
                            if progress.speed_bytes_per_sec > 0:
                                progress.eta_seconds = remaining / progress.speed_bytes_per_sec
                            
                            if progress_callback:
                                progress_callback(progress)
                            
                            last_update = now
                            bytes_since_update = 0
            
            # Verify download
            progress.status = "verifying"
            if progress_callback:
                progress_callback(progress)
            
            if target_file.checksum:
                is_valid = await self.verify(cache_path, target_file.checksum)
                if not is_valid:
                    cache_path.unlink()
                    raise ValidationError(
                        message="Checksum verification failed",
                        model_id=model_id,
                        provider=self.provider_id
                    )
            
            # Move to final destination
            cache_path.rename(output_path)
            
            progress.status = "complete"
            progress.bytes_downloaded = progress.bytes_total
            if progress_callback:
                progress_callback(progress)
            
            return output_path
            
        except aiohttp.ClientError as e:
            progress.status = "error"
            progress.error = str(e)
            if progress_callback:
                progress_callback(progress)
            
            raise DownloadError(
                message=f"Download failed: {str(e)}",
                model_id=model_id,
                provider=self.provider_id,
                resumable=True,
                bytes_downloaded=progress.bytes_downloaded
            )
    
    async def download_repo(
        self,
        model_id: str,
        destination: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Path:
        """Download full repository using huggingface_hub"""
        from huggingface_hub import HfApi, snapshot_download
        
        info = await self.get_model_info(model_id)
        if not info:
             raise ModelNotFoundError(model_id, self.provider_id)
             
        repo_id = info.repo_id
        
        # Get total size using HfApi and filter by ignored patterns
        api = HfApi(token=self.token)
        repo_info = await asyncio.to_thread(api.model_info, repo_id, files_metadata=True)
        
        ignore_patterns = ["*.msgpack", "*.h5", "*.ot", "*.ckpt", ".git*"]
        total_bytes = 0
        for f in repo_info.siblings:
            if not f.size: continue
            # Basic glob check for ignore patterns
            should_ignore = False
            for p in ignore_patterns:
                import fnmatch
                if fnmatch.fnmatch(f.rfilename, p):
                    should_ignore = True
                    break
            if not should_ignore:
                total_bytes += f.size
        
        repo_dir = destination
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        progress = DownloadProgress(
            model_id=model_id,
            filename="Full Repository",
            status="downloading",
            bytes_total=total_bytes,
            bytes_downloaded=0
        )
        
        # Track downloading progress locally
        import threading
        from tqdm.auto import tqdm
        
        tqdm_lock = threading.Lock()
        global_download_state = {"bytes": 0}
        
        class ProgressTracker(tqdm):
            def __init__(self, *args, **kwargs):
                # Remove unsupported arguments like 'name' that may be passed by huggingface_hub
                kwargs.pop('name', None)
                self.is_bytes = kwargs.get('unit', '') == 'B'
                super().__init__(*args, **kwargs)

            def update(self, n=1):
                super().update(n)
                if self.is_bytes:
                    with tqdm_lock:
                        global_download_state["bytes"] += n
                        
        stop_polling = False
        async def poll_progress():
            last_bytes = 0
            last_time = time.time()
            
            while not stop_polling:
                try:
                    # Calculate finished local files and partially downloaded ones
                    local_bytes = sum(f.stat().st_size for f in repo_dir.rglob('*') if f.is_file())
                    
                    with tqdm_lock:
                        active_downloading = global_download_state["bytes"]
                    
                    calculated_bytes = max(local_bytes, active_downloading)
                    calculated_bytes = min(total_bytes, calculated_bytes)
                    
                    if calculated_bytes > progress.bytes_downloaded:
                        progress.bytes_downloaded = calculated_bytes
                    
                    current_bytes = progress.bytes_downloaded
                    
                    # Terminal update
                    if int(time.time() * 2) % 2 == 0: # Print twice per second
                        print(f"\r[{model_id}] Progress: {progress.progress_percent:.1f}% ({progress.downloaded_gb:.2f}/{progress.total_gb:.2f} GB) Speed: {progress.speed_mb_per_sec:.2f} MB/s    ", end="", flush=True)
                    
                    now = time.time()
                    elapsed = now - last_time
                    if elapsed > 0:
                        speed = (current_bytes - last_bytes) / elapsed
                        progress.speed_bytes_per_sec = speed
                        if speed > 0:
                            progress.eta_seconds = (total_bytes - current_bytes) / speed
                            
                    last_bytes = current_bytes
                    last_time = now
                    
                    if progress_callback:
                        progress_callback(progress)
                except Exception:
                    pass
                    
                await asyncio.sleep(0.5)
                
        polling_task = asyncio.create_task(poll_progress())
        
        try:
            # Using snapshot_download handles resumes and multithreading
            await asyncio.to_thread(
                snapshot_download,
                repo_id=repo_id,
                local_dir=str(repo_dir),
                token=self.token,
                ignore_patterns=ignore_patterns,
                tqdm_class=ProgressTracker,
                max_workers=8
            )
            
            print(f"\n[{model_id}] Download repository complete!")
            
            progress.status = "complete"
            progress.bytes_downloaded = total_bytes
            if progress_callback:
                progress_callback(progress)
                
            return repo_dir
            
        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            if progress_callback:
                progress_callback(progress)
            raise DownloadError(message=f"Snapshot download failed: {str(e)}", model_id=model_id, provider=self.provider_id)
        finally:
            stop_polling = True
            await polling_task

    async def verify(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """Verify file checksum"""
        if not expected_checksum:
            return True
        
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        
        actual = sha256.hexdigest()
        return actual.lower() == expected_checksum.lower()
    
    async def get_download_url(
        self,
        model_id: str,
        filename: str
    ) -> Optional[str]:
        """Get direct download URL"""
        info = await self.get_model_info(model_id)
        if info:
            return self._get_download_url(info.repo_id, filename)
        return None
    
    def supports_resume(self) -> bool:
        return True
    
    def requires_authentication(self) -> bool:
        return False  # Public models don't require auth