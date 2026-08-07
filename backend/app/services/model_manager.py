"""Model Management Service"""
import os
import json
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
import aiofiles

from app.config import settings
from app.services.registry import ModelRegistry
from app.security.encryption import ModelEncryption
from app.providers.huggingface import HuggingFaceProvider
from app.providers.custom_catalog import CustomModelCatalog


def _fuzzy_match_model(models: List[Dict[str, Any]], model_id: str) -> Optional[Dict[str, Any]]:
    """Resolve a model id that wasn't found in the registry directly.

    Normalizes slashes/colons, prefers an exact normalized match, then a
    containment match. ``split:`` variants never win a fuzzy match — they are
    derived views of a base model, so a display-name request like
    "Qwen3.5-0.8B" must resolve to the base model rather than the split copy
    (otherwise ``app.state.active_model`` ends up as a different id than the
    one the caller asked for). Explicit "split:..." requests still resolve
    through the direct registry lookup before this is called.
    """
    clean_request = model_id.replace("/", "-").replace(":", "-").lower()
    stripped_req = clean_request.replace("split-", "")

    for m in models:
        if m["id"].startswith("split:"):
            continue  # prefer the base model over split variants
        clean_m = m["id"].replace("/", "-").replace(":", "-").lower()
        if clean_m == clean_request:
            return m  # exact normalized match wins outright
        if clean_m.replace("split-", "") == stripped_req:
            return m  # exact match modulo the split: prefix
        if stripped_req in clean_m or clean_m in stripped_req:
            return m  # first containment match (base models only)
    return None


