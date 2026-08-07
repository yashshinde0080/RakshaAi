"""Plugin Interface"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class PluginInterface(ABC):
    """Base interface for all plugins"""
    
    # Plugin metadata
    id: str = "base_plugin"
    name: str = "Base Plugin"
    version: str = "1.0.0"
    description: str = "Base plugin interface"
    author: str = "Unknown"
    
    def __init__(self):
        self.enabled = True
        self.config: Dict[str, Any] = {}
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize plugin"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup plugin resources"""
        pass
    
    @abstractmethod
    def get_actions(self) -> List[str]:
        """Get available actions"""
        pass
    
    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute plugin action"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "actions": self.get_actions()
        }