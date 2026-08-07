"""Layer Streaming Scheduler"""
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import time


class LayerState(Enum):
    NOT_LOADED = 0
    LOADING = 1
    LOADED = 2
    COMPUTING = 3
    EVICTING = 4


@dataclass
class LayerInfo:
    """Layer information"""
    id: int
    offset: int
    size: int
    state: LayerState = LayerState.NOT_LOADED
    last_used: float = 0
    buffer: Optional[bytes] = None


class LayerScheduler:
    """Schedule layer loading and eviction"""
    
    def __init__(
        self,
        num_layers: int,
        max_loaded: int = 2,
        prefetch_count: int = 1
    ):
        self.num_layers = num_layers
        self.max_loaded = max_loaded
        self.prefetch_count = prefetch_count
        
        self.layers: Dict[int, LayerInfo] = {}
        self.loaded_layers: List[int] = []
        self._lock = asyncio.Lock()
    
    def initialize_layers(self, layer_infos: List[Dict[str, int]]):
        """Initialize layer metadata"""
        for info in layer_infos:
            self.layers[info["id"]] = LayerInfo(
                id=info["id"],
                offset=info["offset"],
                size=info["size"]
            )
    
    async def ensure_loaded(self, layer_id: int, loader) -> bytes:
        """Ensure layer is loaded"""
        async with self._lock:
            layer = self.layers[layer_id]
            
            if layer.state == LayerState.LOADED:
                layer.last_used = time.time()
                return layer.buffer
            
            # Check if we need to evict
            while len(self.loaded_layers) >= self.max_loaded:
                await self._evict_oldest()
            
            # Load layer
            layer.state = LayerState.LOADING
            layer.buffer = await loader.load_layer_async(layer_id)
            layer.state = LayerState.LOADED
            layer.last_used = time.time()
            self.loaded_layers.append(layer_id)
            
            return layer.buffer
    
    async def prefetch(self, current_layer: int, loader):
        """Prefetch upcoming layers"""
        for i in range(1, self.prefetch_count + 1):
            next_id = current_layer + i
            if next_id < self.num_layers and next_id not in self.loaded_layers:
                asyncio.create_task(self.ensure_loaded(next_id, loader))
    
    async def _evict_oldest(self):
        """Evict least recently used layer"""
        if not self.loaded_layers:
            return
        
        # Find oldest
        oldest_id = min(
            self.loaded_layers,
            key=lambda x: self.layers[x].last_used
        )
        
        layer = self.layers[oldest_id]
        layer.state = LayerState.EVICTING
        layer.buffer = None
        layer.state = LayerState.NOT_LOADED
        self.loaded_layers.remove(oldest_id)
    
    async def evict_layer(self, layer_id: int):
        """Evict specific layer"""
        async with self._lock:
            if layer_id in self.loaded_layers:
                layer = self.layers[layer_id]
                layer.buffer = None
                layer.state = LayerState.NOT_LOADED
                self.loaded_layers.remove(layer_id)
    
    def get_loaded_count(self) -> int:
        """Get number of loaded layers"""
        return len(self.loaded_layers)
    
    def get_memory_usage(self) -> int:
        """Get total memory usage"""
        return sum(
            self.layers[lid].size 
            for lid in self.loaded_layers
        )