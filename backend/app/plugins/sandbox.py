"""Plugin Sandbox"""
import asyncio
try:
    import resource
except ImportError:
    resource = None
from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor
import threading

from app.plugins.interface import PluginInterface


class PluginSandbox:
    """Sandbox for plugin execution"""
    
    def __init__(
        self,
        max_memory_mb: int = 512,
        max_time_seconds: int = 30
    ):
        self.max_memory_mb = max_memory_mb
        self.max_time_seconds = max_time_seconds
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def execute(
        self,
        plugin: PluginInterface,
        action: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute plugin action in sandbox"""
        
        # Create timeout wrapper
        try:
            result = await asyncio.wait_for(
                plugin.execute(action, params),
                timeout=self.max_time_seconds
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Plugin execution timed out after {self.max_time_seconds}s")
    
    def _set_limits(self):
        """Set resource limits for plugin execution"""
        if resource is None:
            return
        try:
            # Memory limit
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.max_memory_mb * 1024 * 1024, hard)
            )
        except:
            pass  # May not work on all platforms