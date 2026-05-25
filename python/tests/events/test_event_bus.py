"""Tests for the event bus (Phase 32 / R25, Slice 32.1)."""

from __future__ import annotations


import pytest

from agent_runtime_cockpit.events import EventBus, get_bus, reset_bus, set_bus
from agent_runtime_cockpit.events.types import (
    ArcEvent,
    AuditVerified,
    HitlDecided,
    HitlRequired,
    QuotaWarning,
    RunCompleted,
    RunFailed,
    parse_event,
)


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_bus()
    yield
    reset_bus()


def test_publish_and_subscribe():
    """Publish an event and verify subscriber receives it."""
    bus = EventBus()
    received: list[ArcEvent] = []

    def handler(event: ArcEvent) -> None:
        received.append(event)

    bus.subscribe("hitl_required", handler)
    event = HitlRequired(
        run_id="run-1",
        hitl_id="hitl-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    bus.publish(event)
    assert len(received) == 1
    assert received[0].event_type == "hitl_required"
    assert received[0].hitl_id == "hitl-1"


def test_typed_filtering():
    """Subscribers only receive events of their subscribed type."""
    bus = EventBus()
    received: list[ArcEvent] = []

    def handler(event: ArcEvent) -> None:
        received.append(event)

    bus.subscribe("run_completed", handler)
    bus.publish(HitlRequired(run_id="r1", hitl_id="h1", step_id="s1", prompt_text="?"))
    bus.publish(RunCompleted(run_id="r1", workflow_id="wf1", duration_ms=100))
    assert len(received) == 1
    assert received[0].event_type == "run_completed"


def test_untyped_catch_all():
    """Drain handlers receive all events."""
    bus = EventBus()
    received: list[ArcEvent] = []

    def handler(event: ArcEvent) -> None:
        received.append(event)

    bus.subscribe_all(handler)
    bus.publish(HitlRequired(run_id="r1", hitl_id="h1", step_id="s1", prompt_text="?"))
    bus.publish(RunCompleted(run_id="r1", workflow_id="wf1", duration_ms=100))
    assert len(received) == 2


def test_backpressure():
    """Bounded queue drops oldest events when full."""
    bus = EventBus(maxsize=3)
    queue = bus.stream(event_type="*")
    for i in range(10):
        bus.publish(HitlRequired(run_id=f"r{i}", hitl_id=f"h{i}", step_id="s1", prompt_text="?"))
    collected = []
    while not queue.empty():
        ev = queue.get_nowait()
        if ev is not None:
            collected.append(ev)
    # Queue should have at most 3 items (maxsize)
    assert len(collected) <= 3


def test_multiple_subscribers():
    """Multiple subscribers to the same event type all receive events."""
    bus = EventBus()
    received1: list[ArcEvent] = []
    received2: list[ArcEvent] = []

    def handler1(event: ArcEvent) -> None:
        received1.append(event)

    def handler2(event: ArcEvent) -> None:
        received2.append(event)

    bus.subscribe("hitl_required", handler1)
    bus.subscribe("hitl_required", handler2)
    bus.publish(HitlRequired(run_id="r1", hitl_id="h1", step_id="s1", prompt_text="?"))
    assert len(received1) == 1
    assert len(received2) == 1


def test_unsubscribing():
    """Unsubscribing a handler stops it from receiving events."""
    bus = EventBus()
    received: list[ArcEvent] = []

    def handler(event: ArcEvent) -> None:
        received.append(event)

    bus.subscribe("hitl_required", handler)
    bus.publish(HitlRequired(run_id="r1", hitl_id="h1", step_id="s1", prompt_text="?"))
    assert len(received) == 1

    bus.unsubscribe("hitl_required", handler)
    bus.publish(HitlRequired(run_id="r2", hitl_id="h2", step_id="s1", prompt_text="?"))
    assert len(received) == 1  # No new events


def test_cross_type_isolation():
    """Events of different types don't leak across subscribers."""
    bus = EventBus()
    hitl_received: list[ArcEvent] = []
    audit_received: list[ArcEvent] = []

    def hitl_handler(event: ArcEvent) -> None:
        hitl_received.append(event)

    def audit_handler(event: ArcEvent) -> None:
        audit_received.append(event)

    bus.subscribe("hitl_required", hitl_handler)
    bus.subscribe("audit_verified", audit_handler)

    bus.publish(HitlRequired(run_id="r1", hitl_id="h1", step_id="s1", prompt_text="?"))
    bus.publish(AuditVerified(ok=True, mode="hmac", records_checked=5, reason="ok", duration_ms=10))

    assert len(hitl_received) == 1
    assert len(audit_received) == 1


def test_parse_event_all_types():
    """parse_event correctly dispatches to all known event types."""
    cases = [
        (
            {
                "event_type": "hitl_required",
                "run_id": "r1",
                "hitl_id": "h1",
                "step_id": "s1",
                "prompt_text": "?",
            },
            HitlRequired,
        ),
        (
            {"event_type": "hitl_decided", "run_id": "r1", "hitl_id": "h1", "decision": "approve"},
            HitlDecided,
        ),
        (
            {
                "event_type": "audit_verified",
                "ok": True,
                "mode": "hmac",
                "records_checked": 0,
                "reason": "",
                "duration_ms": 0,
            },
            AuditVerified,
        ),
        ({"event_type": "run_completed", "run_id": "r1", "workflow_id": "wf1"}, RunCompleted),
        (
            {"event_type": "run_failed", "run_id": "r1", "workflow_id": "wf1", "error": "x"},
            RunFailed,
        ),
        (
            {
                "event_type": "quota_warning",
                "dimension": "tokens",
                "usage_pct": 85.0,
                "limit": 1000,
                "current": 850,
            },
            QuotaWarning,
        ),
    ]
    for payload, expected_cls in cases:
        event = parse_event(payload)
        assert isinstance(event, expected_cls), (
            f"Expected {expected_cls.__name__}, got {type(event).__name__} for {payload['event_type']}"
        )


def test_get_bus_singleton():
    """get_bus() returns the same instance."""
    bus1 = get_bus()
    bus2 = get_bus()
    assert bus1 is bus2


def test_reset_bus():
    """reset_bus() creates a new singleton on next get_bus()."""
    bus1 = get_bus()
    reset_bus()
    bus2 = get_bus()
    assert bus1 is not bus2


def test_set_bus():
    """set_bus() overrides the singleton."""
    custom = EventBus()
    result = set_bus(custom)
    assert result is custom
    assert get_bus() is custom


def test_run_completed_shape():
    """RunCompleted event has expected shape and defaults."""
    event = RunCompleted(run_id="r1", workflow_id="wf1", duration_ms=500)
    assert event.event_type == "run_completed"
    assert event.run_id == "r1"
    assert event.workflow_id == "wf1"
    assert event.duration_ms == 500
    assert event.status == "completed"


def test_run_failed_shape():
    """RunFailed event has expected shape."""
    event = RunFailed(
        run_id="r1",
        workflow_id="wf1",
        duration_ms=200,
        error="timeout",
        error_detail="TimeoutError",
    )
    assert event.event_type == "run_failed"
    assert event.error == "timeout"
    assert event.error_detail == "TimeoutError"


def test_quota_warning_shape():
    """QuotaWarning event has expected shape."""
    event = QuotaWarning(dimension="tokens", usage_pct=90.5, limit=1000, current=905)
    assert event.event_type == "quota_warning"
    assert event.dimension == "tokens"
    assert event.usage_pct == 90.5
