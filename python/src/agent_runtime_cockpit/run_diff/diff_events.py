"""Run event diff - compare two run records or JSONL event streams."""

from __future__ import annotations

import hashlib
import json

from .models import (
    DiffSubject,
    DiffSubjectKind,
    EventDiff,
    EventEntry,
    FirstDivergence,
    RunDiffReport,
)


def _event_hash(event):
    content = {
        "type": event.type,
        "timestamp": event.timestamp,
        "sequence": event.sequence,
        "data_keys": sorted(event.data.keys()),
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _event_entry_from_event(event):
    return EventEntry(
        event_index=event.sequence,
        event_type=event.type,
        timestamp=event.timestamp,
        sequence=event.sequence,
        data_keys=sorted(event.data.keys()),
        hash=_event_hash(event),
    )


def diff_run_records(left, right):
    from .models import DiffSummary

    left_events = left.events
    right_events = right.events
    left_by_type = {}
    right_by_type = {}
    for e in left_events:
        left_by_type.setdefault(e.type, []).append(e.sequence)
    for e in right_events:
        right_by_type.setdefault(e.type, []).append(e.sequence)
    types_only_in_left = sorted(set(left_by_type) - set(right_by_type))
    types_only_in_right = sorted(set(right_by_type) - set(left_by_type))
    left_map = {e.sequence: e for e in left_events}
    right_map = {e.sequence: e for e in right_events}
    events_added = []
    events_removed = []
    events_changed = []
    sequence_alignment = []
    first_divergence_idx = None
    all_sequences = sorted(set(left_map.keys()) | set(right_map.keys()))
    for seq in all_sequences:
        left_e = left_map.get(seq)
        right_e = right_map.get(seq)
        if left_e and right_e:
            l_hash = _event_hash(left_e)
            r_hash = _event_hash(right_e)
            aligned = l_hash == r_hash
            sequence_alignment.append(
                {
                    "sequence": seq,
                    "left_idx": left_e.sequence,
                    "right_idx": right_e.sequence,
                    "aligned": aligned,
                }
            )
            if not aligned and first_divergence_idx is None:
                first_divergence_idx = len(events_changed)
            if not aligned:
                events_changed.append(
                    {
                        "sequence": seq,
                        "left_type": left_e.type,
                        "right_type": right_e.type,
                        "left_hash": l_hash,
                        "right_hash": r_hash,
                    }
                )
        elif left_e and not right_e:
            events_removed.append(_event_entry_from_event(left_e))
            sequence_alignment.append(
                {"sequence": seq, "left_idx": left_e.sequence, "right_idx": None, "aligned": False}
            )
            if first_divergence_idx is None:
                first_divergence_idx = len(events_removed) - 1
        elif not left_e and right_e:
            events_added.append(_event_entry_from_event(right_e))
            sequence_alignment.append(
                {"sequence": seq, "left_idx": None, "right_idx": right_e.sequence, "aligned": False}
            )
            if first_divergence_idx is None:
                first_divergence_idx = len(events_added) - 1
    event_diff = EventDiff(
        events_added=events_added,
        events_removed=events_removed,
        events_changed=events_changed,
        sequence_alignment=sequence_alignment,
        first_event_divergence=first_divergence_idx,
        event_count_left=len(left_events),
        event_count_right=len(right_events),
    )
    summary = DiffSummary()
    summary.events_added = len(events_added)
    summary.events_removed = len(events_removed)
    summary.events_changed = len(events_changed)
    summary.event_types_added = types_only_in_right
    summary.event_types_removed = types_only_in_left
    summary.compute_total()
    first_div = None
    if first_divergence_idx is not None:
        if events_added and first_divergence_idx < len(events_added):
            first = events_added[first_divergence_idx]
            first_div = FirstDivergence(
                kind="event",
                event_type=first.event_type,
                sequence=first.sequence,
                reason=f"Event type '{first.event_type}' at sequence {first.sequence} not in left run",
                left_value=None,
                right_value={"event_type": first.event_type, "sequence": first.sequence},
            )
        elif events_removed and first_divergence_idx < len(events_removed):
            first = events_removed[first_divergence_idx]
            first_div = FirstDivergence(
                kind="event",
                event_type=first.event_type,
                sequence=first.sequence,
                reason=f"Event type '{first.event_type}' at sequence {first.sequence} not in right run",
                left_value={"event_type": first.event_type, "sequence": first.sequence},
                right_value=None,
            )
        elif events_changed and first_divergence_idx < len(events_changed):
            first = events_changed[first_divergence_idx]
            first_div = FirstDivergence(
                kind="event",
                sequence=first["sequence"],
                reason=f"Event at sequence {first['sequence']} changed: {first['left_type']} -> {first['right_type']}",
                left_value={"type": first["left_type"]},
                right_value={"type": first["right_type"]},
            )
    left_subject = DiffSubject(
        kind=DiffSubjectKind.RUN_RECORD,
        id=left.id,
        run_id=left.id,
        metadata={
            "workflow_id": left.workflow_id,
            "runtime": left.runtime,
            "status": left.status.value,
            "event_count": len(left.events),
        },
    )
    right_subject = DiffSubject(
        kind=DiffSubjectKind.RUN_RECORD,
        id=right.id,
        run_id=right.id,
        metadata={
            "workflow_id": right.workflow_id,
            "runtime": right.runtime,
            "status": right.status.value,
            "event_count": len(right.events),
        },
    )
    report = RunDiffReport(
        left=left_subject,
        right=right_subject,
        mode="run_vs_run",
        summary=summary,
        first_divergence=first_div,
        event_diff=event_diff,
        warnings=[],
    )
    return report.with_hash()


def diff_run_records_from_ids(run_a, run_b, trace_dir=None):
    from pathlib import Path
    from ..storage.jsonl import JsonlTraceStore

    errors = []
    warnings = []
    ws_path = trace_dir or str(Path.cwd())
    store = JsonlTraceStore(Path(ws_path) / ".arc" / "traces")
    rec_a = store.load(run_a)
    rec_b = store.load(run_b)
    if rec_a is None:
        errors.append(f"Run not found: {run_a}")
    if rec_b is None:
        errors.append(f"Run not found: {run_b}")
    if rec_a is None or rec_b is None:
        report = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.RUN_RECORD, id=run_a, run_id=run_a),
            right=DiffSubject(kind=DiffSubjectKind.RUN_RECORD, id=run_b, run_id=run_b),
            mode="run_vs_run",
            errors=errors,
        )
        return report.with_hash(), errors, warnings
    return diff_run_records(rec_a, rec_b), errors, warnings
