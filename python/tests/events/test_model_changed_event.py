"""Tests for ModelChanged typed event (v0.6 Task 5)."""

from __future__ import annotations

from agent_runtime_cockpit.events.types import ModelChanged
from agent_runtime_cockpit.protocol.typed_events import parse_typed_event


def _raw(previous="gpt-4o", current="kimi-k2.6", added=None, removed=None):
    return {
        "schema_version": 2,
        "type": "MODEL_CHANGED",
        "timestamp": "2026-06-05T00:00:00Z",
        "run_id": "r-abc",
        "sequence": 1,
        "data": {
            "previous_model": previous,
            "current_model": current,
            "capabilities_added": added or [],
            "capabilities_removed": removed or [],
        },
    }


def test_model_changed_round_trip():
    event = parse_typed_event(_raw())
    assert event.type == "MODEL_CHANGED"
    assert event.data.previous_model == "gpt-4o"
    assert event.data.current_model == "kimi-k2.6"


def test_capabilities_added_reflects_diff():
    """capabilities_added should list features in new but not old model."""
    event = parse_typed_event(_raw(added=["vision"], removed=[]))
    assert "vision" in event.data.capabilities_added
    assert event.data.capabilities_removed == []


def test_capabilities_removed():
    event = parse_typed_event(_raw(added=[], removed=["tools"]))
    assert "tools" in event.data.capabilities_removed


def test_extra_fields_ignored_forward_compat():
    """extra='ignore' forward-compat: unknown fields in data must not raise."""
    raw = _raw()
    raw["data"]["future_field_v99"] = "should be ignored"
    event = parse_typed_event(raw)
    assert event.type == "MODEL_CHANGED"


def test_bus_event_emittable():
    from agent_runtime_cockpit.events import get_bus, reset_bus

    reset_bus()
    received = []
    get_bus().subscribe("model_changed", received.append)

    get_bus().publish(
        ModelChanged(
            previous_model="gpt-4o",
            current_model="kimi-k2.6",
            capabilities_added=["vision"],
            capabilities_removed=[],
        )
    )
    assert len(received) == 1
    assert received[0].current_model == "kimi-k2.6"
    assert "vision" in received[0].capabilities_added
