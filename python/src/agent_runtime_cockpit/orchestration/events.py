from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Iterator
import uuid

from ..protocol.schemas import RunEvent


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def event(run_id: str, sequence: int, event_type: str, data: dict) -> RunEvent:
    return RunEvent(type=event_type, timestamp=now(), run_id=run_id, sequence=sequence, data=data)


def coalesce_chunks(events: Iterable[RunEvent], max_chars: int = 4096) -> Iterator[RunEvent]:
    buffer: list[str] = []
    sequence = 0
    run_id = ""
    source = ""
    for item in events:
        sequence = item.sequence
        run_id = item.run_id
        if item.type != "MESSAGE_CHUNK":
            if buffer:
                yield event(run_id, sequence, "MESSAGE", {"text": "".join(buffer), "source": source, "coalesced": True})
                buffer = []
            yield item
            continue
        source = str(item.data.get("source") or source)
        buffer.append(str(item.data.get("text") or ""))
        if sum(len(part) for part in buffer) >= max_chars:
            yield event(run_id, sequence, "MESSAGE", {"text": "".join(buffer), "source": source, "coalesced": True})
            buffer = []
    if buffer:
        yield event(run_id, sequence + 1, "MESSAGE", {"text": "".join(buffer), "source": source, "coalesced": True})
