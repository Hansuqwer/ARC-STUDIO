"""Golden trace evaluation — compare a run against an expected golden trace."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..protocol.schemas import RunRecord, RunStatus


class GoldenTrace(BaseModel):
    id: str
    workflow_id: str
    expected_status: RunStatus = RunStatus.COMPLETED
    expected_event_types: list[str] = Field(default_factory=list)
    expected_final_output_contains: str = ""
    description: str = ""


class EvalResult(BaseModel):
    run_id: str
    golden_id: str
    passed: bool
    status_match: bool
    event_type_match: bool
    output_contains_match: bool
    score: float = 0.0
    details: str = ""


def eval_run(run: RunRecord, golden: GoldenTrace) -> EvalResult:
    """Compare a RunRecord against a GoldenTrace.

    Returns an EvalResult with per-check booleans and an overall pass/fail.
    """
    status_match = run.status == golden.expected_status

    actual_types = {ev.type for ev in run.events}
    expected_set = set(golden.expected_event_types)
    event_type_match = expected_set.issubset(actual_types)

    output_contains_match = True
    if golden.expected_final_output_contains:
        combined = " ".join(str(ev.data.get("final_output", "")) for ev in run.events)
        output_contains_match = golden.expected_final_output_contains in combined

    checks = [status_match, event_type_match, output_contains_match]
    score = sum(checks) / len(checks)
    passed = score >= 0.5 and status_match  # status must match

    parts = []
    if not status_match:
        parts.append(f"status expected={golden.expected_status.value} actual={run.status.value}")
    if not event_type_match:
        parts.append(f"missing event types: {expected_set - actual_types}")
    if not output_contains_match:
        parts.append(f"output missing expected text")

    return EvalResult(
        run_id=run.id,
        golden_id=golden.id,
        passed=passed,
        status_match=status_match,
        event_type_match=event_type_match,
        output_contains_match=output_contains_match,
        score=round(score, 2),
        details="; ".join(parts) if parts else "all checks passed",
    )
