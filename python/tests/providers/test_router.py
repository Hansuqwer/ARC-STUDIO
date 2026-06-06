"""Tests for ProviderRouter multi-provider failover."""

import pytest

from agent_runtime_cockpit.providers.base import RateLimitError, AuthError
from agent_runtime_cockpit.providers.router import ProviderRouter


async def _ok(value):
    async def fn():
        return value

    return fn


async def _fail(exc):
    async def fn():
        raise exc

    return fn


@pytest.mark.asyncio
async def test_router_returns_first_provider_result():
    router = ProviderRouter([await _ok("first"), await _ok("second")])
    result = await router.call()
    assert result == "first"


@pytest.mark.asyncio
async def test_router_failover_on_retryable_error():
    router = ProviderRouter([await _fail(RateLimitError("rate")), await _ok("fallback")])
    result = await router.call()
    assert result == "fallback"


@pytest.mark.asyncio
async def test_router_does_not_failover_on_non_retryable():
    router = ProviderRouter([await _fail(AuthError("auth")), await _ok("second")])
    with pytest.raises(AuthError):
        await router.call()


@pytest.mark.asyncio
async def test_router_raises_when_all_fail():
    router = ProviderRouter(
        [
            await _fail(RateLimitError("r1")),
            await _fail(RateLimitError("r2")),
        ]
    )
    with pytest.raises(RateLimitError):
        await router.call()


@pytest.mark.asyncio
async def test_router_single_provider():
    router = ProviderRouter([await _ok("only")])
    assert await router.call() == "only"
