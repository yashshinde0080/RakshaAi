"""System Schemas"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class HardwareProfile(BaseModel):
    cpu_name: str
    cpu_cores: int
    cpu_threads: int
    has_avx2: bool
    has_avx512: bool
    ram_total_gb: float
    gpu_name: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    disk_type: str
    disk_speed_mb_s: float


class SystemStatus(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    model_loaded: bool
    current_model: Optional[str]
    current_mode: Optional[str]
    task_type: Optional[str] = None
    is_generative: bool = False
    ram_total_gb: float
    ram_used_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    engine_stats: Dict[str, Any] = {}


class ResourceUsage(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    disk_read_mb_s: float
    disk_write_mb_s: float
    