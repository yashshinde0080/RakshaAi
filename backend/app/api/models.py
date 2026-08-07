"""Models API Endpoints"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import Optional

from app.schemas.models import (
    ModelInfo,
    ModelList,
    PullRequest,
    PullStatus,
    LoadRequest,
    RecommendRequest,
    RecommendResult,
)
from app.core.engine_factory import EngineFactory


router = APIRouter()


@router.get("/", response_model=ModelList)
async def list_models(request: Request):
    """List installed models"""
    models = await request.app.state.model_manager.list_models()
    return ModelList(models=models)


@router.post("/recommend", response_model=list[RecommendResult])
async def recommend_models(
    request: Request,
    rec: RecommendRequest,
):
    """Recommend models for hardware + use case via llmfit.

    Returns top-N models scored by fit, speed, quality.
    Falls back to static list if llmfit unavailable.
    """
    try:
        from llmfit import recommend as llmfit_recommend
        from llmfit.hardware import probe_hardware

        hw = probe_hardware()
        if rec.max_ram_gb:
            hw.ram_total_gb = min(hw.ram_total_gb, rec.max_ram_gb)

        results = llmfit_recommend(
            hardware=hw,
            use_case=rec.use_case,
            prefer_speed=rec.prefer_speed,
            top_n=rec.top_n,
        )
        return [
            RecommendResult(
                name=r.name,
                fit_score=r.fit_score,
                est_tok_s=r.est_tok_s,
                ram_gb=r.ram_gb,
                context=r.context,
                quant=r.quant,
                quality_score=getattr(r, "quality_score", 0.0),
                backend=getattr(r, "backend", "llama.cpp"),
                download_url=getattr(r, "download_url", ""),
                reasoning=getattr(r, "reasoning", ""),
            )
            for r in results
        ]
    except ImportError:
        # llmfit not installed -- return static fallback
        return _fallback_recommendations(rec)
    except Exception as e:
        print(f"llmfit recommend failed: {e}")
        return _fallback_recommendations(rec)


def _fallback_recommendations(rec: RecommendRequest) -> list[RecommendResult]:
    """Static fallback when llmfit unavailable."""
    fallback = [
        RecommendResult(
            name="Qwen2.5-Coder-7B-Instruct-Q4_K_M",
            fit_score=0.85, est_tok_s=35, ram_gb=5.2, context=32768,
            quant="Q4_K_M", quality_score=0.78, backend="llama.cpp",
            download_url="", reasoning="Well-balanced coding model for most hardware",
        ),
        RecommendResult(
            name="Phi-3.5-mini-instruct-Q4_K_M",
            fit_score=0.92, est_tok_s=50, ram_gb=2.8, context=131072,
            quant="Q4_K_M", quality_score=0.72, backend="llama.cpp",
            download_url="", reasoning="Lightweight, fast, fits nearly any device",
        ),
        RecommendResult(
            name="Llama-3.2-3B-Instruct-Q4_K_M",
            fit_score=0.90, est_tok_s=55, ram_gb=2.2, context=131072,
            quant="Q4_K_M", quality_score=0.69, backend="llama.cpp",
            download_url="", reasoning="Smallest Llama 3, great for low-RAM systems",
        ),
        RecommendResult(
            name="Mistral-7B-Instruct-v0.3-Q4_K_M",
            fit_score=0.87, est_tok_s=38, ram_gb=4.8, context=32768,
            quant="Q4_K_M", quality_score=0.80, backend="llama.cpp",
            download_url="", reasoning="Solid general-purpose 7B with large context",
        ),
    ]
    # Filter by RAM if specified
    if rec.max_ram_gb:
        fallback = [m for m in fallback if m.ram_gb <= rec.max_ram_gb]
    if rec.prefer_speed:
        fallback.sort(key=lambda m: m.est_tok_s, reverse=True)
    else:
        fallback.sort(key=lambda m: m.fit_score, reverse=True)
    return fallback[: rec.top_n]


@router.post("/pull")
async def pull_model(
    request: Request, 
    pull_request: PullRequest,
    background_tasks: BackgroundTasks
):
    """Pull/download a model"""
    model_manager = request.app.state.model_manager
    
    # Check if already downloading
    if model_manager.is_downloading(pull_request.model):
        return {"status": "already_downloading", "model": pull_request.model}
    
    # Check if already exists
    if await model_manager.model_exists(pull_request.model):
        return {"status": "exists", "model": pull_request.model}
    
    # Start download in background
    background_tasks.add_task(
        model_manager.download_model,
        pull_request.model,
        pull_request.quant
    )
    
    return {"status": "downloading", "model": pull_request.model}


@router.get("/pull/status/{model_name:path}")
async def pull_status(request: Request, model_name: str):
    """Get download status"""
    status = request.app.state.model_manager.get_download_status(model_name)
    return PullStatus(**status)


@router.post("/load")
async def load_model(request: Request, load_request: LoadRequest):
    """Load model into RAM/VRAM"""
    app = request.app
    manager: ModelManager = app.state.model_manager
    
    try:
        result = await manager.load_model(
            model_id=load_request.model,
            mode=load_request.mode
        )
        return result
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=f"Model configuration error: {msg}")
    except RuntimeError as e:
        msg = str(e)
        # Unsupported arch/format is a client-side model choice issue, not a server crash
        if "not supported" in msg.lower() or "architecture" in msg.lower():
            raise HTTPException(status_code=422, detail=msg)
        raise HTTPException(status_code=500, detail=f"Failed to load model: {msg}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@router.post("/unload")
async def unload_model(request: Request):
    """Unload active model"""
    manager: ModelManager = request.app.state.model_manager
    await manager.unload_model()
    return {"status": "unloaded"}


@router.post("/refresh")
async def refresh_models(request: Request):
    """Scan models directory and update registry"""
    manager: ModelManager = request.app.state.model_manager
    await manager.scan_installed()
    models = await manager.list_models()
    return {"status": "refreshed", "count": len(models)}


@router.get("/current")
async def get_current_model(request: Request):
    """Get metadata about currently loaded model for dynamic task UI routing"""
    app = request.app
    if not app.state.active_engine:
        return {"loaded": False}
        
    engine = app.state.active_engine
    
    # Try fetching task_metadata
    task_info = getattr(engine, "task_metadata", {})
    if not task_info:
        # Fallback
        from app.core.task_resolver import TaskResolver
        task_info = TaskResolver.resolve(engine.model_path)
        
    return {
        "loaded": True,
        "model": app.state.active_model,
        "mode": app.state.active_mode,
        "task_type": task_info.get("task_type", "unknown"),
        "input_modality": task_info.get("input_modality", "text"),
        "is_generative": task_info.get("is_generative", False),
        "ram_usage": getattr(engine, "get_memory_usage", lambda: {})()
    }


@router.get("/{model_name:path}", response_model=ModelInfo)
async def get_model(request: Request, model_name: str):
    """Get model details"""
    model = await request.app.state.model_manager.get_model(model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelInfo(**model)


@router.delete("/{model_name:path}")
async def delete_model(request: Request, model_name: str):
    """Delete a model"""
    model_manager = request.app.state.model_manager
    
    # Check if model is currently loaded
    if request.app.state.active_model == model_name:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete currently loaded model"
        )
    
    success = await model_manager.delete_model(model_name)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {"status": "deleted", "model": model_name}