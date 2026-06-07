"""Deterministic trace replay for ARC Mobile Runtime.

Compares a recorded trace against a golden trace produced in deterministic mode.
Two traces match if they have the same number of events with identical
(plan_id, step_id, capability_id, allowed, mock, payload_hash) tuples.
Timestamps are intentionally excluded from the match so wall-clock traces
can be compared against deterministic golden traces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .recorder import MobileTrace


@dataclass
class ReplayDiff:
    """Result of comparing a recorded trace against a golden trace."""

    match: bool
    recorded_count: int
    golden_count: int
    first_diff_index: int | None
    diffs: list[dict[str, Any]]

    @property
    def summary(self) -> str:
        if self.match:
            return f"ok — {self.recorded_count} events match golden"
        if self.recorded_count != self.golden_count:
            return (
                f"event count mismatch: recorded={self.recorded_count} golden={self.golden_count}"
            )
        return f"first divergence at index {self.first_diff_index}"


def _event_key(event: Any) -> tuple:
    """Fields compared during replay (excludes timestamp, event_hash, prev_event_hash)."""
    return (
        event.plan_id,
        event.step_id,
        event.capability_id,
        event.allowed,
        event.mock,
        event.payload_hash,
    )


def replay_trace(recorded: MobileTrace, golden: MobileTrace) -> ReplayDiff:
    """Compare *recorded* trace against *golden* trace.

    Returns a ReplayDiff with match=True if all events are semantically
    identical (ignoring timestamps and hash fields).
    """
    diffs: list[dict[str, Any]] = []
    first_diff = None

    if len(recorded.events) != len(golden.events):
        return ReplayDiff(
            match=False,
            recorded_count=len(recorded.events),
            golden_count=len(golden.events),
            first_diff_index=None,
            diffs=[
                {
                    "reason": "event_count_mismatch",
                    "recorded": len(recorded.events),
                    "golden": len(golden.events),
                }
            ],
        )

    for i, (rec_evt, gold_evt) in enumerate(zip(recorded.events, golden.events)):
        rk = _event_key(rec_evt)
        gk = _event_key(gold_evt)
        if rk != gk:
            if first_diff is None:
                first_diff = i
            diffs.append(
                {
                    "index": i,
                    "recorded": {
                        "plan_id": rec_evt.plan_id,
                        "step_id": rec_evt.step_id,
                        "allowed": rec_evt.allowed,
                        "payload_hash": rec_evt.payload_hash,
                    },
                    "golden": {
                        "plan_id": gold_evt.plan_id,
                        "step_id": gold_evt.step_id,
                        "allowed": gold_evt.allowed,
                        "payload_hash": gold_evt.payload_hash,
                    },
                }
            )

    return ReplayDiff(
        match=not diffs,
        recorded_count=len(recorded.events),
        golden_count=len(golden.events),
        first_diff_index=first_diff,
        diffs=diffs,
    )
