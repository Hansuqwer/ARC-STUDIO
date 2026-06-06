"""Tests for TurnManager hitl_gate_fn hook (Phase 131)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import never_cancelled
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import ProviderResponse, UsageRecord
from agent_runtime_cockpit.providers.base import ProviderError
from agent_runtime_cockpit.runtime.turn_manager import TurnManager


class _Provider:
    def __init__(self) -> None:
        self.called = False

    async def complete(self, request, *, cancellation_token):
        self.called = True
        return ProviderResponse(
            call_id="c1",
            model="m",
            content="ok",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=1, output_tokens=1),
        )

    async def stream(self, request, *, cancellation_token):
        self.called = True
        yield  # pragma: no cover

    async def cancel(self, call_id: str) -> None:
        return None


def _session() -> ChatSession:
    return ChatSession()


@pytest.mark.asyncio
async def test_gate_allow_proceeds() -> None:
    """hitl_gate_fn returning 'allow' must not block the turn."""
    provider = _Provider()
    manager = TurnManager(
        provider,
        model="m",
        hitl_gate_fn=lambda req: "allow",
    )
    result = await manager.run_turn(_session(), "hello", cancellation_token=never_cancelled())
    assert not result.degraded
    assert provider.called


@pytest.mark.asyncio
async def test_gate_deny_raises_provider_error() -> None:
    """hitl_gate_fn returning 'deny' must raise ProviderError(retryable=False)."""
    provider = _Provider()
    events: list[str] = []
    manager = TurnManager(
        provider,
        model="m",
        event_sink=lambda name, _: events.append(name),
        hitl_gate_fn=lambda req: "deny",
    )
    with pytest.raises(ProviderError) as exc_info:
        await manager.run_turn(_session(), "hello", cancellation_token=never_cancelled())
    assert not exc_info.value.retryable
    assert "turn.denied" in events
    assert not provider.called


@pytest.mark.asyncio
async def test_no_gate_fn_no_change() -> None:
    """hitl_gate_fn=None must leave behaviour unchanged."""
    provider = _Provider()
    manager = TurnManager(provider, model="m", hitl_gate_fn=None)
    result = await manager.run_turn(_session(), "hi", cancellation_token=never_cancelled())
    assert not result.degraded
    assert provider.called
