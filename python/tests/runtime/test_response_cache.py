"""MT-3 v1: deterministic response cache tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.providers.base import (
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from agent_runtime_cockpit.runtime.response_cache import DeterministicResponseCache


def _request(temperature: float = 0.0, content: str = "hello") -> ProviderRequest:
    return ProviderRequest(
        model="claude-sonnet-4-5",
        messages=[ProviderMessage(role="user", content=content)],
        max_tokens=1024,
        temperature=temperature,
    )


def _response(content: str = "hi there") -> ProviderResponse:
    return ProviderResponse(
        call_id="c1",
        model="claude-sonnet-4-5",
        content=content,
        finish_reason="stop",
        usage=UsageRecord(input_tokens=100, output_tokens=50),
    )


# ── Default-off ───────────────────────────────────────────────────────────────


def test_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ARC_ENABLE_REPLAY_CACHE", raising=False)
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    cache.put(_request(), _response())
    assert cache.get(_request()) is None
    # Nothing written
    assert list(tmp_path.glob("*.json")) == []


def test_enabled_flag():
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"ARC_ENABLE_REPLAY_CACHE": "1"}):
        assert DeterministicResponseCache.enabled() is True
    with patch.dict(os.environ, {"ARC_ENABLE_REPLAY_CACHE": "0"}):
        assert DeterministicResponseCache.enabled() is False


# ── Round-trip when enabled + deterministic ──────────────────────────────────


def test_put_get_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    req = _request()
    cache.put(req, _response("cached answer"))
    hit = cache.get(req)
    assert hit is not None
    assert hit.content == "cached answer"


def test_cache_hit_zeroes_usage(tmp_path, monkeypatch):
    """A cache hit reports 0 tokens (no API call) + metadata cache_hit=True."""
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    req = _request()
    cache.put(req, _response())
    hit = cache.get(req)
    assert hit.usage.input_tokens == 0
    assert hit.usage.output_tokens == 0
    assert hit.metadata.get("cache_hit") is True


def test_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    assert cache.get(_request(content="never seen")) is None


# ── Temperature gating ────────────────────────────────────────────────────────


def test_non_deterministic_not_cached(tmp_path, monkeypatch):
    """temperature > 0 → no caching (would suppress intended variation)."""
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    req = _request(temperature=0.7)
    cache.put(req, _response())
    assert cache.get(req) is None
    assert list(tmp_path.glob("*.json")) == []


# ── Key sensitivity ───────────────────────────────────────────────────────────


def test_different_content_different_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    cache.put(_request(content="question A"), _response("answer A"))
    # Different prompt → cache miss
    assert cache.get(_request(content="question B")) is None
    # Same prompt → hit
    assert cache.get(_request(content="question A")).content == "answer A"


def test_different_model_different_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    req_a = _request()
    cache.put(req_a, _response("sonnet answer"))
    req_b = ProviderRequest(
        model="gpt-4o",
        messages=[ProviderMessage(role="user", content="hello")],
        max_tokens=1024,
        temperature=0.0,
    )
    assert cache.get(req_b) is None


# ── Never cache degraded/error responses ─────────────────────────────────────


def test_degraded_response_not_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    req = _request()
    degraded = ProviderResponse(
        call_id="c1",
        model="claude-sonnet-4-5",
        content="partial",
        finish_reason="error",
        usage=UsageRecord(available=False, input_tokens=0, output_tokens=0),
        degraded=True,
        degraded_reason="timeout",
    )
    cache.put(req, degraded)
    assert cache.get(req) is None


# ── Fail-open on corrupt cache file ──────────────────────────────────────────


def test_corrupt_cache_file_fails_open(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    cache = DeterministicResponseCache(cache_dir=tmp_path)
    req = _request()
    key = DeterministicResponseCache._key(req)
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{key}.json").write_text("{ corrupt json", encoding="utf-8")
    # Must not raise; returns None
    assert cache.get(req) is None


# ── Integration: TurnManager emits cache_hit and skips provider call ─────────


@pytest.mark.asyncio
async def test_turn_manager_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_REPLAY_CACHE", "1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    from agent_runtime_cockpit.cli_repl.cancellation import never_cancelled
    from agent_runtime_cockpit.cli_repl.session import ChatSession
    from agent_runtime_cockpit.runtime.turn_manager import TurnManager

    call_count = {"n": 0}

    class _CountingProvider:
        async def complete(self, request, *, cancellation_token):
            call_count["n"] += 1
            return ProviderResponse(
                call_id="c1",
                model="m",
                content="first answer",
                finish_reason="stop",
                usage=UsageRecord(input_tokens=10, output_tokens=5),
            )

        async def stream(self, request, *, cancellation_token):
            return
            yield

    events: list[str] = []
    mgr = TurnManager(
        _CountingProvider(),
        model="m",
        temperature=0.0,
        event_sink=lambda name, payload: events.append(name),
    )

    # First turn — provider called, response cached
    s1 = ChatSession()
    await mgr.run_turn(s1, "deterministic question", cancellation_token=never_cancelled())
    assert call_count["n"] == 1

    # Second identical turn in a fresh session — cache hit, no provider call
    s2 = ChatSession()
    await mgr.run_turn(s2, "deterministic question", cancellation_token=never_cancelled())
    assert call_count["n"] == 1  # NOT incremented
    assert "turn.cache_hit" in events
