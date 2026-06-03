"""Flight segment diff - compare two FlightSegment objects."""

from __future__ import annotations

from .models import DiffSubject, DiffSubjectKind, FlightDiff, RunDiffReport


def diff_flight_segments(left, right):
    from .models import DiffSummary

    fd = FlightDiff(
        events_added=max(0, right.event_count - left.event_count),
        events_removed=max(0, left.event_count - right.event_count),
        events_changed=0,
        segment_hashes_match=left.segment_hash == right.segment_hash,
        hash_chain_valid=left.segment_hash != ""
        and right.previous_segment_hash == left.segment_hash,
        event_types_added=[],
        event_types_removed=[],
        first_event_divergence=None,
    )
    summary = DiffSummary()
    summary.compute_total()
    report = RunDiffReport(
        left=DiffSubject(
            kind=DiffSubjectKind.FLIGHT_SEGMENT,
            id=left.segment_id,
            metadata={
                "run_id": left.run_id,
                "event_count": left.event_count,
                "segment_hash": left.segment_hash,
            },
        ),
        right=DiffSubject(
            kind=DiffSubjectKind.FLIGHT_SEGMENT,
            id=right.segment_id,
            metadata={
                "run_id": right.run_id,
                "event_count": right.event_count,
                "segment_hash": right.segment_hash,
            },
        ),
        mode="flight_vs_flight",
        summary=summary,
        flight_diff=fd,
        warnings=["Hash chain broken between segments"] if not fd.hash_chain_valid else [],
    )
    return report.with_hash()


def diff_flight_events(left_events, right_events):
    from collections import Counter

    left_types = Counter(e.event_type.value for e in left_events)
    right_types = Counter(e.event_type.value for e in right_events)
    all_types = set(left_types) | set(right_types)
    types_added = sorted(t for t in all_types if right_types[t] > 0 and left_types[t] == 0)
    types_removed = sorted(t for t in all_types if left_types[t] > 0 and right_types[t] == 0)
    return FlightDiff(
        events_added=max(0, len(right_events) - len(left_events)),
        events_removed=max(0, len(left_events) - len(right_events)),
        events_changed=0,
        segment_hashes_match=False,
        hash_chain_valid=True,
        event_types_added=types_added,
        event_types_removed=types_removed,
        first_event_divergence=None,
    )
