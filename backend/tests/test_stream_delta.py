"""Regression test for the LayerStream rolling-window stream delta.

Rebuilds a sentence token-by-token through ``_stream_delta`` and asserts the
streamed reconstruction exactly equals the full tokenizer decode. This pins the
BPE subword-merge behavior (e.g. ``" wor" + "ld" -> " world"``) that the old
prefix slice ``full_text[len(decoded_text):]`` could drop or duplicate.

Requires the split Qwen3.5 tokenizer on disk — skips otherwise.
"""
from pathlib import Path

import pytest

from app.engines.layerstream.executor import _stream_delta

_ROOT = Path(__file__).resolve().parents[2]
_OFFLOAD = _ROOT / "workspace" / "offload_cache" / "Qwen-Qwen3.5-0.8B"
_INSTALLED = _ROOT / "workspace" / "models" / "installed" / "Qwen-Qwen3.5-0.8B"

pytestmark = pytest.mark.skipif(
    not (_OFFLOAD / "tokenizer_config.json").exists()
    and not (_INSTALLED / "tokenizer_config.json").exists(),
    reason="split Qwen3.5 tokenizer not installed",
)


@pytest.fixture(scope="module")
def tokenizer():
    from transformers import AutoTokenizer

    tok_dir = _OFFLOAD if (_OFFLOAD / "tokenizer_config.json").exists() else _INSTALLED
    return AutoTokenizer.from_pretrained(tok_dir, trust_remote_code=True, local_files_only=True)


def _stream_reconstruct(tokenizer, ids):
    """Decode ids one token at a time via _stream_delta and join the deltas."""
    emitted = ""
    joined = ""
    for i in range(1, len(ids) + 1):
        delta = _stream_delta(tokenizer, ids[:i], emitted)
        emitted += delta
        joined += delta
    return joined


def test_stream_delta_reconstruction_matches_full_decode(tokenizer):
    sentences = [
        "The quick brown fox jumps over the lazy dog. " * 5,
        "The patient was diagnosed with lung cancer.",
        "Merges: don't, won't, can't, I'm, we're. 1234567890",
    ]
    for sentence in sentences:
        ids = tokenizer.encode(sentence)
        assert _stream_reconstruct(tokenizer, ids) == tokenizer.decode(
            ids, skip_special_tokens=True
        )


def test_stream_delta_byte_fallback_style_edges(tokenizer):
    """Byte-fallback-style edge cases that stress the overlap matcher.

    Highly repetitive text can trick a longest-overlap matcher into over-
    reporting the overlap (matching more than the truly shared text), which
    would silently drop the newest token. Runs of identical words, punctuation
    and spaces are the classic triggers — SentencePiece tokenizers emit them
    as repeated pieces whose decoded text re-matches the emitted tail.
    """
    sentences = [
        "a  b   c    d     e      f",  # growing space runs
        "x" + " " * 12 + "y",  # long single space run
        ", , , , , , ,",  # punctuation run
        "??? ... !!! ... ???",  # mixed punctuation
        "word " * 12,  # repeated word run
        "the the the the the the the the the the",  # repeated word, no trailing space
    ]
    for sentence in sentences:
        ids = tokenizer.encode(sentence)
        assert _stream_reconstruct(tokenizer, ids) == tokenizer.decode(
            ids, skip_special_tokens=True
        ), f"sentence: {sentence!r}"
