"""Regression: split models must never hit the fullram engine on mode=auto.

Split models live in ``workspace/offload_cache`` as per-layer safetensors
(``embed``/``layer_N``/``lm_head``) and only support the LayerStream engine
(registry ``modes_supported: ["layerstream"]``). The auto-mode RAM heuristic
picks fullram for a small split model, and FullRAMEngine then runs
``from_pretrained`` on a directory with no consolidated weights — the
"no file named model.safetensors, or pytorch_model.bin" failure.

These tests drive the real ``ModelManager.load_model`` with a stubbed registry
and engine factory (no model files touched), asserting the resolved engine
mode and the path handed to the factory.
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
    """Records what load_model asked for; never touches real engines."""

    def __init__(self, hardware_profile):
        self.hardware_profile = hardware_profile
        self.created = []

    async def create_engine(self, model_path, mode="auto", model_metadata=None):
        self.created.append({"path": model_path, "mode": mode})
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
    factory = _FakeFactory({})
    # load_model does `from app.core.engine_factory import EngineFactory` at
    # call time, so patching the module attribute is enough.
    monkeypatch.setattr(engine_factory_mod, "EngineFactory", lambda hw: factory)
    return manager, app, factory


def test_split_auto_forces_layerstream(monkeypatch):
    """mode=auto on a split id must resolve to layerstream, never fullram."""
    manager, app, factory = _make_manager(monkeypatch, [SPLIT, BASE])

    result = asyncio.run(manager.load_model(SPLIT["id"], mode="auto"))

    assert factory.created[0]["mode"] == "layerstream"
    assert result["mode"] == "layerstream"
    assert app.state.active_mode == "layerstream"
    assert app.state.active_model == SPLIT["id"]


def test_split_explicit_fullram_swaps_to_base_path(monkeypatch):
    """Explicit fullram on a split still redirects to the base model's dir."""
    manager, app, factory = _make_manager(monkeypatch, [SPLIT, BASE])

    result = asyncio.run(manager.load_model(SPLIT["id"], mode="fullram"))

    assert factory.created[0]["path"] == BASE["path"]  # base weights dir
    assert factory.created[0]["mode"] == "fullram"


def test_non_split_auto_unaffected(monkeypatch):
    """auto on a base model stays auto — resolution is left to the factory."""
    manager, app, factory = _make_manager(monkeypatch, [SPLIT, BASE])

    result = asyncio.run(manager.load_model(BASE["id"], mode="auto"))

    assert factory.created[0]["mode"] == "auto"
    assert result["mode"] == "fullram"  # the factory's own auto resolution
