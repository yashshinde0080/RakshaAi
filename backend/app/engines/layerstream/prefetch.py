"""Layer Prefetching System"""
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import deque
import threading


@dataclass
class PrefetchTask:
    """Prefetch task"""
    layer_id: int
    priority: int = 0


class PrefetchQueue:
    """Async prefetch queue"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.queue: deque = deque()
        self.active: Dict[int, asyncio.Task] = {}
        self.completed: set = set()
        self._lock = asyncio.Lock()
        self.running = False
        self.buffers: Dict[int, bytes] = {}
    
    async def start(self, loader):
        """Start prefetch worker"""
        self.running = True
        self.loader = loader
        
        while self.running:
            async with self._lock:
                # Start new tasks if capacity available
                while self.queue and len(self.active) < self.max_concurrent:
                    task = self.queue.popleft()
                    if task.layer_id not in self.completed:
                        self.active[task.layer_id] = asyncio.create_task(
                            self._prefetch_layer(task.layer_id)
                        )
            
            await asyncio.sleep(0.01)
    
    async def stop(self):
        """Stop prefetch worker"""
        self.running = False
        
        # Cancel active tasks
        for task in self.active.values():
            task.cancel()
        self.active.clear()
    
    async def schedule(self, layer_id: int, priority: int = 0):
        """Schedule layer for prefetch"""
        async with self._lock:
            if layer_id not in self.completed and layer_id not in self.active:
                self.queue.append(PrefetchTask(layer_id=layer_id, priority=priority))
    
    async def _prefetch_layer(self, layer_id: int):
        """Prefetch single layer"""
        try:
            buffer = await self.loader.load_layer_async(layer_id)
            async with self._lock:
                self.buffers[layer_id] = buffer
                self.completed.add(layer_id)
                if layer_id in self.active:
                    del self.active[layer_id]
        except Exception as e:
            async with self._lock:
                if layer_id in self.active:
                    del self.active[layer_id]
    
    async def get_buffer(self, layer_id: int) -> Optional[bytes]:
        """Get prefetched buffer"""
        async with self._lock:
            return self.buffers.get(layer_id)
    
    async def release_buffer(self, layer_id: int):
        """Release buffer memory"""
        async with self._lock:
            if layer_id in self.buffers:
                del self.buffers[layer_id]
            if layer_id in self.completed:
                self.completed.remove(layer_id)
    
    def is_ready(self, layer_id: int) -> bool:
        """Check if layer is prefetched"""
        return layer_id in self.completed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prefetch statistics"""
        return {
            "queue_size": len(self.queue),
            "active_count": len(self.active),
            "completed_count": len(self.completed),
            "buffer_count": len(self.buffers)
        }