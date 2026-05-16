"""
Event registry — versioned event type definitions and validation (ADR-004).

Provides:
- ``EventTypeDef`` — schema definition for a single event type
- ``EVENT_TYPES`` — canonical registry of all known event types
- ``create_event()`` — validated event factory
- ``validate_event_data()`` — standalone field checker
- ``CURRENT_SCHEMA_VERSION`` — global schema version constant
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .schemas import RunEvent

# The current event schema version. Increment on breaking changes.
# Readers must support N and N-1.
CURRENT_SCHEMA_VERSION = 1


class EventTypeDef(BaseModel):
    """Schema definition for one event type."""
    version: int = CURRENT_SCHEMA_VERSION
    required_fields: set[str] = Field(default_factory=set)
    optional_fields: set[str] = Field(default_factory=set)


# ---------------------------------------------------------------------------
# Canonical event type registry
# ---------------------------------------------------------------------------

EVENT_TYPES: dict[str, EventTypeDef] = {
    # ── Run lifecycle ────────────────────────────────────────────────────
    "RUN_STARTED": EventTypeDef(
        required_fields={"workflow_id", "runtime"},
        optional_fields={"profile_id", "isolation"},
    ),
    "RUN_COMPLETED": EventTypeDef(
        required_fields={"duration_ms"},
        optional_fields={"output", "evidence_refs"},
    ),
    "RUN_FAILED": EventTypeDef(
        required_fields={"error"},
        optional_fields={"error_detail", "error_type"},
    ),
    "RUN_CANCELLED": EventTypeDef(
        required_fields={"cancel_reason"},
        optional_fields=set(),
    ),

    # ── Step lifecycle ───────────────────────────────────────────────────
    "STEP_STARTED": EventTypeDef(
        required_fields={"step_id", "step_name"},
        optional_fields={"step_type"},
    ),
    "STEP_COMPLETED": EventTypeDef(
        required_fields={"step_id"},
        optional_fields={"output", "duration_ms"},
    ),
    "STEP_FAILED": EventTypeDef(
        required_fields={"step_id", "error"},
        optional_fields=set(),
    ),

    # ── Agent lifecycle ──────────────────────────────────────────────────
    "AGENT_START": EventTypeDef(
        required_fields={"agent_name"},
        optional_fields={"instructions"},
    ),
    "AGENT_END": EventTypeDef(
        required_fields={"agent_name", "output"},
        optional_fields={"usage"},
    ),

    # ── Tool calls ───────────────────────────────────────────────────────
    "TOOL_CALL": EventTypeDef(
        required_fields={"tool_call_id", "tool_name"},
        optional_fields=set(),
    ),
    "TOOL_CALL_START": EventTypeDef(
        required_fields={"tool_call_id", "tool_name"},
        optional_fields=set(),
    ),
    "TOOL_CALL_ARGS": EventTypeDef(
        required_fields={"tool_call_id", "delta"},
        optional_fields=set(),
    ),
    "TOOL_CALL_END": EventTypeDef(
        required_fields={"tool_call_id"},
        optional_fields=set(),
    ),
    "TOOL_CALL_RESULT": EventTypeDef(
        required_fields={"tool_call_id", "result"},
        optional_fields={"evidence_refs"},
    ),
    "TOOL_CALL_ERROR": EventTypeDef(
        required_fields={"tool_call_id", "error"},
        optional_fields={"evidence_refs"},
    ),
    "TOOL_END": EventTypeDef(
        required_fields={"tool_name", "result"},
        optional_fields=set(),
    ),

    # ── Handoffs ─────────────────────────────────────────────────────────
    "HANDOFF": EventTypeDef(
        required_fields={"from_agent", "to_agent"},
        optional_fields=set(),
    ),

    # ── Node lifecycle ───────────────────────────────────────────────────
    "NODE_STARTED": EventTypeDef(
        required_fields={"node_id"},
        optional_fields={"node_name", "node_type"},
    ),
    "NODE_UPDATE": EventTypeDef(
        required_fields={"runtime", "status"},
        optional_fields={"run_id"},
    ),
    "NODE_FAILED": EventTypeDef(
        required_fields={"node_id", "error"},
        optional_fields={"node_name"},
    ),

    # ── Messages ─────────────────────────────────────────────────────────
    "MESSAGE": EventTypeDef(
        required_fields={"text"},
        optional_fields={"source", "coalesced", "evidence_refs"},
    ),
    "MESSAGE_CHUNK": EventTypeDef(
        required_fields={"text"},
        optional_fields={"source"},
    ),
    "TEXT_MESSAGE_START": EventTypeDef(
        required_fields={"message_id"},
        optional_fields={"role"},
    ),
    "TEXT_MESSAGE_CONTENT": EventTypeDef(
        required_fields={"message_id", "delta"},
        optional_fields=set(),
    ),
    "TEXT_MESSAGE_END": EventTypeDef(
        required_fields={"message_id"},
        optional_fields=set(),
    ),
    "TEXT_MESSAGE_CHUNK": EventTypeDef(
        required_fields={"role", "delta"},
        optional_fields=set(),
    ),

    # ── State ────────────────────────────────────────────────────────────
    "STATE_SNAPSHOT": EventTypeDef(
        required_fields={"state"},
        optional_fields={"redacted"},
    ),

    # ── Human-in-the-loop ────────────────────────────────────────────────
    "HITL_PROMPT": EventTypeDef(
        required_fields={"hitl_id", "step_id", "prompt_text", "options", "timeout_seconds"},
        optional_fields={"context", "created_at"},
    ),
    "HITL_RESPONSE": EventTypeDef(
        required_fields={"hitl_id", "decision", "operator_id", "responded_at"},
        optional_fields={"modified_data", "notes"},
    ),
    "HITL_TIMEOUT": EventTypeDef(
        required_fields={"hitl_id", "timeout_seconds"},
        optional_fields=set(),
    ),

    # ── Raw / fallback ───────────────────────────────────────────────────
    "RAW": EventTypeDef(
        required_fields={"raw"},
        optional_fields={"source"},
    ),
    "CUSTOM": EventTypeDef(
        required_fields={"custom_type"},
        optional_fields={"data"},
    ),
    "CONTRACT_PROPOSED": EventTypeDef(
        required_fields={"contract"},
        optional_fields=set(),
    ),
    "RECEIPT_GENERATED": EventTypeDef(
        required_fields={"receipt"},
        optional_fields=set(),
    ),
    "FAILURE_AUTOPSY_GENERATED": EventTypeDef(
        required_fields={"autopsy"},
        optional_fields=set(),
    ),
    "EVIDENCE_REF_CREATED": EventTypeDef(
        required_fields={"evidence_ref"},
        optional_fields=set(),
    ),
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_event_data(event_type: str, data: dict[str, Any]) -> list[str]:
    """Validate event *data* fields against the registry.

    Returns a list of error messages (empty = valid).
    """
    typedef = EVENT_TYPES.get(event_type)
    if typedef is None:
        return [f"Unknown event type: {event_type!r}"]

    errors: list[str] = []
    for field in typedef.required_fields:
        if field not in data:
            errors.append(
                f"Event {event_type!r} missing required field: {field!r}"
            )
    return errors


def create_event(
    run_id: str,
    sequence: int,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> RunEvent:
    """Create a validated ``RunEvent`` with the current schema version.

    Raises ``ValueError`` if the event type is unknown or required fields
    are missing.
    """
    data = data or {}
    errors = validate_event_data(event_type, data)
    if errors:
        raise ValueError("; ".join(errors))

    typedef = EVENT_TYPES.get(event_type)
    return RunEvent(
        schema_version=typedef.version if typedef else CURRENT_SCHEMA_VERSION,
        type=event_type,
        timestamp=_now(),
        run_id=run_id,
        sequence=sequence,
        data=data,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
