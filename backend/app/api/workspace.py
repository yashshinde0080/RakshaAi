"""Workspace Snapshots API — save/restore sessions"""
import json
import os
import time
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _workspace_dir(app) -> str:
    d = os.path.join(BASE, "workspace", "sessions")
    os.makedirs(d, exist_ok=True)
    return os.path.abspath(d)


@router.post("/save")
async def save_workspace(request: Request):
    """Save current workspace state as a snapshot"""
    app = request.app
    data = {
        "model": app.state.active_model,
        "mode": app.state.active_mode,
        "timestamp": time.time(),
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    snap_id = f"snap-{int(time.time())}"
    path = os.path.join(_workspace_dir(app), f"{snap_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return {"id": snap_id, **data}


@router.get("/")
async def list_workspaces(request: Request):
    """List saved workspace snapshots"""
    snapshots = []
    sess_dir = _workspace_dir(request.app)
    if not os.path.isdir(sess_dir):
        return {"snapshots": []}
    for fname in sorted(os.listdir(sess_dir), reverse=True):
        if fname.endswith(".json"):
            path = os.path.join(sess_dir, fname)
            try:
                with open(path) as f:
                    snap = json.load(f)
                snapshots.append({"id": fname.replace(".json", ""), **snap})
            except (json.JSONDecodeError, OSError):
                continue
    return {"snapshots": snapshots}


@router.get("/{snap_id}")
async def load_workspace(request: Request, snap_id: str):
    """Load a workspace snapshot"""
    path = os.path.join(_workspace_dir(request.app), f"{snap_id}.json")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    with open(path) as f:
        snap = json.load(f)
    return snap


@router.delete("/{snap_id}")
async def delete_workspace(request: Request, snap_id: str):
    """Delete a workspace snapshot"""
    path = os.path.join(_workspace_dir(request.app), f"{snap_id}.json")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    os.remove(path)
    return {"status": "deleted", "id": snap_id}
