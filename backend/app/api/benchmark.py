"""Benchmark API Endpoints"""
import asyncio
import time
from fastapi import APIRouter, HTTPException, Request

from app.schemas.benchmark import BenchmarkRequest, BenchmarkResult


router = APIRouter()


@router.post("/run", response_model=BenchmarkResult)
async def run_benchmark(request: Request, bench_request: BenchmarkRequest):
    """Run inference benchmark.

    Uses llmfit.bench() when available for real tok/s, TTFT, memory measurement.
    Falls back to in-process inference timing.
    """
    app = request.app

    # Determine which model to benchmark
    model_name = bench_request.model or app.state.active_model
    if not model_name:
        raise HTTPException(status_code=400, detail="No model specified and none loaded")

    # Try llmfit benchmark first
    try:
        return await _llmfit_benchmark(model_name, bench_request, app)
    except ImportError:
        pass  # fall through to legacy
    except Exception as e:
        print(f"llmfit bench failed, falling back: {e}")

    # Legacy in-process benchmark
    return await _legacy_benchmark(app, bench_request)


async def _llmfit_benchmark(
    model_name: str,
    bench_request: BenchmarkRequest,
    app,
) -> BenchmarkResult:
    """Benchmark via llmfit for real tok/s / TTFT."""
    from llmfit import benchmark as llmfit_bench

    duration = bench_request.duration_seconds or (bench_request.iterations * 10)
    result = await llmfit_bench(
        model=model_name,
        backend=bench_request.backend,
        duration_seconds=duration,
    )

    runs = []
    for i, run in enumerate(getattr(result, "runs", []) or []):
        runs.append({
            "iteration": i + 1,
            "tokens": getattr(run, "tokens", 0),
            "time_seconds": round(getattr(run, "time_s", 0), 3),
            "tokens_per_second": round(getattr(run, "tok_s", 0), 2),
        })

    if not runs:
        runs.append({
            "iteration": 1,
            "tokens": 0,
            "time_seconds": round(getattr(result, "duration_s", 0), 3),
            "tokens_per_second": round(getattr(result, "tok_s", 0), 2),
        })

    summary = {
        "total_tokens": sum(r.get("tokens", 0) for r in runs),
        "total_time_seconds": round(sum(r.get("time_seconds", 0) for r in runs), 3),
        "average_tokens_per_second": round(
            getattr(result, "tok_s", 0), 2
        ),
        "peak_ram_gb": round(getattr(result, "memory_used_gb", 0), 2),
        "ttft_ms": round(getattr(result, "ttft_ms", 0), 2),
        "verified": getattr(result, "verified", False),
    }

    return BenchmarkResult(
        model=model_name,
        mode="llmfit",
        iterations=len(runs),
        runs=runs,
        summary=summary,
    )


async def _legacy_benchmark(app, bench_request: BenchmarkRequest) -> BenchmarkResult:
    """In-process benchmark using loaded engine."""
    if not app.state.active_engine:
        raise HTTPException(status_code=400, detail="No model loaded")

    engine = app.state.active_engine
    model_name = app.state.active_model

    test_prompts = [
        "Hello, how are you?",
        "Explain quantum computing in simple terms.",
        "Write a short poem about artificial intelligence.",
    ]

    runs = []
    total_tokens = 0
    total_time = 0

    for i in range(bench_request.iterations):
        prompt = test_prompts[i % len(test_prompts)]

        start_time = time.perf_counter()
        response = await engine.generate(
            prompt=prompt,
            max_tokens=bench_request.max_tokens,
        )
        elapsed = time.perf_counter() - start_time

        tokens = response.get("completion_tokens", 0)
        total_tokens += tokens
        total_time += elapsed

        runs.append({
            "iteration": i + 1,
            "tokens": tokens,
            "time_seconds": round(elapsed, 3),
            "tokens_per_second": round(tokens / elapsed, 2) if elapsed > 0 else 0,
        })

    avg_tps = total_tokens / total_time if total_time > 0 else 0

    summary = {
        "total_tokens": total_tokens,
        "total_time_seconds": round(total_time, 3),
        "average_tokens_per_second": round(avg_tps, 2),
        "peak_ram_gb": engine.get_memory_usage().get("peak_ram_gb", 0),
    }

    return BenchmarkResult(
        model=model_name or "unknown",
        mode=app.state.active_mode or "unknown",
        iterations=bench_request.iterations,
        runs=runs,
        summary=summary,
    )


@router.get("/compare")
async def compare_modes(request: Request):
    """Compare fullram vs layerstream performance"""
    app = request.app
    
    if not app.state.active_model:
        raise HTTPException(status_code=400, detail="No model loaded")
    
    model_name = app.state.active_model
    engine = app.state.active_engine
    current_mode = app.state.active_mode
    
    # ponytail: compares current mode, the other mode shows how to switch
    # ponytail: to compare both, reload model in each mode separately
    test_prompt = "Hello, how are you?"
    results = {}
    
    for mode in ["fullram", "layerstream"]:
        if mode == current_mode:
            start = time.perf_counter()
            response = await engine.generate(
                input_data=test_prompt,
                max_tokens=50,
            )
            elapsed = time.perf_counter() - start
            tokens = response.get("completion_tokens", 0) or len(response.get("text", "").split())
            results[mode] = {
                "tokens": tokens,
                "time_s": round(elapsed, 3),
                "tps": round(tokens / elapsed, 2) if elapsed > 0 else 0,
                "ram_gb": engine.get_memory_usage().get("ram_used_gb", 0),
            }
        else:
            results[mode] = {"available": False, "reason": f"Model loaded in {current_mode}. Switch to {mode} to benchmark."}
    
    return {
        "model": model_name,
        "current_mode": current_mode,
        "results": results,
    }