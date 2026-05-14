"""AG-UI event schema validator."""
from __future__ import annotations

import enum
import logging
from typing import Any

log = logging.getLogger(__name__)


# Duplicate AGUIEventType enum to avoid circular import
class AGUIEventType(str, enum.Enum):
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    RUN_CANCELLED = "RUN_CANCELLED"
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"
    STEP_ERROR = "STEP_ERROR"
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    TEXT_MESSAGE_CHUNK = "TEXT_MESSAGE_CHUNK"
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"
    TOOL_CALL_ERROR = "TOOL_CALL_ERROR"
    HANDOFF = "HANDOFF"
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    CUSTOM = "CUSTOM"
    RAW = "RAW"


# Required fields for all events
REQUIRED_FIELDS = {"type", "timestamp", "threadId", "runId"}

# Event-specific required fields
EVENT_REQUIRED_FIELDS = {
    AGUIEventType.TEXT_MESSAGE_START: {"messageId", "role"},
    AGUIEventType.TEXT_MESSAGE_CONTENT: {"messageId", "delta"},
    AGUIEventType.TEXT_MESSAGE_END: {"messageId"},
    AGUIEventType.TEXT_MESSAGE_CHUNK: {"role", "delta"},
    AGUIEventType.TOOL_CALL_START: {"toolCallId", "toolCallName"},
    AGUIEventType.TOOL_CALL_ARGS: {"toolCallId", "delta"},
    AGUIEventType.TOOL_CALL_END: {"toolCallId"},
    AGUIEventType.TOOL_CALL_RESULT: {"toolCallId", "content"},
    AGUIEventType.STEP_STARTED: {"stepName"},
    AGUIEventType.STEP_FINISHED: {"stepName"},
    AGUIEventType.STATE_SNAPSHOT: {"snapshot"},
    AGUIEventType.RUN_ERROR: {"message"},
}


def validate_event(event: dict[str, Any], runtime: str) -> list[str]:
    """
    Validate AG-UI event schema.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in event:
            errors.append(f"Missing required field: {field}")
    
    # Check event type
    event_type = event.get("type")
    if not event_type:
        errors.append("Missing event type")
        return errors
    
    # Check event-specific fields
    try:
        event_enum = AGUIEventType(event_type)
        required = EVENT_REQUIRED_FIELDS.get(event_enum, set())
        for field in required:
            if field not in event:
                errors.append(f"Missing required field for {event_type}: {field}")
    except ValueError:
        errors.append(f"Unknown event type: {event_type}")
    
    return errors


def validate_events(events: list[dict[str, Any]], runtime: str) -> None:
    """
    Validate list of events and log warnings for any issues.
    """
    for i, event in enumerate(events):
        errors = validate_event(event, runtime)
        if errors:
            log.warning(
                "Event validation failed for %s event %d: %s",
                runtime, i, "; ".join(errors)
            )
