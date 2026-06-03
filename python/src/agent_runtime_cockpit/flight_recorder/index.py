"""Flight Recorder local index — cross-run, cross-segment master index.

Written atomically to ``.arc/flight/index.json`` using the same pattern
as ``storage/atomic.py``.

Thread-safe via a module-level lock.  The index is the only mutable
global state; segments are append-only and self-contained.

No network I/O, no subprocess, no model calls.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import FlightIndex, RetentionPolicy, RunEntry, SegmentRef
from .segments import _atomic_write

log = logging.getLogger(__name__)

_INDEX_FILENAME = "index.json"
_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------


def load_index(base_dir: Path) -> FlightIndex:
    """Load the index from disk, or return an empty index if not found."""
    path = base_dir / _INDEX_FILENAME
    if not path.exists():
        return FlightIndex()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return FlightIndex.model_validate(data)
    except Exception as exc:
        log.warning(
            "flight_recorder.index: corrupt index at %s, returning empty: %s",
            path,
            exc,
        )
        return FlightIndex()


def save_index(base_dir: Path, index: FlightIndex) -> None:
    """Atomically persist the index to disk."""
    base_dir.mkdir(parents=True, exist_ok=True)
    index.last_updated_at = _utc_now()
    text = index.model_dump_json(indent=2)
    _atomic_write(base_dir / _INDEX_FILENAME, text)


# ---------------------------------------------------------------------------
# Mutation helpers (all thread-safe)
# ---------------------------------------------------------------------------


def upsert_run(base_dir: Path, run: RunEntry) -> None:
    """Add or update a run entry in the index. Thread-safe."""
    with _LOCK:
        idx = load_index(base_dir)
        idx.runs[run.run_id] = run
        save_index(base_dir, idx)


def add_segment_ref(base_dir: Path, seg_ref: SegmentRef) -> None:
    """Append a segment reference to the index. Thread-safe."""
    with _LOCK:
        idx = load_index(base_dir)
        # Avoid duplicates — replace if segment_id already present
        idx.segments = [s for s in idx.segments if s.segment_id != seg_ref.segment_id]
        idx.segments.append(seg_ref)
        save_index(base_dir, idx)


def update_segment_ref(base_dir: Path, seg_ref: SegmentRef) -> None:
    """Update an existing segment reference. Thread-safe."""
    with _LOCK:
        idx = load_index(base_dir)
        idx.segments = [seg_ref if s.segment_id == seg_ref.segment_id else s for s in idx.segments]
        save_index(base_dir, idx)


def close_run(
    base_dir: Path,
    run_id: str,
    status: str,
    completed_at: Optional[str] = None,
) -> None:
    """Mark a run as completed or failed. Thread-safe."""
    with _LOCK:
        idx = load_index(base_dir)
        if run_id in idx.runs:
            run = idx.runs[run_id]
            run.status = status
            run.completed_at = completed_at or _utc_now()
        save_index(base_dir, idx)


def mark_verified(base_dir: Path) -> None:
    """Update last_verified_at timestamp. Thread-safe."""
    with _LOCK:
        idx = load_index(base_dir)
        idx.last_verified_at = _utc_now()
        save_index(base_dir, idx)


def set_retention(base_dir: Path, retention: RetentionPolicy) -> None:
    """Persist retention configuration. Thread-safe."""
    with _LOCK:
        idx = load_index(base_dir)
        idx.retention = retention
        save_index(base_dir, idx)


def get_runs_for_index(base_dir: Path) -> dict[str, RunEntry]:
    """Return run map from the current index. No lock — caller should be careful."""
    idx = load_index(base_dir)
    return dict(idx.runs)


def segments_for_run(base_dir: Path, run_id: str) -> list[SegmentRef]:
    """Return segment refs for a given run_id."""
    idx = load_index(base_dir)
    return [s for s in idx.segments if s.run_id == run_id]
