"""Append-only JSONL segment writer for the Local Agent Flight Recorder.

Design:
  - One segment per active write session (rotates by size or event count).
  - Segment events file: ``segments/<run_id>/segment-NNNNNN.events.jsonl``
  - Segment meta file:   ``segments/<run_id>/segment-NNNNNN.meta.json``
  - Meta is written atomically (temp file → os.replace + fsync).
  - Segment hash = SHA-256 over concatenated event hashes in sequence order.
  - Hash chain: each segment's ``previous_segment_hash`` = previous segment's
    ``segment_hash``, enabling tamper-evident ordering across segments.
  - Corrupt/partial trailing JSONL lines are tolerated during read.
  - Never delete an active (open) segment.
  - No network I/O, no subprocess, no model calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import FlightEvent, FlightRecorderConfig, FlightSegment

log = logging.getLogger(__name__)

_GENESIS = "GENESIS"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# SegmentWriter
# ---------------------------------------------------------------------------


class SegmentWriter:
    """Manages a single open segment file.

    Thread-safe via ``_lock``.  Callers must call ``close()`` to finalise
    the segment hash and write atomic metadata.
    """

    def __init__(
        self,
        segment_id: str,
        run_id: str,
        events_path: Path,
        meta_path: Path,
        previous_segment_hash: str,
        config: FlightRecorderConfig,
    ) -> None:
        self._lock = threading.Lock()
        self._segment = FlightSegment(
            segment_id=segment_id,
            run_id=run_id,
            created_at=_utc_now(),
            events_path=str(events_path),
            meta_path=str(meta_path),
            previous_segment_hash=previous_segment_hash,
        )
        self._events_path = events_path
        self._meta_path = meta_path
        self._config = config
        self._event_hashes: list[str] = []
        self._fp: Optional[Any] = None
        self._closed = False
        self._bytes_written = 0

        # Ensure parent directory exists
        events_path.parent.mkdir(parents=True, exist_ok=True)

        # Open for append
        self._fp = events_path.open("a", encoding="utf-8")

        # Write initial meta so the segment is crash-visible immediately
        self._write_meta()

    @property
    def segment(self) -> FlightSegment:
        return self._segment

    @property
    def is_full(self) -> bool:
        """True if the segment should rotate."""
        return self._bytes_written >= self._config.max_segment_bytes

    @property
    def is_closed(self) -> bool:
        return self._closed

    def append(self, event: FlightEvent) -> None:
        """Append one event to the JSONL file. Thread-safe."""
        if self._closed:
            raise RuntimeError(f"Segment {self._segment.segment_id} is closed")
        with self._lock:
            self._append_locked(event)

    def _append_locked(self, event: FlightEvent) -> None:
        line = json.dumps(event.model_dump(), separators=(",", ":")) + "\n"
        encoded = line.encode("utf-8")
        self._fp.write(line)  # type: ignore[union-attr]
        # fsync to make crash-safe
        self._fp.flush()  # type: ignore[union-attr]
        os.fsync(self._fp.fileno())  # type: ignore[union-attr]
        self._bytes_written += len(encoded)

        # Update in-memory segment metadata
        event_hash = event.hash or event.compute_hash()
        self._event_hashes.append(event_hash)
        count = len(self._event_hashes)
        self._segment.event_count = count
        self._segment.last_sequence = event.sequence
        if count == 1:
            self._segment.first_sequence = event.sequence

        # Incrementally update segment hash
        self._segment.segment_hash = self._compute_segment_hash()

        # Write meta periodically (every 10 events or always — keep it cheap)
        if count % 10 == 0 or count == 1:
            self._write_meta()

    def _compute_segment_hash(self) -> str:
        """SHA-256 over the concatenated event hashes in sequence order."""
        combined = ",".join(self._event_hashes)
        return _sha256(combined.encode("utf-8"))

    def _write_meta(self) -> None:
        """Atomically write segment metadata JSON."""
        text = json.dumps(self._segment.__dict__, indent=2, default=str)
        _atomic_write(self._meta_path, text)

    def close(self) -> FlightSegment:
        """Flush, close, and finalise segment metadata. Returns closed segment."""
        with self._lock:
            if self._closed:
                return self._segment
            if self._fp:
                self._fp.flush()
                os.fsync(self._fp.fileno())
                self._fp.close()
                self._fp = None
            self._segment.closed_at = _utc_now()
            self._segment.segment_hash = self._compute_segment_hash()
            self._write_meta()
            self._closed = True
        return self._segment

    def flush(self) -> None:
        """Flush without closing."""
        with self._lock:
            if self._fp and not self._closed:
                self._fp.flush()
                os.fsync(self._fp.fileno())
                self._write_meta()


# ---------------------------------------------------------------------------
# SegmentReader — tolerate partial/corrupt trailing lines
# ---------------------------------------------------------------------------


def read_segment_events(events_path: Path) -> list[dict[str, Any]]:
    """Read events from a JSONL segment file.

    Tolerates a corrupt/partial trailing line (from a crash mid-write).
    Returns list of parsed event dicts; corrupt lines are skipped with a
    warning.
    """
    if not events_path.exists():
        return []
    events: list[dict[str, Any]] = []
    lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning(
                "flight_recorder.segments: corrupt line %d in %s — skipped",
                i,
                events_path,
            )
    return events


def read_segment_meta(meta_path: Path) -> Optional[FlightSegment]:
    """Read segment metadata. Returns None if missing or corrupt."""
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return FlightSegment(**data)
    except Exception as exc:
        log.warning("flight_recorder.segments: corrupt meta %s: %s", meta_path, exc)
        return None


# ---------------------------------------------------------------------------
# Segment naming helpers
# ---------------------------------------------------------------------------


def segment_dir(base_dir: Path, run_id: str) -> Path:
    return base_dir / "segments" / run_id


def segment_events_name(n: int) -> str:
    return f"segment-{n:06d}.events.jsonl"


def segment_meta_name(n: int) -> str:
    return f"segment-{n:06d}.meta.json"


def new_segment_id() -> str:
    return str(uuid.uuid4())


def open_segment(
    base_dir: Path,
    run_id: str,
    segment_number: int,
    previous_segment_hash: str,
    config: FlightRecorderConfig,
) -> SegmentWriter:
    """Create and open a new segment for writing."""
    seg_dir = segment_dir(base_dir, run_id)
    seg_dir.mkdir(parents=True, exist_ok=True)
    events_path = seg_dir / segment_events_name(segment_number)
    meta_path = seg_dir / segment_meta_name(segment_number)
    segment_id = new_segment_id()
    return SegmentWriter(
        segment_id=segment_id,
        run_id=run_id,
        events_path=events_path,
        meta_path=meta_path,
        previous_segment_hash=previous_segment_hash,
        config=config,
    )


# ---------------------------------------------------------------------------
# Atomic write helper (mirrors storage/atomic.py)
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text via temp file + os.replace + fsync. Crash-safe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
