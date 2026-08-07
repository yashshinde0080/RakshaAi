"""
Pydantic schemas for all database entities.
No ambiguity. No loose dicts flying around.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EngineMode(str, Enum):
    FULLRAM = "fullram"
    LAYERSTREAM = "layerstream"
    AUTO = "auto"


class QuantType(str, Enum):
    Q4_0 = "Q4_0"
    Q4_K_M = "Q4_K_M"
    Q4_K_S = "Q4_K_S"
    Q5_0 = "Q5_0"
    Q5_K_M = "Q5_K_M"
    Q5_K_S = "Q5_K_S"
    Q8_0 = "Q8_0"
    F16 = "F16"
    F32 = "F32"


class ModelStatus(str, Enum):
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    ENCRYPTING = "encrypting"
    READY = "ready"
    CORRUPTED = "corrupted"
    REMOVED = "removed"


class ModelRecord(BaseModel):
    id: Optional[int] = None
    name: str
    family: str
    size_label: str  # "7b", "8b", "13b"
    quant: QuantType
    file_path: str
    file_size_bytes: int
    checksum_sha256: str
    source: str = "local"  # "huggingface", "local", "usb_bundle"
    repo_id: Optional[str] = None
    status: ModelStatus = ModelStatus.READY
    engines_supported: str = "fullram,layerstream"  # comma separated
    context_length: int = 4096
    hidden_size: int = 4096
    num_layers: int = 32
    ram_required_mb: int = 0
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None
    use_count: int = 0


class SessionRecord(BaseModel):
    model_config = {'protected_namespaces': ()}
    
    id: Optional[int] = None
    session_id: str
    model_name: str
    engine_mode: EngineMode
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    avg_tokens_per_sec: float = 0.0
    peak_ram_mb: float = 0.0
    status: str = "active"  # "active", "completed", "crashed"


class HardwareProfile(BaseModel):
    id: Optional[int] = None
    cpu_name: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    has_avx2: bool = False
    has_avx512: bool = False
    total_ram_mb: int = 0
    available_ram_mb: int = 0
    gpu_name: Optional[str] = None
    gpu_vram_mb: int = 0
    disk_type: str = "unknown"  # "ssd", "hdd", "nvme", "usb"
    disk_read_speed_mbps: float = 0.0
    disk_write_speed_mbps: float = 0.0
    recommended_mode: EngineMode = EngineMode.AUTO
    max_model_size_label: str = ""
    profiled_at: Optional[str] = None


class DocumentRecord(BaseModel):
    id: Optional[int] = None
    document_id: str
    filename: str
    file_path: str
    file_size_bytes: int
    mime_type: str = "application/pdf"
    total_chunks: int = 0
    total_embeddings: int = 0
    checksum_sha256: str = ""
    status: str = "pending"  # "pending", "chunked", "embedded", "indexed", "failed"
    created_at: Optional[str] = None
    processed_at: Optional[str] = None


class PluginRecord(BaseModel):
    id: Optional[int] = None
    plugin_id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    entry_point: str
    is_active: bool = False
    permissions: str = ""  # comma separated
    signature: Optional[str] = None
    installed_at: Optional[str] = None


class AuditRecord(BaseModel):
    id: Optional[int] = None
    timestamp: Optional[str] = None
    event_type: str  # "model_load", "query", "download", "error", "security"
    severity: str = "info"  # "info", "warning", "error", "critical"
    source: str = ""  # module that generated event
    message: str = ""
    metadata_json: Optional[str] = None