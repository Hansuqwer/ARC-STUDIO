"""Tests for _call_with_retry in turn_manager — provider error retry hardening."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent_runtime_cockpit.providers.base import (
    AuthError,
    NetworkError,
    ProviderError,
    RateLimitError,
)
from agent_runtime_cockpit.runtime.turn_manager import _call_with_retry


@pytest.fixture(autouse=True)
def _disable_sleep(monkeypatch):
    """Skip real sleep in all tests."""
    monkeypatch.setenv("ARC_DISABLE_RETRY_SLEEP", "1")


@pytest.mark.asyncio
async def test_success_on_first_call():
    fn = AsyncMock(return_value="ok")
    result = await _call_with_retry(fn)
    assert result == "ok"
    assert fn.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_rate_limit_then_succeeds():
    fn = AsyncMock(side_effect=[RateLimitError("429"), "ok"])
    result = await _call_with_retry(fn, max_retries=2)
    assert result == "ok"
    assert fn.call_count == 2


@pytest.mark.asyncio
async def test_retries_on_network_error_then_succeeds():
    fn = AsyncMock(side_effect=[NetworkError("timeout"), NetworkError("timeout"), "ok"])
    result = await _call_with_retry(fn, max_retries=2)
    assert result == "ok"
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_retries_exhausted():
    fn = AsyncMock(side_effect=RateLimitError("always rate limited"))
    with pytest.raises(RateLimitError):
        await _call_with_retry(fn, max_retries=2)
    assert fn.call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_non_retryable_propagates_immediately():
    fn = AsyncMock(side_effect=[AuthError("bad key"), "should not reach"])
    with pytest.raises(AuthError):
        await _call_with_retry(fn, max_retries=2)
    assert fn.call_count == 1  # no retry on auth error


@pytest.mark.asyncio
async def test_non_retryable_provider_error_not_retried():
    """ProviderError with retryable=False is never retried."""
    fn = AsyncMock(side_effect=ProviderError("validation failed", retryable=False))
    with pytest.raises(ProviderError):
        await _call_with_retry(fn, max_retries=2)
    assert fn.call_count == 1


@pytest.mark.asyncio
async def test_max_retries_zero_never_retries():
    fn = AsyncMock(side_effect=[RateLimitError("429"), "ok"])
    with pytest.raises(RateLimitError):
        await _call_with_retry(fn, max_retries=0)
    assert fn.call_count == 1


@pytest.mark.asyncio
async def test_non_provider_exception_propagates_immediately():
    """Non-ProviderError exceptions (e.g. CancelledError from cancellation) pass through."""
    fn = AsyncMock(side_effect=ValueError("unexpected"))
    with pytest.raises(ValueError):
        await _call_with_retry(fn, max_retries=2)
    assert fn.call_count == 1


# ─── _stream_with_retry (R-OPEN-HARDEN slice 2) ───────────────────────────────


async def _make_stream(chunks):
    """An async generator that yields the given chunks."""
    for c in chunks:
        yield c


async def _failing_before_first(exc):
    """An async generator that raises before yielding anything."""
    raise exc
    yield  # pragma: no cover — unreachable, makes this an async generator


async def _failing_after_first(chunks, exc):
    """An async generator that yields some chunks then raises."""
    for c in chunks:
        yield c
    raise exc


@pytest.mark.asyncio
async def test_stream_success_no_retry():
    from agent_runtime_cockpit.runtime.turn_manager import _stream_with_retry

    out = [c async for c in _stream_with_retry(lambda: _make_stream(["a", "b", "c"]))]
    assert out == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_stream_retries_before_first_chunk():
    """A retryable error before the first chunk triggers a retry."""
    from agent_runtime_cockpit.runtime.turn_manager import _stream_with_retry

    attempts = {"n": 0}

    def factory():
        attempts["n"] += 1
        if attempts["n"] == 1:
            return _failing_before_first(RateLimitError("429"))
        return _make_stream(["ok"])

    out = [c async for c in _stream_with_retry(factory, max_retries=2)]
    assert out == ["ok"]
    assert attempts["n"] == 2


@pytest.mark.asyncio
async def test_stream_does_not_retry_after_first_chunk():
    """Once a chunk is emitted, a failure propagates — no duplicate output."""
    from agent_runtime_cockpit.runtime.turn_manager import _stream_with_retry

    attempts = {"n": 0}

    def factory():
        attempts["n"] += 1
        return _failing_after_first(["partial"], RateLimitError("429 mid-stream"))

    collected = []
    with pytest.raises(RateLimitError):
        async for c in _stream_with_retry(factory, max_retries=2):
            collected.append(c)
    # The one chunk emitted before the error is kept; no retry/duplication.
    assert collected == ["partial"]
    assert attempts["n"] == 1


@pytest.mark.asyncio
async def test_stream_non_retryable_propagates_before_first_chunk():
    from agent_runtime_cockpit.runtime.turn_manager import _stream_with_retry

    attempts = {"n": 0}

    def factory():
        attempts["n"] += 1
        return _failing_before_first(AuthError("bad key"))

    with pytest.raises(AuthError):
        async for _ in _stream_with_retry(factory, max_retries=2):
            pass
    assert attempts["n"] == 1  # auth error not retried


@pytest.mark.asyncio
async def test_stream_raises_after_max_retries():
    from agent_runtime_cockpit.runtime.turn_manager import _stream_with_retry

    attempts = {"n": 0}

    def factory():
        attempts["n"] += 1
        return _failing_before_first(RateLimitError("always"))

    with pytest.raises(RateLimitError):
        async for _ in _stream_with_retry(factory, max_retries=2):
            pass
    assert attempts["n"] == 3  # initial + 2 retries