class ModelManager:
    """Manage model lifecycle"""
    
    HUGGINGFACE_API = "https://huggingface.co/api/models"
    
    def __init__(self):
        self.models_dir = settings.models_dir
        self.registry = ModelRegistry(settings.database_path)
        self.encryption = ModelEncryption() if settings.encryption_enabled else None
        
        self.download_status: Dict[str, Dict[str, Any]] = {}
        self._download_tasks: Dict[str, asyncio.Task] = {}
        
        self.provider = HuggingFaceProvider()
    
    async def initialize(self, app=None):
        """Initialize model manager with app reference for engine state"""
        self.app = app
        await self.registry.initialize()
        await self.provider.initialize()
        
        # Load custom model catalogs (enterprise / USB YAML definitions)
        catalog = CustomModelCatalog()
        n = catalog.load_directory(settings.catalog_dir)
        if n:
            print(f"Custom model catalog: {n} models loaded from {settings.catalog_dir}")

        # Scan for models
        await self.scan_installed()
    
    async def scan_installed(self):
        """Scan models directory for installed models and sync with registry"""
        installed_dir = self.models_dir / "installed"
        installed_dir.mkdir(parents=True, exist_ok=True)
        
        folders = [d for d in installed_dir.iterdir() if d.is_dir()]
        gguf_files = list(installed_dir.glob("*.gguf")) + list(installed_dir.glob("*.gguf.enc"))
        
        installed_ids = []
        
        # Scan folders
        for model_dir in folders:
            metadata_path = model_dir / "metadata.json"
            metadata = None
            
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    
                    # Sync path with current filesystem location
                    if "path" in metadata:
                        original_path = Path(metadata["path"])
                        if not original_path.exists():
                            # If direct path fails, assume it's this directory
                            metadata["path"] = str(model_dir)
                except Exception as e:
                    print(f"Error reading metadata for {model_dir}: {e}")
                    pass
            
            if not metadata:
                # Try to discover model manually if metadata is missing
                metadata = await self._discover_model(model_dir)
            
            if metadata:
                print(f"SCAN: Found model {metadata['id']} at {metadata['path']}")
                # Always register/update to sync DB with disk
                await self.registry.add_model(metadata)
                installed_ids.append(metadata["id"])

        # Scan standalone GGUF files
        for gguf_path in gguf_files:
            model_id = gguf_path.name
            metadata = {
                "id": model_id,
                "name": gguf_path.name,
                "family": "gguf",
                "parameters": "unknown",
                "quant": "unknown",
                "size_gb": round(gguf_path.stat().st_size / (1024**3), 2),
                "path": str(gguf_path),
                "downloaded": True,
                "modes_supported": ["fullram", "layerstream"],
                "created_at": datetime.now().isoformat()
            }
            print(f"SCAN: Found GGUF model {model_id} at {gguf_path}")
            await self.registry.add_model(metadata)
            installed_ids.append(model_id)
        
        # ALSO SCAN OFFLOAD CACHE
        cache_dir = settings.workspace_dir / "offload_cache"
        if cache_dir.exists():
            for cache_model_dir in cache_dir.iterdir():
                if cache_model_dir.is_dir():
                    # Check if it looks like a pre-split model
                    if (cache_model_dir / "embed.safetensors").exists():
                        model_id = f"split:{cache_model_dir.name}"
                        metadata_path = cache_model_dir / "metadata.json"
                        metadata = None
                        
                        if metadata_path.exists():
                            try:
                                with open(metadata_path) as f:
                                    metadata = json.load(f)
                                metadata["id"] = model_id # Force prefix
                                metadata["path"] = str(cache_model_dir)
                            except: pass
                            
                        if not metadata:
                            # Create minimal metadata
                            metadata = {
                                "id": model_id,
                                "name": f"{cache_model_dir.name} (Split)",
                                "family": "split",
                                "parameters": "unknown",
                                "quant": "fp16",
                                "size_gb": round(sum(f.stat().st_size for f in cache_model_dir.glob("*.safetensors")) / (1024**3), 2),
                                "path": str(cache_model_dir),
                                "downloaded": True,
                                "modes_supported": ["layerstream"],
                                "created_at": datetime.now().isoformat()
                            }
                        
                        print(f"SCAN: Found split model {model_id} at {metadata['path']}")
                        await self.registry.add_model(metadata)
                        installed_ids.append(model_id)

        # Cleanup registry: remove models that no longer exist on disk
        db_models = await self.registry.list_models()
        for db_m in db_models:
             if db_m["id"] not in installed_ids:
                 # Check if path still exists
                 if not Path(db_m["path"]).exists():
                     await self.registry.delete_model(db_m["id"])

    async def _discover_model(self, model_dir: Path) -> Optional[Dict[str, Any]]:
        """Try to discover model information from a directory"""
        # Look for config.json (HF repo)
        config_path = model_dir / "config.json"
        
        # ID strategy: use folder name if metadata is missing
        # If folder follows name-repo format from download_model, it will stay as is
        model_id = model_dir.name 
        
        if config_path.exists():
            # HF repo
            model_type = "unknown"
            try:
                with open(config_path) as f:
                    config = json.load(f)
                model_type = config.get("model_type", "unknown")
            except Exception:
                pass
            
            # Calculate size
            size_bytes = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
            
            return {
                "id": model_id,
                "name": model_dir.name,
                "family": model_type,
                "parameters": "unknown",
                "quant": "none",
                "size_gb": round(size_bytes / (1024**3), 2),
                "path": str(model_dir),
                "downloaded": True,
                "modes_supported": ["fullram", "layerstream"],
                "created_at": datetime.now().isoformat()
            }
        
        # Look for .gguf files
        gguf_files = list(model_dir.glob("*.gguf"))
        if gguf_files:
            gguf_path = gguf_files[0]
            return {
                "id": model_id,
                "name": model_id,
                "family": "gguf",
                "parameters": "unknown",
                "quant": "unknown",
                "size_gb": round(gguf_path.stat().st_size / (1024**3), 2),
                "path": str(gguf_path),
                "downloaded": True,
                "modes_supported": ["fullram", "layerstream"],
                "created_at": datetime.now().isoformat()
            }
            
        return None
    
    async def load_model(self, model_id: str, mode: str = "auto") -> Dict[str, Any]:
        """Unified load logic with hardware check"""
        from app.core.engine_factory import EngineFactory
        
        print(f"LOAD: Request for model {model_id} (mode={mode})")
        model = await self.get_model(model_id)
        
        if not model:
            # Fuzzy match: some callers pass display names or dash-replaced ids
            all_models = await self.list_models()
            model = _fuzzy_match_model(all_models, model_id)
            if model:
                print(f"LOAD: Fuzzy matched {model_id} to {model['id']}")
                model_id = model["id"]
                    
        if not model:
            print(f"LOAD: Model {model_id} not found in registry")
            raise ValueError(f"Model {model_id} not found in registry")
            
        if not self.app:
            raise RuntimeError("ModelManager not linked to FastAPI application state")
            
        # Unload current if any
        await self.unload_model()
        
        # Split models are stored in offload_cache as per-layer safetensors and
        # only support the LayerStream engine. auto must never hand them to
        # fullram (which would look for a consolidated model.safetensors that
        # only exists in the base model dir).
        if mode == "auto" and model["id"].startswith("split:"):
            mode = "layerstream"

        # If we're in fullram mode but selected a split model, try to use the base model
        model_path = model["path"]
        if mode == "fullram" and model["id"].startswith("split:"):
            target_base = model["id"].replace("split:", "")
            
            # Reuse fuzzy matching logic to find the base model
            all_models = await self.list_models()
            clean_target = target_base.replace("/", "-").replace(":", "-").lower()
            
            base_model = None
            for m in all_models:
                # Don't match against other split models
                if m["id"].startswith("split:"):
                    continue
                    
                clean_m = m["id"].replace("/", "-").replace(":", "-").lower()
                if clean_m == clean_target:
                    base_model = m
                    break
            
            if base_model:
                print(f"LOAD: Switching to base model {base_model['id']} path for fullram mode")
                model_path = base_model["path"]

        # Initialize engine (pass metadata for llmfit scoring)
        factory = EngineFactory(self.app.state.hardware_profile)
        engine = await factory.create_engine(
            model_path=model_path,
            mode=mode,
            model_metadata=model,
        )
        
        # Update app state
        self.app.state.active_engine = engine
        self.app.state.active_model = model_id
        self.app.state.active_mode = engine.mode
        
        return {
            "status": "loaded",
            "model": model_id,
            "mode": engine.mode,
            "metadata": getattr(engine, "task_metadata", {})
        }
        
    async def unload_model(self):
        """Safely unload active model"""
        if not self.app or not getattr(self.app.state, "active_engine", None):
            return
            
        engine = self.app.state.active_engine
        await engine.unload()
        
        self.app.state.active_engine = None
        self.app.state.active_model = None
        self.app.state.active_mode = None
        
        import gc
        gc.collect()

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all installed models"""
        return await self.registry.list_models()
    
    async def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model by name"""
        return await self.registry.get_model(model_name)
    
    async def model_exists(self, model_name: str) -> bool:
        """Check if model exists"""
        model = await self.registry.get_model(model_name)
        return model is not None
    
    def is_downloading(self, model_name: str) -> bool:
        """Check if model is being downloaded"""
        return model_name in self._download_tasks
    
    def get_download_status(self, model_name: str) -> Dict[str, Any]:
        """Get download status"""
        return self.download_status.get(model_name, {
            "model": model_name,
            "status": "unknown",
            "progress": 0
        })
    
    async def download_model(self, model_name: str, quant: str = "Q4_K_M"):
        """Download model from HuggingFace"""
        self.download_status[model_name] = {
            "model": model_name,
            "status": "downloading",
            "progress": 0,
            "downloaded_gb": 0,
            "total_gb": 0,
            "error": None
        }
        
        def update_progress(progress):
            self.download_status[model_name].update({
                "status": progress.status,
                "progress": progress.progress_percent,
                "downloaded_gb": progress.downloaded_gb,
                "total_gb": progress.total_gb,
                "error": progress.error
            })
            
        try:
            # Get model info
            info = await self.provider.get_model_info(model_name)
            if not info:
                raise Exception(f"Model {model_name} not found")
                
            # Create model directory
            safe_name = model_name.replace(":", "-").replace("/", "-")
            model_dir = self.models_dir / "installed" / safe_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Start download
            # Support full repo download if quant is "full" or empty
            actual_quant = quant if quant not in ["full", "none", ""] else ""
            
            model_path = await self.provider.download(
                model_id=model_name,
                destination=model_dir,
                quantization=actual_quant,
                progress_callback=update_progress
            )
            
            # Get specific file info for metadata
            file_info = info.get_file_by_quant(actual_quant) or info.get_best_file() if actual_quant else None
            
            # calculate size accurately
            total_size_bytes = 0
            if model_path.is_file():
                total_size_bytes = model_path.stat().st_size
            else:
                total_size_bytes = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
            
            # Map download quant string to engine quant_method.
            # GGUF quant variants (Q4_K_M, Q5_K_M, Q8_0, etc.) imply gguf quant_method.
            # Full model repos imply "none" (LayerStream can later re-quantize to int8).
            quant_string = file_info.quantization.value if file_info and file_info.quantization else (quant if quant else "none")
            if quant_string and quant_string not in ("full", "none", ""):
                quant_method = "gguf"  # All GGUF variants share the same engine quant_method
            else:
                quant_method = "none"

            # Create metadata
            metadata = {
                "id": model_name,
                "name": info.name,
                "family": info.family or model_name.split(":")[0],
                "parameters": info.parameters or "",
                "quant": quant_string,
                "quant_method": quant_method,
                "size_gb": round(total_size_bytes / (1024**3), 2),
                "path": str(model_path),
                "checksum": file_info.checksum if file_info else "",
                "downloaded": True,
                "modes_supported": ["fullram", "layerstream"],
                "created_at": datetime.now().isoformat()
            }
            
            # Save metadata
            with open(model_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Register
            await self.registry.add_model(metadata)
            
            self.download_status[model_name]["status"] = "complete"
            self.download_status[model_name]["progress"] = 100
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.download_status[model_name]["status"] = "error"
            self.download_status[model_name]["error"] = str(e)
            
        finally:
            if model_name in self._download_tasks:
                del self._download_tasks[model_name]
    
    async def delete_model(self, model_name: str) -> bool:
        """Delete a model"""
        model = await self.registry.get_model(model_name)
        if not model:
            return False
        
        # Delete files
        model_path = Path(model["path"])
        if model_path.is_dir():
            model_dir = model_path
        else:
            model_dir = model_path.parent
            
        if model_dir.exists():
            import shutil
            shutil.rmtree(model_dir)
        
        # Remove from registry
        await self.registry.delete_model(model_name)
        
        return True
