"""Regression tests for the model id fuzzy matcher.

Pins the fix for the /load-vs-/status disagreement: a display-name request
like "Qwen3.5-0.8B" must resolve to the base model id, not the split variant
(which would set ``app.state.active_model`` to an id the caller never asked
for). Explicit "split:..." ids still resolve through the direct registry
lookup in ``load_model``, which runs before this matcher.
"""
from app.services.model_manager import _fuzzy_match_model

BASE = {"id": "Qwen/Qwen3.5-0.8B"}
SPLIT = {"id": "split:Qwen-Qwen3.5-0.8B"}
BITNET = {"id": "microsoft/bitnet-b1.58-2B-4T"}


def test_display_name_prefers_base_over_split():
    """'Qwen3.5-0.8B' previously fuzzy-matched to split:... — must now be base."""
    hit = _fuzzy_match_model([SPLIT, BASE], "Qwen3.5-0.8B")
    assert hit is BASE


def test_split_variant_never_wins_even_when_listed_first():
    hit = _fuzzy_match_model([SPLIT, BASE], "Qwen3.5-0.8B")
    assert hit is BASE
    # also with only the split variant present, nothing should match
    assert _fuzzy_match_model([SPLIT], "Qwen3.5-0.8B") is None


def test_exact_clean_match_wins():
    models = [SPLIT, BASE]
    assert _fuzzy_match_model(models, "qwen-qwen3.5-0.8b") is BASE
    assert _fuzzy_match_model(models, "qwen/qwen3.5-0.8b") is BASE


def test_containment_match_finds_base():
    assert _fuzzy_match_model([SPLIT, BITNET, BASE], "qwen3.5-0.8b") is BASE
    assert _fuzzy_match_model([BITNET, BASE], "bitnet-b1.58-2B-4T") is BITNET


def test_no_match_returns_none():
    assert _fuzzy_match_model([SPLIT, BASE, BITNET], "nonexistent-model") is None
    assert _fuzzy_match_model([], "anything") is None
