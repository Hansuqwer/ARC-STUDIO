"""R-AUDIT25: ProviderRouter wired into the run path (opt-in cascading failover)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.providers import router as router_mod
from agent_runtime_cockpit.providers.base import ProviderError


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text


class _FailingClient:
    async def complete(self, request, *, cancellation_token=None):
        raise ProviderError("rate limited", retryable=True)


class _OkClient:
    def __init__(self, text: str) -> None:
        self._text = text

    async def complete(self, request, *, cancellation_token=None):
        return _Resp(self._text)


def _make_tm(primary, fallbacks):
    from agent_runtime_cockpit.runtime.turn_manager import TurnManager

    return TurnManager(primary, model="m", fallback_clients=fallbacks)


@pytest.mark.asyncio
async def test_failover_routes_to_fallback_when_enabled(monkeypatch):
    monkeypatch.setattr(router_mod, "ENABLED", True)
    tm = _make_tm(_FailingClient(), [_OkClient("from-fallback")])
    resp = await tm._complete_with_failover(object(), cancellation_token=None)
    assert resp.text == "from-fallback"


@pytest.mark.asyncio
async def test_default_off_does_not_failover(monkeypatch):
    monkeypatch.setattr(router_mod, "ENABLED", False)
    monkeypatch.setenv("ARC_DISABLE_RETRY_SLEEP", "1")
    tm = _make_tm(_FailingClient(), [_OkClient("from-fallback")])
    # Router disabled -> primary path (with retry) propagates the primary's error, no failover.
    with pytest.raises(ProviderError):
        await tm._complete_with_failover(object(), cancellation_token=None)
