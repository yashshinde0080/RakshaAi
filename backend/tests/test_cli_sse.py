"""Runnable check for the CLI chat SSE parser (``_sse_delta``).

Feeds the shapes the API's ``stream_response`` emits (content deltas, reasoning
deltas for thinking models, empty deltas, ``[DONE]``) and asserts the parser
returns the right (content, reasoning) pair — the CLI chat loop in ``run``
depends on this to not leak tags or drop tokens.
"""
from app.cli.main import _sse_delta


def test_content_delta():
    assert _sse_delta('{"choices":[{"delta":{"content":"hi"}}]}') == ("hi", "")


def test_reasoning_delta():
    assert _sse_delta('{"choices":[{"delta":{"reasoning":"let me think"}}]}') == ("", "let me think")


def test_both_fields_returned():
    # loop picks content when both present (elif); parser must not lose reasoning
    assert _sse_delta('{"choices":[{"delta":{"content":"a","reasoning":"r"}}]}') == ("a", "r")


def test_empty_delta():
    assert _sse_delta('{"choices":[{"delta":{}}]}') == ("", "")
    assert _sse_delta('{"choices":[{"finish_reason":"stop"}]}') == ("", "")


def test_garbage_and_done():
    assert _sse_delta("[DONE]") == ("", "")
    assert _sse_delta("not json") == ("", "")
    assert _sse_delta("") == ("", "")
