"""
Provider Registry

Factory and registry for model providers.
Manages provider instances and provides unified access.
"""

from typing import Dict, Any, Optional, List, Type
from pathlib import Path

from app.providers.base import BaseProvider, ModelMetadata
from app.providers.huggingface import HuggingFaceProvider
from app.providers.local import LocalProvider
from app.providers.enterprise_repo import EnterpriseRepoProvider
from app.providers.usb_bundle import USBBundleProvider
from app.providers.exceptions import ProviderError


class ProviderRegistry:
    """
    Registry and factory for model providers.
    
    Manages multiple provider instances and provides unified search/download
    across all registered providers.
    """
    
    # Built-in provider classes
    BUILTIN_PROVIDERS: Dict[str, Type[BaseProvider]] = {
        "huggingface": HuggingFaceProvider,
        "local": LocalProvider,
        "enterprise": EnterpriseRepoProvider,
        "usb_bundle": USBBundleProvider,
    }
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._default_provider: Optional[str] = None
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize registry with configuration.
        
        Config format:
        {
            "providers": {
                "huggingface": {
                    "enabled": true,
                    "token": "hf_xxx"
                },
                "local": {
                    "enabled": true
                    # models_dir defaults to the project models dir
                },
                "enterprise": {
                    "enabled": false,
                    "base_url": "https://models.company.com",
                    "api_key": "xxx"
                }
            },
            "default": "huggingface"
        }
        """
        config = config or {}
        providers_config = config.get("providers", {})
        
        # Initialize default providers if no config
        if not providers_config:
            providers_config = {
                "huggingface": {"enabled": True},
                "local": {"enabled": True},
            }
        
        for provider_id, provider_config in providers_config.items():
            if not provider_config.get("enabled", True):
                continue
            
            await self.register(provider_id, provider_config)
        
        # Set default provider
        self._default_provider = config.get("default", "huggingface")
        
        if self._default_provider not in self._providers:
            # Fallback to first available
            if self._providers:
                self._default_provider = next(iter(self._providers.keys()))
    
    async def cleanup(self):
        """Cleanup all providers"""
        for provider in self._providers.values():
            try:
                await provider.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup provider {provider.provider_id}: {e}")
        
        self._providers.clear()
    
    async def register(
        self,
        provider_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseProvider:
        """
        Register and initialize a provider.
        
        Args:
            provider_id: Provider identifier (must match BUILTIN_PROVIDERS key)
            config: Provider configuration
            
        Returns:
            Initialized provider instance
        """
        if provider_id not in self.BUILTIN_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_id}")
        
        provider_class = self.BUILTIN_PROVIDERS[provider_id]
        provider = provider_class(config)
        
        await provider.initialize()
        
        self._providers[provider_id] = provider
        
        return provider
    
    async def register_custom(
        self,
        provider_id: str,
        provider_class: Type[BaseProvider],
        config: Optional[Dict[str, Any]] = None
    ) -> BaseProvider:
        """Register a custom provider class"""
        provider = provider_class(config)
        await provider.initialize()
        
        self._providers[provider_id] = provider
        
        return provider
    
    def unregister(self, provider_id: str):
        """Unregister a provider"""
        if provider_id in self._providers:
            del self._providers[provider_id]
    
    def get(self, provider_id: str) -> Optional[BaseProvider]:
        """Get a specific provider"""
        return self._providers.get(provider_id)
    
    def get_default(self) -> Optional[BaseProvider]:
        """Get the default provider"""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        return None
    
    def set_default(self, provider_id: str):
        """Set the default provider"""
        if provider_id not in self._providers:
            raise ValueError(f"Provider not registered: {provider_id}")
        self._default_provider = provider_id
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers"""
        return [
            {
                "id": pid,
                "name": provider.provider_name,
                "initialized": provider.is_initialized,
                "requires_auth": provider.requires_authentication(),
                "supports_resume": provider.supports_resume(),
                "is_default": pid == self._default_provider
            }
            for pid, provider in self._providers.items()
        ]
    
    async def search_all(
        self,
        query: str,
        limit: int = 10,
        providers: Optional[List[str]] = None
    ) -> List[ModelMetadata]:
        """
        Search across all (or specified) providers.
        
        Args:
            query: Search query
            limit: Maximum results per provider
            providers: List of provider IDs to search (None = all)
            
        Returns:
            Combined list of results from all providers
        """
        results = []
        target_providers = providers or list(self._providers.keys())
        
        for provider_id in target_providers:
            provider = self._providers.get(provider_id)
            if not provider:
                continue
            
            try:
                provider_results = await provider.search(query, limit)
                results.extend(provider_results)
            except Exception as e:
                print(f"Warning: Search failed for provider {provider_id}: {e}")
        
        return results
    
    async def get_model_info(
        self,
        model_id: str,
        provider_id: Optional[str] = None
    ) -> Optional[ModelMetadata]:
        """
        Get model info from a specific provider or search all.
        
        Args:
            model_id: Model identifier
            provider_id: Specific provider to use (None = search all)
            
        Returns:
            Model metadata or None
        """
        if provider_id:
            provider = self._providers.get(provider_id)
            if provider:
                return await provider.get_model_info(model_id)
            return None
        
        # Search all providers
        for provider in self._providers.values():
            try:
                info = await provider.get_model_info(model_id)
                if info:
                    return info
            except Exception:
                continue
        
        return None
    
    async def download(
        self,
        model_id: str,
        destination: Path,
        provider_id: Optional[str] = None,
        **kwargs
    ) -> Path:
        """
        Download model from a provider.
        
        Args:
            model_id: Model identifier
            destination: Destination directory
            provider_id: Specific provider (None = auto-detect)
            **kwargs: Additional arguments for provider.download()
            
        Returns:
            Path to downloaded file
        """
        provider = None
        
        if provider_id:
            provider = self._providers.get(provider_id)
        else:
            # Try to find provider that has this model
            for p in self._providers.values():
                try:
                    info = await p.get_model_info(model_id)
                    if info:
                        provider = p
                        break
                except Exception:
                    continue
        
        if not provider:
            raise ProviderError(f"No provider found for model: {model_id}")
        
        return await provider.download(model_id, destination, **kwargs)


# Global registry instance
_registry: Optional[ProviderRegistry] = None


async def get_registry() -> ProviderRegistry:
    """Get or create the global provider registry"""
    global _registry
    
    if _registry is None:
        _registry = ProviderRegistry()
        await _registry.initialize()
    
    return _registry


async def get_provider(provider_id: Optional[str] = None) -> BaseProvider:
    """
    Get a provider instance.
    
    Args:
        provider_id: Provider ID (None = default provider)
        
    Returns:
        Provider instance
    """
    registry = await get_registry()
    
    if provider_id:
        provider = registry.get(provider_id)
    else:
        provider = registry.get_default()
    
    if not provider:
        raise ProviderError(f"Provider not found: {provider_id or 'default'}")
    
    return provider


async def cleanup_registry():
    """Cleanup the global registry"""
    global _registry
    
    if _registry:
        await _registry.cleanup()
        _registry = None