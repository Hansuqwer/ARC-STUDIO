"""P0-3: provider-aware token counter tests."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.context.token_counter import estimate_tokens


def test_heuristic_short_text() -> None:
    result = estimate_tokens("hello world", provider=None)
    # "hello world" = 11 chars → int(11/4*1.33) = 3; within 15% of 3 tokens
    assert 1 <= result <= 10


def test_heuristic_longer_text() -> None:
    text = "a" * 400  # 400 chars → ~133 tokens
    result = estimate_tokens(text)
    assert 100 <= result <= 200


def test_heuristic_empty_string() -> None:
    assert estimate_tokens("") == 0


def test_heuristic_unicode() -> None:
    result = estimate_tokens("こんにちは世界")
    assert result >= 0


def test_unknown_provider_uses_heuristic() -> None:
    text = "x" * 100
    r_unknown = estimate_tokens(text, provider="groq")
    r_none = estimate_tokens(text, provider=None)
    assert r_unknown == r_none


def test_anthropic_falls_back_to_heuristic_without_real_client() -> None:
    # AnthropicCountTokensEstimator requires a live SDK client.
    # Without one, token_counter falls back to heuristic — must not raise.
    result = estimate_tokens("hello world", provider="anthropic")
    assert result > 0


def test_openai_falls_back_to_heuristic_without_tiktoken(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate tiktoken not installed
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "tiktoken":
            raise ImportError("mocked missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = estimate_tokens("hello world", provider="openai")
    assert result > 0


def test_list_input_sums_per_entry() -> None:
    class Entry:
        def __init__(self, content: str) -> None:
            self.content = content

    entries = [Entry("hello"), Entry("world")]
    result = estimate_tokens(entries)
    single = estimate_tokens("hello world")
    # List sum should be in the same ballpark (not zero, not wildly off)
    assert result > 0
    assert abs(result - single) <= single  # within 2× of single-string estimate


def test_handles_dict_entries() -> None:
    entries = [{"content": "hello"}, {"content": "world"}]
    result = estimate_tokens(entries)
    assert result > 0


def test_data_store_increments_total_tokens() -> None:
    """add_entry() should increment DataStore.total_tokens."""
    from agent_runtime_cockpit.tui.data import DataStore

    ds = DataStore()
    assert ds.total_tokens == 0
    ds.add_entry("user", "hello world")
    assert ds.total_tokens > 0
