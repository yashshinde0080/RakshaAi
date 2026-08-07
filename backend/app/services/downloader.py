"""Download Service"""
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import hashlib


class DownloadManager:
    """Manage file downloads with resume support"""
    
    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
        self.cache_dir = download_dir / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_downloads: Dict[str, asyncio.Task] = {}
    
    async def download(
        self,
        url: str,
        filename: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        expected_checksum: Optional[str] = None
    ) -> Path:
        """Download file with resume support"""
        cache_path = self.cache_dir / f"{filename}.part"
        final_path = self.download_dir / filename
        
        # Check for partial download
        start_byte = 0
        if cache_path.exists():
            start_byte = cache_path.stat().st_size
        
        headers = {}
        if start_byte > 0:
            headers["Range"] = f"bytes={start_byte}-"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status not in (200, 206):
                    raise Exception(f"Download failed: {resp.status}")
                
                total_size = int(resp.headers.get("content-length", 0))
                if start_byte > 0:
                    total_size += start_byte
                
                mode = "ab" if start_byte > 0 else "wb"
                
                async with aiofiles.open(cache_path, mode) as f:
                    downloaded = start_byte
                    
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress = (downloaded / total_size * 100) if total_size else 0
                            progress_callback(progress, downloaded, total_size)
        
        # Verify checksum
        if expected_checksum:
            actual = await self._compute_checksum(cache_path)
            if actual != expected_checksum:
                cache_path.unlink()
                raise Exception("Checksum verification failed")
        
        # Move to final location
        cache_path.rename(final_path)
        
        return final_path
    
    async def _compute_checksum(self, path: Path) -> str:
        """Compute SHA256 checksum"""
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(path, "rb") as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def cancel_download(self, filename: str):
        """Cancel active download"""
        if filename in self.active_downloads:
            self.active_downloads[filename].cancel()
            del self.active_downloads[filename]
    
    def cleanup_cache(self):
        """Clean up partial downloads"""
        for path in self.cache_dir.glob("*.part"):
            path.unlink()