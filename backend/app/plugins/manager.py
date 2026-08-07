"""Plugin Manager"""
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

from app.config import settings
from app.plugins.interface import PluginInterface
from app.plugins.sandbox import PluginSandbox


class PluginManager:
    """Manage plugin lifecycle"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.builtin_plugins_path = Path(__file__).parent / "builtin"
        self.user_plugins_path = settings.plugins_dir
        self.sandbox = PluginSandbox()
    
    async def load_plugins(self):
        """Load all plugins"""
        # Load builtin plugins
        await self._load_from_directory(self.builtin_plugins_path, builtin=True)
        
        # Load user plugins
        if self.user_plugins_path.exists():
            await self._load_from_directory(self.user_plugins_path, builtin=False)
    
    async def _load_from_directory(self, path: Path, builtin: bool = False):
        """Load plugins from directory"""
        if not path.exists():
            return
        
        for plugin_file in path.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                plugin = await self._load_plugin_file(plugin_file)
                if plugin:
                    plugin.builtin = builtin
                    await plugin.initialize()
                    self.plugins[plugin.id] = plugin
            except Exception as e:
                print(f"Failed to load plugin {plugin_file}: {e}")
    
    async def _load_plugin_file(self, path: Path) -> Optional[PluginInterface]:
        """Load single plugin file"""
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find plugin class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type) and 
                issubclass(attr, PluginInterface) and 
                attr is not PluginInterface
            ):
                return attr()
        
        return None
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins"""
        return [
            {
                **plugin.get_info(),
                "builtin": getattr(plugin, "builtin", False)
            }
            for plugin in self.plugins.values()
        ]
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin info"""
        plugin = self.plugins.get(plugin_id)
        if plugin:
            return {
                **plugin.get_info(),
                "builtin": getattr(plugin, "builtin", False)
            }
        return None
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = True
            return True
        return False
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = False
            return True
        return False
    
    async def execute_plugin(
        self,
        plugin_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute plugin action"""
        plugin = self.plugins.get(plugin_id)
        
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        if not plugin.enabled:
            raise ValueError(f"Plugin disabled: {plugin_id}")
        
        if action not in plugin.get_actions():
            raise ValueError(f"Unknown action: {action}")
        
        # Execute in sandbox
        return await self.sandbox.execute(plugin, action, params)
    
    async def unload_all(self):
        """Unload all plugins"""
        for plugin in self.plugins.values():
            try:
                await plugin.cleanup()
            except:
                pass
        self.plugins.clear()