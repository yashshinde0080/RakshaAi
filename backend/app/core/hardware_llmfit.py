"""llmfit Hardware Probe Wrapper

Thin wrapper around llmfit.hardware.probe_hardware() that returns
the same Dict[str, Any] format as HardwareDetector.detect().

llmfit detects RAM, CPU (AVX2/AVX-512/NEON), GPU VRAM (NVIDIA/AMD/Apple),
disk speed, and available backends -- all in a single call.
"""
import platform
from typing import Dict, Any
import psutil


def detect_via_llmfit() -> Dict[str, Any]:
    """Probe hardware via llmfit and return SovereignAI-compatible profile.

    Falls back to existing HardwareDetector if llmfit is not installed.
    """
    try:
        from llmfit.hardware import probe_hardware

        hw = probe_hardware()
        profile = {
            "cpu_name": getattr(hw, "cpu_name", platform.processor() or "Unknown CPU"),
            "cpu_cores": getattr(hw, "cpu_cores", psutil.cpu_count(logical=False) or 1),
            "cpu_threads": getattr(hw, "cpu_threads", psutil.cpu_count(logical=True) or 1),
            "has_avx2": "avx2" in (getattr(hw, "cpu_features", "") or "").lower(),
            "has_avx512": "avx512" in (getattr(hw, "cpu_features", "") or "").lower(),
            "ram_total_gb": getattr(hw, "ram_total_gb", round(psutil.virtual_memory().total / (1024**3), 2)),
            "gpu_name": getattr(hw, "gpu_name", None),
            "gpu_vram_gb": getattr(hw, "gpu_vram_gb", None),
            "disk_type": "SSD" if (getattr(hw, "disk_speed_mb_s", 0) or 0) > 300 else "HDD",
            "disk_speed_mb_s": getattr(hw, "disk_speed_mb_s", 100.0),
            "available_backends": getattr(hw, "available_backends", []),
            "_source": "llmfit",
        }
        return profile
    except ImportError:
        # llmfit not installed -- return empty shell; caller can fall back
        return {"_source": "unavailable"}
    except Exception as exc:
        print(f"llmfit probe failed: {exc}")
        return {"_source": "error", "_error": str(exc)}


def detect_hardware() -> Dict[str, Any]:
    """Top-level hardware detection.

    Prefers llmfit for richer detection (GPU, disk, backends).
    Falls back to HardwareDetector when llmfit unavailable.
    """
    result = detect_via_llmfit()
    if result.get("_source") == "llmfit":
        return result

    # Fallback
    from app.core.hardware_detector import HardwareDetector
    fallback = HardwareDetector().detect()
    fallback["_source"] = "legacy"
    return fallback
