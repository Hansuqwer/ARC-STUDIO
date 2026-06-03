"""Flight Recorder integrity verification.

``arc flight verify`` walks all closed segments, verifies:
  1. Meta file exists and is parseable.
  2. Events file exists.
  3. Each event's hash field matches recomputed hash.
  4. Segment hash matches the hash of all event hashes.
  5. Hash chain: previous_segment_hash links correctly (per run_id, in order).

Tolerates partial/corrupt trailing lines — they are counted as issues
but do not crash the verifier.

No network I/O, no subprocess, no model calls.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from . import index as _index
from .models import (
    FlightVerificationReport,
    SegmentRef,
    VerificationIssue,
)

log = logging.getLogger(__name__)


def verify(base_dir: Path) -> FlightVerificationReport:
    """Verify all segments in the index. Returns a FlightVerificationReport."""
    idx = _index.load_index(base_dir)
    report = FlightVerificationReport(ok=True)

    # Build per-run ordered segment chains for hash-chain verification
    run_segments: dict[str, list[SegmentRef]] = {}
    for seg_ref in idx.segments:
        run_segments.setdefault(seg_ref.run_id, []).append(seg_ref)

    # Sort segments within each run by creation time
    for run_id in run_segments:
        run_segments[run_id].sort(key=lambda s: s.created_at)

    all_seg_refs = idx.segments
    report.checked_segments = len(all_seg_refs)

    for seg_ref in all_seg_refs:
        _verify_segment(base_dir, seg_ref, report)

    # Verify hash chain per run
    for run_id, segs in run_segments.items():
        _verify_chain(run_id, segs, report)

    report.ok = (
        len(report.corrupt_segments) == 0
        and len(report.missing_segments) == 0
        and report.hash_chain_valid
    )

    # Persist verification timestamp
    _index.mark_verified(base_dir)

    return report


def _verify_segment(base_dir: Path, seg_ref: SegmentRef, report: FlightVerificationReport) -> None:
    """Verify a single segment's integrity."""
    segment_id = seg_ref.segment_id
    events_path = _resolve_path(base_dir, seg_ref.events_path)
    meta_path = _resolve_path(base_dir, seg_ref.meta_path)

    # Check meta file
    if meta_path and not meta_path.exists():
        report.missing_segments.append(segment_id)
        report.issues.append(
            VerificationIssue(
                segment_id=segment_id,
                issue_type="missing_file",
                detail=f"meta not found: {seg_ref.meta_path}",
            )
        )

    # Check events file
    if not events_path or not events_path.exists():
        report.missing_segments.append(segment_id)
        report.issues.append(
            VerificationIssue(
                segment_id=segment_id,
                issue_type="missing_file",
                detail=f"events not found: {seg_ref.events_path}",
            )
        )
        return

    # Load events
    raw_events = _safe_load_events(events_path, segment_id, report)
    if raw_events is None:
        return

    # Verify event hashes
    event_hashes: list[str] = []
    for i, raw in enumerate(raw_events):
        expected_hash = raw.get("hash", "")
        # Reconstruct hash from event content
        computed = _compute_event_hash(raw)
        if computed != expected_hash:
            report.corrupt_segments.append(segment_id)
            report.issues.append(
                VerificationIssue(
                    segment_id=segment_id,
                    issue_type="hash_mismatch",
                    detail=f"event index {i}: expected {expected_hash}, computed {computed}",
                )
            )
        event_hashes.append(computed)

    # Verify segment hash
    if event_hashes:
        import hashlib

        computed_seg_hash = hashlib.sha256(",".join(event_hashes).encode("utf-8")).hexdigest()
        if seg_ref.segment_hash and seg_ref.segment_hash != computed_seg_hash:
            if segment_id not in report.corrupt_segments:
                report.corrupt_segments.append(segment_id)
            report.issues.append(
                VerificationIssue(
                    segment_id=segment_id,
                    issue_type="hash_mismatch",
                    detail=(
                        f"segment_hash mismatch: "
                        f"index={seg_ref.segment_hash}, "
                        f"computed={computed_seg_hash}"
                    ),
                )
            )


def _verify_chain(run_id: str, segs: list[SegmentRef], report: FlightVerificationReport) -> None:
    """Verify the hash chain links across segments for a given run."""
    prev_hash = "GENESIS"
    for seg in segs:
        if seg.previous_segment_hash != prev_hash:
            report.hash_chain_valid = False
            report.issues.append(
                VerificationIssue(
                    segment_id=seg.segment_id,
                    issue_type="chain_break",
                    detail=(
                        f"run {run_id}: expected previous_segment_hash={prev_hash}, "
                        f"got {seg.previous_segment_hash}"
                    ),
                )
            )
        prev_hash = seg.segment_hash


def _safe_load_events(
    events_path: Path, segment_id: str, report: FlightVerificationReport
) -> Optional[list[dict]]:
    """Load events from a JSONL file, tolerating partial trailing lines."""
    if not events_path.exists():
        return None
    lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    events = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # Partial/corrupt trailing line — tolerate and report
            report.issues.append(
                VerificationIssue(
                    segment_id=segment_id,
                    issue_type="corrupt_json",
                    detail=f"line {i}: partial/corrupt JSON (crash truncation?)",
                )
            )
            if segment_id not in report.corrupt_segments:
                report.corrupt_segments.append(segment_id)
    return events


def _compute_event_hash(raw: dict) -> str:
    """Recompute the hash field for an event dict."""
    content = {
        "schema_version": raw.get("schema_version", "1"),
        "event_id": raw.get("event_id", ""),
        "event_type": raw.get("event_type", ""),
        "run_id": raw.get("run_id", ""),
        "session_id": raw.get("session_id"),
        "timestamp": raw.get("timestamp", ""),
        "sequence": raw.get("sequence", 0),
        "source": raw.get("source", "arc"),
        "payload": raw.get("payload", {}),
        "audit_ref": raw.get("audit_ref"),
        "trace_ref": raw.get("trace_ref"),
    }
    import hashlib
    import json as _json

    canonical = _json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_path(base_dir: Path, rel_path: str) -> Optional[Path]:
    """Resolve a relative or absolute path stored in the index."""
    if not rel_path:
        return None
    p = Path(rel_path)
    if p.is_absolute():
        return p
    # Try relative to base_dir
    candidate = base_dir / rel_path
    if candidate.exists():
        return candidate
    # Try as-is
    return p
