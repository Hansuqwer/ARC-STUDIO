"""Tests: hook_event_broker_publish wires EventBroker → GlobalEventBroker (Phase 276)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.stream.websocket import (
    GlobalEventBroker,
    hook_event_broker_publish,
    reset_global_broker,
    get_global_broker,
)

pytestmark = pytest.mark.asyncio


class _FakeBroker:
    """Minimal stand-in for EventBroker.publish interface."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def publish(self, run_id: str, event: dict) -> int:
        self.calls.append((run_id, event))
        return len(self.calls)


def _setup() -> tuple[_FakeBroker, GlobalEventBroker]:
    reset_global_broker()
    fake = _FakeBroker()
    hook_event_broker_publish(fake)
    return fake, get_global_broker()


async def test_hook_forwards_run_started():
    fake, global_broker = _setup()
    q = global_broker.subscribe()
    fake.publish("r1", {"type": "RUN_STARTED", "timestamp": 1.0})
    event = q.get_nowait()
    assert event["type"] == "RUN_STARTED"
    assert event["run_id"] == "r1"
    reset_global_broker()


async def test_hook_forwards_run_completed():
    fake, global_broker = _setup()
    q = global_broker.subscribe()
    fake.publish("r2", {"type": "RUN_COMPLETED"})
    event = q.get_nowait()
    assert event["type"] == "RUN_COMPLETED"
    reset_global_broker()


async def test_hook_forwards_hitl_prompt():
    fake, global_broker = _setup()
    q = global_broker.subscribe()
    fake.publish("r3", {"type": "HITL_PROMPT"})
    event = q.get_nowait()
    assert event["type"] == "HITL_PROMPT"
    reset_global_broker()


async def test_hook_does_not_forward_non_terminal_events():
    fake, global_broker = _setup()
    q = global_broker.subscribe()
    fake.publish("r4", {"type": "TOOL_CALL"})
    assert q.empty()
    reset_global_broker()


async def test_hook_preserves_original_publish_return():
    fake, _ = _setup()
    result = fake.publish("r5", {"type": "RUN_STARTED"})
    assert result == 1  # original incremented .calls counter
    reset_global_broker()


async def test_hook_forwarded_event_has_timestamp():
    fake, global_broker = _setup()
    q = global_broker.subscribe()
    fake.publish("r6", {"type": "RUN_FAILED", "timestamp": 999.0})
    event = q.get_nowait()
    assert event["timestamp"] == 999.0
    reset_global_broker()
