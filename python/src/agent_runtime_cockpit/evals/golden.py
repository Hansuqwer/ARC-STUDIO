"""Golden trace evaluation — compare a run against an expected golden trace."""
from __future__ import annotations

import json
from pathlib import Path

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
        parts.append("output missing expected text")

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


GOLDENS_DIR = ".arc/goldens"


def _goldens_dir(workspace: Path) -> Path:
    d = workspace / GOLDENS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_golden(workspace: Path, golden: GoldenTrace) -> None:
    """Persist a golden trace to the workspace."""
    d = _goldens_dir(workspace)
    (d / f"{golden.id}.json").write_text(golden.model_dump_json(indent=2))


def load_golden(workspace: Path, golden_id: str) -> GoldenTrace | None:
    """Load a saved golden trace by ID."""
    p = _goldens_dir(workspace) / f"{golden_id}.json"
    if not p.exists():
        return None
    return GoldenTrace.model_validate(json.loads(p.read_text()))


def delete_golden(workspace: Path, golden_id: str) -> bool:
    """Delete a saved golden trace. Returns True if a file was removed."""
    p = _goldens_dir(workspace) / f"{golden_id}.json"
    if not p.exists():
        return False
    p.unlink()
    return True


def list_goldens(workspace: Path) -> list[GoldenTrace]:
    """List all saved golden traces in the workspace."""
    d = _goldens_dir(workspace)
    result: list[GoldenTrace] = []
    if not d.exists():
        return result
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            try:
                result.append(GoldenTrace.model_validate(json.loads(f.read_text())))
            except Exception:
                continue
    return result
