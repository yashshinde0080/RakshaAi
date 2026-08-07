"""WebSocket Metrics Streaming"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import psutil

router = APIRouter()

# Connected clients
clients: Set[WebSocket] = set()


@router.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket):
    """Stream system metrics."""
    await websocket.accept()
    clients.add(websocket)
    
    try:
        # Initialize baseline for calculations
        psutil.cpu_percent(interval=None)
        prev_disk_io = psutil.disk_io_counters()
        
        while True:
            # Gather metrics - use interval=0.1 to get a representative slice
            cpu = psutil.cpu_percent(interval=0.1)
            await asyncio.sleep(0.9)  # Total 1s cycle
            
            memory = psutil.virtual_memory()
            
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io and prev_disk_io:
                    disk_read = (disk_io.read_bytes - prev_disk_io.read_bytes) / (1024**2)
                    disk_write = (disk_io.write_bytes - prev_disk_io.write_bytes) / (1024**2)
                else:
                    disk_read = 0
                    disk_write = 0
                prev_disk_io = disk_io
            except:
                disk_read = 0
                disk_write = 0
            
            # GPU Usage (NVIDIA)
            gpu_percent = 0
            gpu_vram_used = 0
            try:
                import subprocess
                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=0.5
                )
                if res.returncode == 0:
                    gpu_data = res.stdout.strip().split(",")
                    gpu_percent = float(gpu_data[0])
                    gpu_vram_used = round(float(gpu_data[1]) / 1024, 2)
            except:
                pass

            task_type = None
            is_generative = False
            app = websocket.app
            engine_stats = {}
            
            if hasattr(app.state, 'active_engine') and app.state.active_engine:
                engine_stats = app.state.active_engine.get_memory_usage()
                task_metadata = getattr(app.state.active_engine, "task_metadata", {})
                task_type = task_metadata.get("task_type")
                is_generative = task_metadata.get("is_generative", False)
            
            metrics = {
                "cpu_percent": cpu,
                "gpu_percent": gpu_percent,
                "gpu_vram_used": gpu_vram_used,
                "ram_used_gb": round(memory.used / (1024**3), 2),
                "ram_total_gb": round(memory.total / (1024**3), 2),
                "ram_percent": memory.percent,
                "disk_read_mb": round(disk_read, 2),
                "disk_write_mb": round(disk_write, 2),
                "model_loaded": app.state.active_model if hasattr(app.state, 'active_model') else None,
                "mode": app.state.active_mode if hasattr(app.state, 'active_mode') else None,
                "task_type": task_type,
                "is_generative": is_generative,
                "engine_stats": engine_stats
            }
            
            await websocket.send_json(metrics)
            
    except WebSocketDisconnect:
        clients.remove(websocket)
    except Exception:
        clients.discard(websocket)


async def broadcast_metrics(metrics: dict):
    """Broadcast metrics to all connected clients"""
    for client in clients.copy():
        try:
            await client.send_json(metrics)
        except:
            clients.discard(client)