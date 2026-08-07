"""Hardware Detection"""
import os
import platform
import subprocess
from typing import Dict, Any, Optional
import psutil


class HardwareDetector:
    """Detect system hardware capabilities"""
    
    def detect(self) -> Dict[str, Any]:
        """Detect and return hardware profile"""
        return {
            "cpu_name": self._get_cpu_name(),
            "cpu_cores": psutil.cpu_count(logical=False) or 1,
            "cpu_threads": psutil.cpu_count(logical=True) or 1,
            "has_avx2": self._check_avx2(),
            "has_avx512": self._check_avx512(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "gpu_name": self._get_gpu_name(),
            "gpu_vram_gb": self._get_gpu_vram(),
            "disk_type": self._detect_disk_type(),
            "disk_speed_mb_s": self._benchmark_disk_speed()
        }
    
    def _get_cpu_name(self) -> str:
        """Get CPU name"""
        try:
            if platform.system() == "Windows":
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
                )
                return winreg.QueryValueEx(key, "ProcessorNameString")[0]
            elif platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
            elif platform.system() == "Darwin":
                return subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"]
                ).decode().strip()
        except:
            pass
        return platform.processor() or "Unknown CPU"
    
    def _check_avx2(self) -> bool:
        """Check AVX2 support"""
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    return "avx2" in f.read().lower()
            elif platform.system() == "Windows":
                # Would need more complex check
                return True
        except:
            pass
        return False
    
    def _check_avx512(self) -> bool:
        """Check AVX512 support"""
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    return "avx512" in f.read().lower()
        except:
            pass
        return False
    
    def _get_gpu_name(self) -> Optional[str]:
        """Get GPU name"""
        try:
            # Try NVIDIA
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def _get_gpu_vram(self) -> Optional[float]:
        """Get GPU VRAM in GB"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return round(float(result.stdout.strip()) / 1024, 2)
        except:
            pass
        return None
    
    def _detect_disk_type(self) -> str:
        """Detect disk type (SSD/HDD)"""
        try:
            if platform.system() == "Linux":
                # Check if root disk is SSD
                result = subprocess.run(
                    ["cat", "/sys/block/sda/queue/rotational"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return "HDD" if result.stdout.strip() == "1" else "SSD"
        except:
            pass
        return "Unknown"
    
    def _benchmark_disk_speed(self) -> float:
        """Quick disk speed benchmark"""
        import tempfile
        import time
        
        try:
            # Write test
            data = b"x" * (10 * 1024 * 1024)  # 10MB
            
            with tempfile.NamedTemporaryFile(delete=True) as f:
                start = time.perf_counter()
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
                elapsed = time.perf_counter() - start
                
            speed = (10 / elapsed) if elapsed > 0 else 0
            return round(speed, 2)
        except:
            return 100.0  # Default