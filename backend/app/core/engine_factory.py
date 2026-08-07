"""Engine Factory"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import os

from app.core.memory_manager import MemoryManager
from app.engines.base import BaseEngine
from app.engines.fullram.executor import FullRAMEngine
from app.engines.layerstream.executor import LayerStreamEngine
from app.engines.manualstream.executor import ManualStreamEngine


class EngineFactory:
    """Factory for creating inference engines"""
    
    def __init__(self, hardware_profile: Dict[str, Any]):
        self.hardware = hardware_profile
        self.memory_manager = MemoryManager()
    
    async def create_engine(
        self,
        model_path: str,
        mode: str = "auto",
        model_metadata: Optional[Dict[str, Any]] = None,
    ) -> BaseEngine:
        """Create appropriate engine"""
        
        model_path = Path(model_path)
        engine_model_path_str = str(model_path)
        model_size = 0
        
        # If directory, determine model size correctly and ensure we pass the correct directory
        if model_path.is_dir():
             # If config.json exists, this is a standard HuggingFace repo
             if (model_path / "config.json").exists():
                 engine_model_path_str = str(model_path)
                 model_size = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
             else:
                 # Try to find GGUF or SafeTensors as fallback for size calculations
                 gguf_files = list(model_path.glob("*.gguf")) + list(model_path.glob("*.gguf.enc"))
                 if gguf_files:
                     # Currently FullRAMEngine uses AutoModelForCausalLM which prefers directories
                     # Depending on the engine, GGUF might require a specific loader
                     # But for HF transformers, passing the directory is usually better if possible
                     engine_model_path_str = str(gguf_files[0])
                     model_size = gguf_files[0].stat().st_size
                 else:
                     st_files = list(model_path.glob("*.safetensors")) + list(model_path.glob("*.safetensors.enc"))
                     if st_files:
                         # Even if safetensors exist without config.json, passing directory is safer for HF
                         engine_model_path_str = str(model_path)
                         model_size = sum(f.stat().st_size for f in st_files)
                     else:
                         # No recognized models found
                         pass
        else:
            model_size = model_path.stat().st_size if model_path.exists() and model_path.is_file() else 0
            engine_model_path_str = str(model_path)
            
        print(f"DEBUG: EngineFactory creating engine for {engine_model_path_str}, size: {model_size/(1024**2):.2f} MB")
        
        # 1. Resolve task to determine if streaming is possible
        from app.core.task_resolver import TaskResolver
        task_metadata = TaskResolver.resolve(engine_model_path_str)
        is_generative = task_metadata.get("is_generative", False)

        # Determine mode
        if mode == "auto":
            # Use llmfit scoring when metadata available, else legacy size-based
            if model_metadata:
                suggested = self.memory_manager.suggest_mode(
                    model_size, model_metadata=model_metadata
                )
            else:
                suggested = self.memory_manager.suggest_mode(model_size)
            if suggested == "layerstream" and not is_generative:
                # Fallback to fullram for non-generative tasks if layerstream suggested
                mode = "fullram"
            else:
                mode = suggested
                
            if mode == "insufficient":
                raise RuntimeError("Insufficient memory for any execution mode")
        
        # Read quant_method from model metadata (set during download).
        # Maps GGUF quant strings (Q4_K_M, Q5_K_M, Q8_0) to quant_method="gguf".
        quant_method = "none"
        metadata_path = model_path / "metadata.json" if isinstance(model_path, Path) else None
        if metadata_path and metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                quant_method = metadata.get("quant_method", "none")
            except Exception:
                quant_method = "none"

        # Create engine
        if mode == "fullram":
            engine = FullRAMEngine(
                model_path=engine_model_path_str,
                hardware=self.hardware,
                memory_manager=self.memory_manager
            )
        elif mode == "layerstream":
            engine = LayerStreamEngine(
                model_path=engine_model_path_str,
                hardware=self.hardware,
                memory_manager=self.memory_manager,
                quant_method=quant_method
            )
        elif mode == "manualstream":
            engine = ManualStreamEngine(
                model_path=engine_model_path_str,
                hardware=self.hardware,
                memory_manager=self.memory_manager
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        # Initialize
        await engine.load()
        
        return engine
    
    def get_recommended_mode(self, model_size_bytes: int) -> str:
        """Get recommended mode for model"""
        return self.memory_manager.suggest_mode(model_size_bytes)