"""AG-UI event types, mapping context, mapper registry, and canonical event schemas."""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

__all__ = [
    "AGUIEventType",
    "MappingContext",
    "register_mapper",
    "map_event",
    "EVENT_SCHEMAS",
]


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
    CUSTOM = "CUSTOM"
    RAW = "RAW"


EVENT_SCHEMAS: set[str] = {e.value for e in AGUIEventType}


@dataclass
class MappingContext:
    thread_id: str
    run_id: str
    runtime: str
    extra: dict[str, Any] = field(default_factory=dict)


_MAPPERS: dict[str, Callable[[dict[str, Any], MappingContext], list[dict[str, Any]]]] = {}


def register_mapper(
    runtime: str,
    fn: Callable[[dict[str, Any], MappingContext], list[dict[str, Any]]],
) -> None:
    _MAPPERS[runtime] = fn


def map_event(runtime: str, native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    fn = _MAPPERS.get(runtime)
    if fn is None:
        return [{"type": AGUIEventType.RAW.value, "event": native, "source": runtime,
                 "threadId": ctx.thread_id, "runId": ctx.run_id, "timestamp": time.time()}]
    events = fn(native, ctx)
    for ev in events:
        ev.setdefault("threadId", ctx.thread_id)
        ev.setdefault("runId", ctx.run_id)
        ev.setdefault("timestamp", time.time())
    return events
