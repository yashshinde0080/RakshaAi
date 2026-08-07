"""Plugins API Endpoints"""
from fastapi import APIRouter, HTTPException, Request
from typing import List

from app.schemas.plugins import PluginInfo, PluginConfig


router = APIRouter()


@router.get("/", response_model=List[PluginInfo])
async def list_plugins(request: Request):
    """List all plugins"""
    plugin_manager = request.app.state.plugin_manager
    return plugin_manager.list_plugins()


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(request: Request, plugin_id: str):
    """Get plugin details"""
    plugin_manager = request.app.state.plugin_manager
    plugin = plugin_manager.get_plugin_info(plugin_id)
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return plugin


@router.post("/{plugin_id}/enable")
async def enable_plugin(request: Request, plugin_id: str):
    """Enable a plugin"""
    plugin_manager = request.app.state.plugin_manager
    success = await plugin_manager.enable_plugin(plugin_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"status": "enabled", "plugin_id": plugin_id}


@router.post("/{plugin_id}/disable")
async def disable_plugin(request: Request, plugin_id: str):
    """Disable a plugin"""
    plugin_manager = request.app.state.plugin_manager
    success = await plugin_manager.disable_plugin(plugin_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"status": "disabled", "plugin_id": plugin_id}


@router.post("/{plugin_id}/execute")
async def execute_plugin(request: Request, plugin_id: str, config: PluginConfig):
    """Execute plugin action"""
    plugin_manager = request.app.state.plugin_manager
    
    try:
        result = await plugin_manager.execute_plugin(
            plugin_id=plugin_id,
            action=config.action,
            params=config.params
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))