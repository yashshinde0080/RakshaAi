"""Configuration Management"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application Settings"""
    
    # Application
    app_name: str = "SovereignAI Edge"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    workspace_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "workspace")
    models_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "workspace" / "models")
    plugins_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "workspace" / "plugins")
    database_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "workspace" / "database" / "sovereign.db")
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "workspace" / "data")
    
    # Memory
    max_ram_usage_percent: float = 0.75
    layer_prefetch_count: int = 2
    kv_cache_max_mb: int = 2048
    
    # Security
    encryption_enabled: bool = True
    audit_logging: bool = True
    
    # Custom model catalog (enterprise / USB YAML definitions)
    catalog_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "workspace" / "plugins" / "user" / "models")

    # Model Defaults
    default_quant: str = "Q4_K_M"
    default_mode: str = "auto"

    # TurboQuant KV Cache Compression
    turboquant_enabled: bool = True
    turboquant_bits: float = 3.5
    turboquant_qjl_enabled: bool = True
    turboquant_rotation: str = "random"

    class Config:
        env_prefix = "SOVEREIGN_"
        env_file = ".env"


settings = Settings()

# Ensure directories exist
settings.models_dir.mkdir(parents=True, exist_ok=True)
settings.workspace_dir.mkdir(parents=True, exist_ok=True)
settings.catalog_dir.mkdir(parents=True, exist_ok=True)
settings.plugins_dir.mkdir(parents=True, exist_ok=True)
settings.database_path.parent.mkdir(parents=True, exist_ok=True)

# Keep HuggingFace tokenizer/config/module caches on the pendrive (portable USB).
# setdefault → an externally-set HF_HOME (e.g. launch script) wins.
os.environ.setdefault("HF_HOME", str(settings.workspace_dir / "hf_cache"))