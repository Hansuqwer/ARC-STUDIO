"""
AG-UI Event Bridge

Maps ARC internal run events to AG-UI protocol-compatible event types.
Source: https://docs.ag-ui.com/concepts/events

AG-UI event types used:
  RUN_STARTED   → RunStarted
  RUN_COMPLETED → RunFinished
  NODE_STARTED  → StepStarted
  NODE_COMPLETED→ StepFinished
  MESSAGE       → TextMessageStart / TextMessageContent / TextMessageEnd
  TOOL_CALL     → ToolCallStart / ToolCallArgs / ToolCallEnd
  STATE_SNAPSHOT→ StateSnapshot (ARC extension)
"""
from __future__ import annotations

from typing import Any
from ..protocol.schemas import RunEvent

# ARC event type → AG-UI event type mapping
ARC_TO_AGUI: dict[str, str] = {
    "RUN_STARTED":    "RunStarted",
    "RUN_COMPLETED":  "RunFinished",
    "RUN_FAILED":     "RunError",
    "NODE_STARTED":   "StepStarted",
    "NODE_COMPLETED": "StepFinished",
    "NODE_FAILED":    "StepError",
    "MESSAGE":        "TextMessageStart",
    "TOOL_CALL":      "ToolCallStart",
    "STATE_SNAPSHOT": "StateSnapshot",
}


def to_agui(event: RunEvent) -> dict[str, Any]:
    """Convert an ARC RunEvent to an AG-UI-compatible event dict."""
    agui_type = ARC_TO_AGUI.get(event.type, event.type)
    return {
        "type": agui_type,
        "timestamp": event.timestamp,
        "runId": event.run_id,
        "sequence": event.sequence,
        **event.data,
        # Preserve ARC-specific type for debugging
        "_arc_type": event.type,
    }


def from_agui(agui_event: dict[str, Any]) -> RunEvent:
    """Convert an incoming AG-UI event to an ARC RunEvent."""
    arc_type = agui_event.get("_arc_type", agui_event.get("type", "UNKNOWN"))
    return RunEvent(
        type=arc_type,
        timestamp=agui_event.get("timestamp", ""),
        run_id=agui_event.get("runId", ""),
        sequence=agui_event.get("sequence", 0),
        data={k: v for k, v in agui_event.items()
              if k not in ("type", "timestamp", "runId", "sequence", "_arc_type")},
    )
