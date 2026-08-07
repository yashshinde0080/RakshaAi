import time
import psutil
import torch
from typing import Dict, Any

class BenchmarkTracker:
    def __init__(self):
        self.stats = {
            "peak_vram_mb": 0.0,
            "peak_ram_mb": 0.0,
            "disk_read_time_total": 0.0,
            "compute_time": 0.0,
            "tokens_per_second": 0.0,
            "layer_load_time_avg": 0.0,
            "kv_cache_size_mb": 0.0,
            "num_layer_loads": 0,
        }
        self.process = psutil.Process()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def update_vram(self):
        if torch.cuda.is_available():
            peak = torch.cuda.max_memory_allocated() / (1024 ** 2)
            self.stats["peak_vram_mb"] = max(self.stats["peak_vram_mb"], peak)

    def update_ram(self):
        ram = self.process.memory_info().rss / (1024 ** 2)
        self.stats["peak_ram_mb"] = max(self.stats["peak_ram_mb"], ram)

    def record_layer_load(self, duration: float):
        self.stats["disk_read_time_total"] += duration
        self.stats["num_layer_loads"] += 1
        self.stats["layer_load_time_avg"] = self.stats["disk_read_time_total"] / self.stats["num_layer_loads"]

    def record_compute(self, duration: float):
        self.stats["compute_time"] += duration

    def set_kv_cache_size(self, size_mb: float):
        self.stats["kv_cache_size_mb"] = size_mb

    def get_stats(self) -> Dict[str, Any]:
        self.update_vram()
        self.update_ram()
        return self.stats
