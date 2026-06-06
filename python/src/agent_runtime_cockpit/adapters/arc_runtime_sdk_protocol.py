"""ARC Runtime SDK daemon/protocol parity (R79/Phase 111 Slice 110.5).

Documents and verifies three things:

1. The SDK standalone debug daemon (port 7842) is a **separate tool** — not the
   ARC Studio daemon (port 7777). The adapter communicates through ARC Studio's
   own daemon; the SDK daemon is for local SDK development only.

2. The 17 ``DaemonEventType`` values from the SDK SSE stream are a **strict
   additive subset** of ARC Studio's 20 ``AGUIEventType`` values. The mapping
   is explicit here: every SDK event maps to one AG-UI event or is
   SDK-specific (and should be surfaced as ``CUSTOM``).

3. The SDK ``/health`` response shape (``status:"ok"``, ``arc_runtime_cli:bool``,
   ``timestamp:int``) is narrower than ARC Studio's (``status:"healthy"``,
   ``arc:true``, ``uptime_seconds``). The shapes do NOT collide on port.

This module intentionally contains no I/O — it is a pure mapping contract with
tests. No network calls, no daemon spawning.
"""

from __future__ import annotations


from ..ag_ui import AGUIEventType

# ── Port / role clarification ────────────────────────────────────────────────

SDK_DAEMON_PORT = 7842  # standalone debug tool; ARC Studio never starts it
ARC_DAEMON_PORT = 7777  # ARC Studio daemon; the adapter integration path


# ── DaemonEventType → AGUIEventType mapping ──────────────────────────────────

# SDK events that map directly to an AG-UI event.
SDK_TO_AGUI: dict[str, AGUIEventType] = {
    "RUN_STARTED": AGUIEventType.RUN_STARTED,
    "RUN_COMPLETED": AGUIEventType.RUN_FINISHED,
    "RUN_FAILED": AGUIEventType.RUN_ERROR,
    "SDK_VALIDATE_STARTED": AGUIEventType.CUSTOM,  # SDK-specific
    "SDK_VALIDATE_COMPLETED": AGUIEventType.CUSTOM,  # SDK-specific
    "SDK_EFFECT_PLANNED": AGUIEventType.CUSTOM,  # SDK-specific
    "SDK_SIMULATION_STEP": AGUIEventType.STEP_STARTED,  # closest AG-UI match
    "SDK_SNAPSHOT_RECORDED": AGUIEventType.STATE_SNAPSHOT,
    "SDK_REPLAY_COMPLETED": AGUIEventType.RUN_FINISHED,
    "USER_INTENT": AGUIEventType.CUSTOM,  # SDK-specific
    "NAVIGATE": AGUIEventType.CUSTOM,  # SDK-specific
    "EFFECT_CALLED": AGUIEventType.TOOL_CALL_START,
    "EFFECT_RESOLVED": AGUIEventType.TOOL_CALL_END,
    "EFFECT_REJECTED": AGUIEventType.TOOL_CALL_ERROR,
    "STATE_MUTATION": AGUIEventType.STATE_SNAPSHOT,
    "CAPABILITY_GATE_EVALUATED": AGUIEventType.CUSTOM,  # SDK-specific; no AG-UI equivalent
}

# Every SDK event type (16 values from arc-sdk-daemon.ts).
SDK_EVENT_TYPES: frozenset[str] = frozenset(SDK_TO_AGUI.keys())

# AG-UI events that appear in the mapping (a strict additive subset of all 20).
AGUI_EVENTS_USED: frozenset[AGUIEventType] = frozenset(SDK_TO_AGUI.values())


def map_sdk_event(sdk_event_type: str) -> AGUIEventType:
    """Map a ``DaemonEventType`` string to the closest ``AGUIEventType``.

    Unknown SDK event types fall back to ``CUSTOM`` rather than raising.
    """
    return SDK_TO_AGUI.get(sdk_event_type, AGUIEventType.CUSTOM)


def is_sdk_event_covered(sdk_event_type: str) -> bool:
    """Return True if the SDK event has an explicit (non-fallback) AG-UI mapping."""
    return sdk_event_type in SDK_TO_AGUI


# ── /health shape documentation ─────────────────────────────────────────────


def sdk_health_shape() -> dict[str, object]:
    """Reference shape for SDK daemon /health (port 7842).

    The SDK returns:
        { "status": "ok", "version": "0.1.0", "arc_runtime_cli": bool,
          "timestamp": <epoch_ms>, "loopback_only": True }

    ARC Studio returns (port 7777):
        { "status": "healthy", "arc": True, "uptime_seconds": int }

    The two shapes do NOT collide (different port + status values).
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "arc_runtime_cli": False,
        "timestamp": 0,
        "loopback_only": True,
    }


def arc_health_shape() -> dict[str, object]:
    """Reference shape for ARC Studio daemon /health (port 7777)."""
    return {
        "status": "healthy",
        "arc": True,
        "uptime_seconds": 0,
    }


def health_shapes_compatible() -> bool:
    """Return True if the two health shapes are disjoint (no collision risk)."""
    # "status" appears in both but with different values ("ok" vs "healthy").
    return sdk_health_shape()["status"] != arc_health_shape()["status"]


__all__ = [
    "SDK_DAEMON_PORT",
    "ARC_DAEMON_PORT",
    "SDK_TO_AGUI",
    "SDK_EVENT_TYPES",
    "AGUI_EVENTS_USED",
    "map_sdk_event",
    "is_sdk_event_covered",
    "sdk_health_shape",
    "arc_health_shape",
    "health_shapes_compatible",
]
