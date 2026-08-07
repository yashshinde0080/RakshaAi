"""
Enterprise Repository Provider

Handles models from private/enterprise repositories.
Supports custom authentication and private model hosting.
"""

import asyncio
import aiohttp
import aiofiles
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

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
    AuthenticationError
)


class EnterpriseRepoProvider(BaseProvider):
    """
    Enterprise/Private Repository Provider.
    
    Connects to private model repositories with custom authentication.
    Supports various authentication methods:
    - API Key
    - Bearer Token
    - Basic Auth
    - Custom Headers
    """
    
    provider_id = "enterprise"
    provider_name = "Enterprise Repository"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        if not config:
            raise ValueError("Enterprise provider requires configuration")
        
        self.base_url = config.get("base_url", "").rstrip("/")
        self.api_key = config.get("api_key")
        self.bearer_token = config.get("bearer_token")
        self.username = config.get("username")
        self.password = config.get("password")
        self.custom_headers = config.get("headers", {})
        
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 300)
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize with authentication"""
        headers = {
            "User-Agent": "SovereignAI-Enterprise/1.0",
            "Accept": "application/json"
        }
        
        # Apply authentication
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        
        # Apply custom headers
        headers.update(self.custom_headers)
        
        # Create auth if using basic auth
        auth = None
        if self.username and self.password:
            auth = aiohttp.BasicAuth(self.username, self.password)
        
        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        
        self._session = aiohttp.ClientSession(
            headers=headers,
            auth=auth,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # Verify connection
        try:
            async with self._session.get(f"{self.base_url}/health") as response:
                if response.status == 401:
                    raise AuthenticationError(
                        message="Authentication failed",
                        provider=self.provider_id
                    )
                elif response.status >= 400:
                    # Try to continue anyway - health endpoint might not exist
                    pass
        except aiohttp.ClientError as e:
            # Connection issues - still mark as initialized
            print(f"Warning: Enterprise repo health check failed: {e}")
        
        self._initialized = True
        return True
    
    async def cleanup(self):
        """Cleanup session"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelMetadata]:
        """Search enterprise repository"""
        if not self._session:
            await self.initialize()
        
        params = {
            "q": query,
            "limit": limit
        }
        
        if filters:
            params.update(filters)
        
        try:
            async with self._session.get(
                f"{self.base_url}/api/models/search",
                params=params
            ) as response:
                if response.status == 401:
                    raise AuthenticationError(provider=self.provider_id)
                elif response.status != 200:
                    return []
                
                data = await response.json()
        except aiohttp.ClientError as e:
            raise DownloadError(
                message=f"Search failed: {str(e)}",
                provider=self.provider_id
            )
        
        results = []
        
        for item in data.get("models", data if isinstance(data, list) else []):
            metadata = self._parse_model_data(item)
            results.append(metadata)
        
        return results[:limit]
    
    async def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model details"""
        if not self._session:
            await self.initialize()
        
        try:
            async with self._session.get(
                f"{self.base_url}/api/models/{model_id}"
            ) as response:
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
        
        return self._parse_model_data(data)
    
    def _parse_model_data(self, data: Dict[str, Any]) -> ModelMetadata:
        """Parse model data from API response"""
        files = []
        
        for file_data in data.get("files", []):
            files.append(ModelFile(
                filename=file_data.get("name", file_data.get("filename", "")),
                size_bytes=file_data.get("size", file_data.get("size_bytes", 0)),
                url=file_data.get("url", file_data.get("download_url")),
                checksum=file_data.get("checksum", file_data.get("sha256")),
                format=ModelFormat(file_data.get("format", "gguf")),
                quantization=QuantizationType(file_data.get("quantization", "unknown"))
                    if file_data.get("quantization") else None
            ))
        
        return ModelMetadata(
            id=data.get("id", data.get("model_id", "")),
            name=data.get("name", data.get("model_name", "")),
            provider=self.provider_id,
            family=data.get("family"),
            parameters=data.get("parameters", data.get("param_count")),
            description=data.get("description"),
            license=data.get("license"),
            author=data.get("author", data.get("organization")),
            format=ModelFormat(data.get("format", "gguf")),
            files=files,
            tags=data.get("tags", []),
            context_length=data.get("context_length", data.get("max_context")),
            modes_supported=data.get("modes", ["fullram", "layerstream"]),
            source_url=data.get("url"),
            repo_id=data.get("repo_id", data.get("id")),
            created_at=datetime.fromisoformat(data["created_at"])
                if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at") else None
        )
    
    async def list_files(self, model_id: str) -> List[ModelFile]:
        """List available files"""
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
        """Download model from enterprise repo"""
        if not self._session:
            await self.initialize()
        
        # Get model info
        info = await self.get_model_info(model_id)
        if not info or not info.files:
            raise ModelNotFoundError(model_id, self.provider_id)
        
        # Select file
        if filename:
            target_file = next((f for f in info.files if f.filename == filename), None)
        elif quantization:
            target_file = info.get_file_by_quant(quantization)
        else:
            target_file = info.get_best_file()
        
        if not target_file:
            raise ModelNotFoundError(model_id, self.provider_id)
        
        # Get download URL
        if target_file.url:
            download_url = target_file.url
        else:
            download_url = f"{self.base_url}/api/models/{model_id}/download/{target_file.filename}"
        
        # Prepare destination
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        
        output_path = destination / target_file.filename
        
        # Progress tracking
        progress = DownloadProgress(
            model_id=model_id,
            filename=target_file.filename,
            status="downloading",
            bytes_total=target_file.size_bytes
        )
        
        try:
            async with self._session.get(download_url) as response:
                if response.status == 401:
                    raise AuthenticationError(provider=self.provider_id)
                elif response.status == 404:
                    raise ModelNotFoundError(model_id, self.provider_id)
                elif response.status != 200:
                    raise DownloadError(
                        message=f"Download failed: HTTP {response.status}",
                        model_id=model_id,
                        provider=self.provider_id
                    )
                
                # Get size
                content_length = response.headers.get("Content-Length")
                if content_length:
                    progress.bytes_total = int(content_length)
                
                # Download
                async with aiofiles.open(output_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8 * 1024 * 1024):
                        await f.write(chunk)
                        progress.bytes_downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(progress)
            
            # Verify
            progress.status = "verifying"
            if progress_callback:
                progress_callback(progress)
            
            if target_file.checksum:
                is_valid = await self.verify(output_path, target_file.checksum)
                if not is_valid:
                    output_path.unlink()
                    raise ValidationError(
                        message="Checksum verification failed",
                        model_id=model_id,
                        provider=self.provider_id
                    )
            
            progress.status = "complete"
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
                provider=self.provider_id
            )
    
    async def verify(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """Verify checksum"""
        if not expected_checksum:
            return True
        
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest().lower() == expected_checksum.lower()
    
    def requires_authentication(self) -> bool:
        return True
    
    def supports_resume(self) -> bool:
        return False  # Depends on server support