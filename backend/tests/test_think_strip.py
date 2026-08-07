"""Regression tests for the chat API think-block stripping and reasoning deltas.

Pins the behavior of ``_split_think`` / ``_trim_tag_prefix`` /
``_prompt_opens_think`` against Qwen3.5's reasoning output: full
``<think>...</think>`` blocks, unclosed blocks, the thinking-mode template
(which leaves an unclosed opener in the prompt so the completion holds only a
bare close), and the streaming prefix-stability property (a tag split across
token boundaries must never leak and never desync the emitted deltas). Also
verifies ``enable_thinking`` toggles the template's reasoning mode.
"""
from pathlib import Path

import pytest

from app.api.chat import (
    _split_think,
    _trim_tag_prefix,
    _prompt_opens_think,
    _OPEN_TAG,
)

_ROOT = Path(__file__).resolve().parents[2]
_INSTALLED = _ROOT / "workspace" / "models" / "installed" / "Qwen-Qwen3.5-0.8B"


# --- _split_think: raw slices, prefix-stable ---

def test_plain_text_passes_through():
    assert _split_think("no tags here") == ("no tags here", None)


def test_full_block_splits_content_and_reasoning():
    content, reasoning = _split_think("<think>let me reason</think>\n\nAnswer here.\n")
    assert content == "\n\nAnswer here.\n"
    assert reasoning == "let me reason"


def test_content_before_opener_is_kept():
    content, reasoning = _split_think("pre <think>r</think> post")
    assert content == "pre  post"
    assert reasoning == "r"


def test_unclosed_block_clean_content_reasoning_exposed():
    content, reasoning = _split_think("A<think>unclosed reasoning")
    assert content == "A"
    assert reasoning == "unclosed reasoning"


def test_empty_block_joins_content():
    content, reasoning = _split_think("A<think></think>B")
    assert content == "AB"
    assert reasoning is None


def test_seeded_thinking_mode_bare_close():
    # Callers prepend the opener when the chat template left it in the prompt
    content, reasoning = _split_think("<think>reasoning here\n</think>\n\nAnswer")
    assert content == "\n\nAnswer"
    assert reasoning == "reasoning here\n"


def test_stray_close_without_opener_keeps_text_in_content():
    # A bare close in non-thinking mode is not a reasoning marker: the tag is
    # dropped but surrounding text stays content (reclassifying it would
    # desync streamed output).
    content, reasoning = _split_think("A</think>B")
    assert content == "AB"
    assert reasoning is None


def test_multiple_blocks_all_stripped():
    content, reasoning = _split_think("<think>1</think>A<think>2</think>B")
    assert content == "AB"
    assert reasoning == "12"


# --- _prompt_opens_think ---

def test_prompt_opens_think_detection():
    assert _prompt_opens_think("...assistant\n<think>\n") is True      # thinking mode
    assert _prompt_opens_think("...assistant\n<think>\n\n</think>\n\n") is False  # closed empty
    assert _prompt_opens_think("plain prompt") is False


# --- _trim_tag_prefix ---

def test_trim_tag_prefix():
    assert _trim_tag_prefix("hello") == "hello"
    assert _trim_tag_prefix("5 ") == "5 "
    assert _trim_tag_prefix("A<thi") == "A", "partial opener must be held back"
    assert _trim_tag_prefix("A</") == "A", "partial close must be held back"
    assert _trim_tag_prefix("<") == ""
    assert _trim_tag_prefix("<think") == ""
    assert _trim_tag_prefix("x<") == "x"


# --- streaming: prefix-stable deltas (mirrors stream_response) ---

def _sim_stream(tokens, prompt_opens_think=False):
    """Feed tokens like stream_response; return (emitted_content, emitted_reasoning)."""
    full_text = _OPEN_TAG if prompt_opens_think else ""
    sent = 0
    rsent = 0
    out_c, out_r = [], []
    for tok in tokens:
        full_text += tok
        content, reasoning = _split_think(full_text)
        content = _trim_tag_prefix(content)
        reasoning = _trim_tag_prefix(reasoning or "")
        if len(content) > sent:
            out_c.append(content[sent:])
            sent = len(content)
        if len(reasoning) > rsent:
            out_r.append(reasoning[rsent:])
            rsent = len(reasoning)
    return "".join(out_c), "".join(out_r)


def test_stream_strips_full_block():
    tokens = ["<think>", "let me think", "</think>", " The", " ans", "wer."]
    content, reasoning = _sim_stream(tokens)
    assert content == " The answer."
    assert reasoning == "let me think"


def test_stream_handles_tag_split_across_tokens():
    tokens = ["hi", "<thi", "nk>", "secret", "</thi", "nk>", " D", "one!"]
    content, reasoning = _sim_stream(tokens)
    assert content == "hi Done!"
    assert reasoning == "secret"


def test_stream_no_think_is_normal_streaming():
    content, reasoning = _sim_stream(["Hel", "lo ", "world"])
    assert content == "Hello world"
    assert reasoning == ""


def test_stream_plain_less_than_not_mistaken_for_tag():
    content, reasoning = _sim_stream(["5 ", "<", " 3", " is", " 8"])
    assert content == "5 < 3 is 8"
    assert reasoning == ""


def test_stream_reasoning_plain_less_than_kept():
    # A literal "<" inside reasoning must resolve as text, not be lost
    tokens = ["<think>", "x = 5 ", "<", " 10", "</think>", " OK"]
    content, reasoning = _sim_stream(tokens)
    assert content == " OK"
    assert reasoning == "x = 5 < 10"


def test_stream_multiple_blocks():
    tokens = ["A", "<think>", "1", "</think>", "B", "<think>", "2", "</think>", "C"]
    content, reasoning = _sim_stream(tokens)
    assert content == "ABC"
    assert reasoning == "12"


def test_stream_unclosed_block_reasoning_still_emitted():
    # Reasoning streams live even if the block never closes
    content, reasoning = _sim_stream(["Q:", " <think>", "reasoning", " never", " closed"])
    assert content == "Q: "
    assert reasoning == "reasoning never closed"


def test_stream_thinking_mode_holds_reasoning():
    # prompt template opened <think>; completion = reasoning + bare close
    tokens = ["reas", "oning\n", "</think>", "\n\nA", "nswer"]
    content, reasoning = _sim_stream(tokens, prompt_opens_think=True)
    assert content == "\n\nAnswer"
    assert reasoning == "reasoning\n"


def test_stream_stray_close_does_not_lose_content():
    # Reviewer-found desync regression: a bare close after emitted content must
    # not reclassify it or drop the tokens that follow.
    content, reasoning = _sim_stream(["A", "</", "think>", "B"])
    assert content == "AB"
    assert reasoning == ""


# --- enable_thinking toggles the Qwen3.5 template (needs the model on disk) ---

def test_enable_thinking_toggles_prompt_template():
    if not (_INSTALLED / "tokenizer_config.json").exists():
        pytest.skip("Qwen3.5 model not installed")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        _INSTALLED, trust_remote_code=True, local_files_only=True
    )
    messages = [{"role": "user", "content": "hi"}]
    on = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=True
    )
    off = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    assert _prompt_opens_think(on) is True
    assert _prompt_opens_think(off) is False
