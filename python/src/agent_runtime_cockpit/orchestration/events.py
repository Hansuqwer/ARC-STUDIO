"""Event helpers — factory, coalesce, ID generation.

Uses ``protocol.events.create_event()`` for validated event creation
with schema versioning (ADR-004).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Iterator
import uuid

from ..protocol.schemas import RunEvent
from ..protocol.events import create_event


_EVENT_SEQUENCE = 0


def new_run_id(prefix: str = "run") -> str:
    """Generate a unique run ID with an optional prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def event(
    run_id: str,
    sequence: int,
    event_type: str,
    data: dict | None = None,
) -> RunEvent:
    """Create a validated event via the protocol registry."""
    return create_event(run_id, sequence, event_type, data or {})


def coalesce_chunks(
    events: Iterable[RunEvent],
    max_chars: int = 4096,
) -> Iterator[RunEvent]:
    """Merge consecutive MESSAGE_CHUNK events into MESSAGE events."""
    buffer: list[str] = []
    sequence = 0
    run_id = ""
    source = ""
    for item in events:
        sequence = item.sequence
        run_id = item.run_id
        if item.type != "MESSAGE_CHUNK":
            if buffer:
                yield create_event(
                    run_id, sequence, "MESSAGE",
                    {"text": "".join(buffer), "source": source, "coalesced": True},
                )
                buffer = []
            yield item
            continue
        source = str(item.data.get("source") or source)
        buffer.append(str(item.data.get("text") or ""))
        if sum(len(part) for part in buffer) >= max_chars:
            yield create_event(
                run_id, sequence, "MESSAGE",
                {"text": "".join(buffer), "source": source, "coalesced": True},
            )
            buffer = []
    if buffer:
        yield create_event(
            run_id, sequence + 1, "MESSAGE",
            {"text": "".join(buffer), "source": source, "coalesced": True},
        )
