"""Event bus persistence for Phase 52 / R25 follow-up.

Writes published events to ``.arc/events/event-log.jsonl`` (append-only).
On daemon startup, replays the last ``MAX_REPLAY`` (500) events back into
the bus so SSE clients connecting after a restart can catch up.

SSE ``Last-Event-ID`` header uses the event's sequential log position
(1-based line number in event-log.jsonl).

Phase 55: adds rolling compaction — bounded by max_entries and max_age_days.
compact() is called on every 200th write to keep the log file bounded.

Design constraints:
- No WebSocket. No shared-server. No remote-sync.
- SSE is local daemon only.
- Writes are best-effort and fire-and-forget (never block the bus publish).
- Replay is bounded to the last 500 events only.
- Compaction is best-effort; never raises; logs on error.
"""

from __future__ import annotations

import json
import logging
import time as _time
from pathlib import Path
from typing import Optional

from .types import ArcEvent, parse_event

log = logging.getLogger(__name__)

MAX_REPLAY = 500
COMPACT_INTERVAL = 200
DEFAULT_EVENT_LOG_DIR = Path(".arc") / "events"
DEFAULT_EVENT_LOG_PATH = DEFAULT_EVENT_LOG_DIR / "event-log.jsonl"


class EventPersistenceWriter:
    """Appends published events to a JSONL log file.

    Thread-safe for single-process use (GIL-protected file append).
    Errors are logged and swallowed — never propagated to the bus.

    Phase 55: compact() bounds the log by max_entries (default 2000) and
    max_age_days (default 7), called on every 200th write.
    """

    def __init__(
        self,
        log_path: Path = DEFAULT_EVENT_LOG_PATH,
        max_entries: int = 2000,
        max_age_days: int = 7,
    ) -> None:
        self._log_path = log_path
        self._max_entries = max_entries
        self._max_age_days = max_age_days
        self._sequence = 0

    def write(self, event: ArcEvent) -> int | None:
        """Append a single event to the log. Best-effort; never raises."""
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            self._sequence += 1
            record = {
                "seq": self._sequence,
                **event.model_dump(mode="json"),
            }
            with self._log_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
            if self._sequence % COMPACT_INTERVAL == 0:
                self.compact()
            return self._sequence
        except Exception:
            log.warning("EventPersistenceWriter: failed to write event", exc_info=True)
            return None

    def compact(self) -> None:
        """Rolling compaction: drops lines beyond max_age_days or past max_entries.

        Writes the surviving tail to a temp file, then atomically renames
        it over the original. Best-effort; never raises.
        """
        if not self._log_path.exists():
            return
        try:
            lines = self._log_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            log.warning("compact: failed to read log", exc_info=True)
            return

        cutoff_ts = _time.time() - self._max_age_days * 86400
        surviving: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            # Check age
            ts = data.get("timestamp", "")
            if ts:
                try:
                    from datetime import datetime

                    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if parsed.timestamp() < cutoff_ts:
                        continue
                except Exception:
                    pass
            surviving.append(line)

        # If still over max_entries, keep only the tail
        if len(surviving) > self._max_entries:
            surviving = surviving[-self._max_entries :]

        changed = len(surviving) != len(lines)
        if not changed:
            return

        # Atomic write: write to tmp, rename
        try:
            tmp_path = self._log_path.with_suffix(".jsonl.tmp")
            tmp_path.write_text("\n".join(surviving) + "\n", encoding="utf-8")
            tmp_path.rename(self._log_path)
        except Exception:
            log.warning("compact: failed to write compacted log", exc_info=True)

    def replay_from(self, last_seen_id: Optional[int] = None) -> list[tuple[int, ArcEvent]]:
        """Replay events from the log, up to the last MAX_REPLAY entries.

        Args:
            last_seen_id: The last sequence ID the client has seen. If None,
                replay from the tail (last MAX_REPLAY events). If given, replay
                events with seq > last_seen_id.

        Returns:
            List of (seq, ArcEvent) tuples in emission order.
        """
        if not self._log_path.exists():
            return []
        try:
            lines = self._log_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            log.warning("EventPersistenceWriter: failed to read log", exc_info=True)
            return []

        # Keep only the last MAX_REPLAY lines
        tail = lines[-MAX_REPLAY:]
        results: list[tuple[int, ArcEvent]] = []
        for line in tail:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                seq = int(data.pop("seq", 0))
                if last_seen_id is not None and seq <= last_seen_id:
                    continue
                event = parse_event(data)
                results.append((seq, event))
            except Exception:
                continue
        return results


# Module-level singleton keyed by log path
_writers: dict[Path, EventPersistenceWriter] = {}


def get_writer(log_path: Path = DEFAULT_EVENT_LOG_PATH) -> EventPersistenceWriter:
    """Get or create the singleton writer for the given log path."""
    if log_path not in _writers:
        _writers[log_path] = EventPersistenceWriter(log_path)
    return _writers[log_path]


def reset_writer(log_path: Path = DEFAULT_EVENT_LOG_PATH) -> None:
    """Remove the singleton writer (for tests)."""
    _writers.pop(log_path, None)
