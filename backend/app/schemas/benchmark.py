"""Benchmark Schemas"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BenchmarkRequest(BaseModel):
    model: str = Field(default="", description="Model name (empty = currently loaded)")
    backend: str = Field(default="llama.cpp", description="Backend: llama.cpp, ollama, mlx")
    iterations: int = Field(default=3, ge=1, le=10)
    max_tokens: int = Field(default=100, ge=10, le=500)
    duration_seconds: Optional[int] = Field(default=None, description="Bench duration (overrides iterations)")


class BenchmarkRun(BaseModel):
    iteration: int
    tokens: int
    time_seconds: float
    tokens_per_second: float


class BenchmarkSummary(BaseModel):
    total_tokens: int
    total_time_seconds: float
    average_tokens_per_second: float
    peak_ram_gb: float


class BenchmarkResult(BaseModel):
    model: str
    mode: str
    iterations: int
    runs: List[Dict[str, Any]]
    summary: Dict[str, Any]