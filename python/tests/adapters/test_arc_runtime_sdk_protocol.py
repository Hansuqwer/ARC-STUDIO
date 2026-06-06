"""Tests for SDK daemon/protocol parity (Slice 110.5)."""

from __future__ import annotations

from agent_runtime_cockpit.ag_ui import AGUIEventType
from agent_runtime_cockpit.adapters.arc_runtime_sdk_protocol import (
    ARC_DAEMON_PORT,
    AGUI_EVENTS_USED,
    SDK_DAEMON_PORT,
    SDK_EVENT_TYPES,
    SDK_TO_AGUI,
    arc_health_shape,
    health_shapes_compatible,
    is_sdk_event_covered,
    map_sdk_event,
    sdk_health_shape,
)


def test_ports_are_distinct():
    assert SDK_DAEMON_PORT == 7842
    assert ARC_DAEMON_PORT == 7777
    assert SDK_DAEMON_PORT != ARC_DAEMON_PORT


def test_all_sdk_events_in_mapping():
    """Every SDK DaemonEventType has an explicit entry."""
    sdk_from_ts = {
        "RUN_STARTED",
        "RUN_COMPLETED",
        "RUN_FAILED",
        "SDK_VALIDATE_STARTED",
        "SDK_VALIDATE_COMPLETED",
        "SDK_EFFECT_PLANNED",
        "SDK_SIMULATION_STEP",
        "SDK_SNAPSHOT_RECORDED",
        "SDK_REPLAY_COMPLETED",
        "USER_INTENT",
        "NAVIGATE",
        "EFFECT_CALLED",
        "EFFECT_RESOLVED",
        "EFFECT_REJECTED",
        "STATE_MUTATION",
        "CAPABILITY_GATE_EVALUATED",
    }
    assert sdk_from_ts == SDK_EVENT_TYPES


def test_mapping_values_are_agui_event_types():
    for sdk_ev, agui_ev in SDK_TO_AGUI.items():
        assert isinstance(agui_ev, AGUIEventType), f"{sdk_ev} mapped to non-AGUIEventType"


def test_agui_events_used_is_subset_of_all():
    assert AGUI_EVENTS_USED.issubset(set(AGUIEventType))


def test_run_events_map_correctly():
    assert map_sdk_event("RUN_STARTED") == AGUIEventType.RUN_STARTED
    assert map_sdk_event("RUN_COMPLETED") == AGUIEventType.RUN_FINISHED
    assert map_sdk_event("RUN_FAILED") == AGUIEventType.RUN_ERROR


def test_effect_events_map_to_tool_call():
    assert map_sdk_event("EFFECT_CALLED") == AGUIEventType.TOOL_CALL_START
    assert map_sdk_event("EFFECT_RESOLVED") == AGUIEventType.TOOL_CALL_END
    assert map_sdk_event("EFFECT_REJECTED") == AGUIEventType.TOOL_CALL_ERROR


def test_sdk_specific_events_map_to_custom():
    for ev in (
        "SDK_VALIDATE_STARTED",
        "SDK_VALIDATE_COMPLETED",
        "SDK_EFFECT_PLANNED",
        "USER_INTENT",
        "NAVIGATE",
        "CAPABILITY_GATE_EVALUATED",
    ):
        assert map_sdk_event(ev) == AGUIEventType.CUSTOM, f"{ev} should map to CUSTOM"


def test_unknown_event_falls_back_to_custom():
    assert map_sdk_event("TOTALLY_UNKNOWN") == AGUIEventType.CUSTOM
    assert not is_sdk_event_covered("TOTALLY_UNKNOWN")


def test_known_events_are_covered():
    for ev in SDK_EVENT_TYPES:
        assert is_sdk_event_covered(ev)


def test_health_shapes_no_status_collision():
    assert sdk_health_shape()["status"] == "ok"
    assert arc_health_shape()["status"] == "healthy"
    assert health_shapes_compatible() is True


def test_health_shapes_disjoint_keys_except_status():
    sdk_keys = set(sdk_health_shape()) - {"status"}
    arc_keys = set(arc_health_shape()) - {"status"}
    assert sdk_keys.isdisjoint(arc_keys), "Unexpected overlapping /health keys"
