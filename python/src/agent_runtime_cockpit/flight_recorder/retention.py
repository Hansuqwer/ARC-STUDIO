"""Flight Recorder retention policy enforcement.

Rules:
  - Never delete an active (open) segment.
  - Delete oldest *closed* segments only.
  - Enforce max_segments, max_total_bytes, max_age_days.
  - Dry run returns list of would-be deleted paths without deleting.
  - Apply mode deletes and updates the index.
  - Never delete audit receipts (those live under .arc/receipts/).
  - Path escape check: refuse to delete outside segments/ directory.

No network I/O, no subprocess, no model calls.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from . import index as _index
from .models import FlightIndex, FlightRecorderConfig, SegmentRef

log = logging.getLogger(__name__)

_MAX_AGE_SECONDS_FACTOR = 86400  # seconds per day


def compute_prunable_segments(
    idx: FlightIndex,
    base_dir: Path,
    config: FlightRecorderConfig,
    active_run_ids: set[str],
) -> list[SegmentRef]:
    """Compute which segments are eligible for deletion.

    Returns list of SegmentRef sorted oldest-first (candidates for deletion).
    Does NOT mutate state.
    """
    # Closed segments only — never delete if the run is still active
    candidates = [
        s for s in idx.segments if s.closed_at is not None and s.run_id not in active_run_ids
    ]

    # Sort by creation time ascending (oldest first)
    candidates.sort(key=lambda s: s.created_at)

    total = len(idx.segments)
    to_delete: list[SegmentRef] = []

    # 1. Age-based pruning
    if config.max_age_days > 0:
        cutoff = time.time() - (config.max_age_days * _MAX_AGE_SECONDS_FACTOR)
        for seg in candidates:
            ts = _parse_unix(seg.created_at)
            if ts and ts < cutoff:
                to_delete.append(seg)

    # 2. Count-based pruning (count all segments including open ones)
    # We only need to prune if, after age pruning, we'd still exceed the limit.
    remaining_after_age = total - len(to_delete)
    if remaining_after_age > config.max_segments:
        excess = remaining_after_age - config.max_segments
        for seg in candidates:
            if seg not in to_delete and excess > 0:
                to_delete.append(seg)
                excess -= 1

    # 3. Size-based pruning
    total_bytes = _compute_total_bytes(base_dir)
    if total_bytes > config.max_total_bytes:
        freed = 0
        for seg in candidates:
            if seg not in to_delete:
                seg_bytes = _segment_bytes(base_dir, seg)
                to_delete.append(seg)
                freed += seg_bytes
                if total_bytes - freed <= config.max_total_bytes:
                    break

    # Deduplicate (preserve order)
    seen: set[str] = set()
    result: list[SegmentRef] = []
    for s in to_delete:
        if s.segment_id not in seen:
            seen.add(s.segment_id)
            result.append(s)

    return result


def prune(
    base_dir: Path,
    config: FlightRecorderConfig,
    active_run_ids: set[str],
    dry_run: bool = True,
) -> dict[str, Any]:
    """Run retention enforcement.

    Args:
        base_dir: Flight recorder base directory.
        config: Recorder configuration.
        active_run_ids: Run IDs with open segments (never deleted).
        dry_run: If True, report but do not delete.

    Returns a summary dict compatible with the CLI ``--json`` output.
    """
    idx = _index.load_index(base_dir)
    prunable = compute_prunable_segments(idx, base_dir, config, active_run_ids)

    deleted_paths: list[str] = []
    deleted_segment_ids: list[str] = []
    errors: list[str] = []

    for seg in prunable:
        paths_to_delete = _segment_file_paths(base_dir, seg)
        for path in paths_to_delete:
            if not _safe_to_delete(base_dir, path):
                errors.append(f"Refusing to delete outside segments/: {path}")
                continue
            deleted_paths.append(str(path))
            if not dry_run:
                try:
                    path.unlink(missing_ok=True)
                    log.info("flight_recorder.retention: deleted %s", path)
                except Exception as exc:
                    errors.append(f"Failed to delete {path}: {exc}")
        deleted_segment_ids.append(seg.segment_id)

    if not dry_run and deleted_segment_ids:
        # Remove from index
        idx.segments = [s for s in idx.segments if s.segment_id not in set(deleted_segment_ids)]
        _index.save_index(base_dir, idx)

    return {
        "dry_run": dry_run,
        "prunable_segments": len(prunable),
        "deleted_segment_ids": deleted_segment_ids,
        "deleted_paths": deleted_paths,
        "errors": errors,
        "applied": not dry_run,
    }


def _segment_file_paths(base_dir: Path, seg: SegmentRef) -> list[Path]:
    """Return the events + meta paths for a segment."""
    paths = []
    for rel in [seg.events_path, seg.meta_path]:
        if not rel:
            continue
        p = Path(rel)
        if not p.is_absolute():
            p = base_dir / rel
        paths.append(p)
    return paths


def _safe_to_delete(base_dir: Path, path: Path) -> bool:
    """Return True only if path is within base_dir/segments/."""
    segments_root = (base_dir / "segments").resolve()
    try:
        resolved = path.resolve()
        # Check that segments_root is a parent of resolved (or equal)
        resolved_parts = resolved.parts
        seg_parts = segments_root.parts
        if len(resolved_parts) <= len(seg_parts):
            return False
        return resolved_parts[: len(seg_parts)] == seg_parts
    except Exception:
        return False


def _compute_total_bytes(base_dir: Path) -> int:
    total = 0
    seg_root = base_dir / "segments"
    if not seg_root.exists():
        return 0
    for p in seg_root.rglob("*.events.jsonl"):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def _segment_bytes(base_dir: Path, seg: SegmentRef) -> int:
    total = 0
    for p in _segment_file_paths(base_dir, seg):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def _parse_unix(ts: str) -> float | None:
    """Parse ISO-8601 UTC timestamp to Unix epoch float."""
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return None
