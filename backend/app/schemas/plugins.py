"""Plugin Schemas"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    enabled: bool
    builtin: bool
    actions: List[str]


class PluginConfig(BaseModel):
    action: str
    params: Dict[str, Any] = {}