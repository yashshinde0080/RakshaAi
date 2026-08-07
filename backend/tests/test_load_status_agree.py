"""Regression: loading by display name must not desync /system/status.

Drives the real ``ModelManager.load_model`` path (stubbed registry + engine
factory — no model files touched) through the exact scenario that previously
broke: a client calls ``POST /v1/models/load`` with a *display name*
("Qwen3.5-0.8B"), and then ``GET /v1/system/status`` reports a different model.

Before the fix, the fuzzy matcher picked the ``split:`` variant, so
``app.state.active_model`` (the single source ``/status`` reads) became an id
the caller never asked for and disagreed with the load response. Now the
display name must resolve to the base id, and the two endpoints must agree.
Explicit ``split:...`` ids still resolve to the split model.
"""
import asyncio
import types

import app.core.engine_factory as engine_factory_mod
from app.services.model_manager import ModelManager

BASE = {"id": "Qwen/Qwen3.5-0.8B", "path": "/models/base"}
SPLIT = {"id": "split:Qwen-Qwen3.5-0.8B", "path": "/offload/cache"}


class _FakeEngine:
    """Minimal stand-in — load_model only touches .mode / .task_metadata."""

    mode = "fullram"
    task_metadata = {}

    async def unload(self):
        pass


class _FakeFactory:
    """Replaces EngineFactory so load_model never touches real engines."""

    def __init__(self, hardware_profile):
        self.hardware_profile = hardware_profile

    async def create_engine(self, model_path, mode="auto", model_metadata=None):
        engine = _FakeEngine()
        engine.mode = "fullram" if mode == "auto" else mode
        return engine


def _make_manager(monkeypatch, models):
    """ModelManager with a stubbed registry, no real DB/engines/app involved."""
    manager = ModelManager.__new__(ModelManager)  # skip the heavy __init__
    app = types.SimpleNamespace(
        state=types.SimpleNamespace(
            hardware_profile={},
            active_engine=None,
            active_model=None,
            active_mode=None,
        )
    )
    manager.app = app

    async def fake_get_model(model_id):
        return next((m for m in models if m["id"] == model_id), None)

    async def fake_list_models():
        return models

    manager.get_model = fake_get_model
    manager.list_models = fake_list_models
    monkeypatch.setattr(engine_factory_mod, "EngineFactory", _FakeFactory)
    return manager, app


def test_display_name_load_response_and_status_agree(monkeypatch):
    """The regression: 'Qwen3.5-0.8B' must load the base id, and the load
    response must equal what /system/status would report."""
    manager, app = _make_manager(monkeypatch, [SPLIT, BASE])

    result = asyncio.run(manager.load_model("Qwen3.5-0.8B", mode="auto"))

    # load response reports the base model the caller meant, not the split view
    assert result["model"] == BASE["id"]
    assert result["model"] != SPLIT["id"]
    # GET /v1/system/status reads app.state.active_model / active_mode
    assert app.state.active_model == BASE["id"]
    assert app.state.active_mode == result["mode"]
    # the exact regression: the two endpoints agree
    assert app.state.active_model == result["model"]


def test_explicit_split_request_keeps_split_id_and_agrees(monkeypatch):
    """Explicit split:... ids still load the split model; status stays in sync."""
    manager, app = _make_manager(monkeypatch, [SPLIT, BASE])

    result = asyncio.run(
        manager.load_model("split:Qwen-Qwen3.5-0.8B", mode="layerstream")
    )

    assert result["model"] == SPLIT["id"]
    assert app.state.active_model == SPLIT["id"]
    assert app.state.active_model == result["model"]
    assert app.state.active_mode == result["mode"] == "layerstream"
