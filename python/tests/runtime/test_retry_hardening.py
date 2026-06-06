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
