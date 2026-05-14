"""Run diff — compare two RunRecord objects."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from ..protocol.schemas import RunRecord, RunStatus


class RunDiff(BaseModel):
    run_a_id: str
    run_b_id: str
    status_a: str
    status_b: str
    runtime_a: str
    runtime_b: str
    duration_a_ms: int | None = None
    duration_b_ms: int | None = None
    event_count_a: int = 0
    event_count_b: int = 0
    types_only_in_a: list[str] = Field(default_factory=list)
    types_only_in_b: list[str] = Field(default_factory=list)
    types_common: list[str] = Field(default_factory=list)
    final_output_a: str | None = None
    final_output_b: str | None = None
    error_events_a: list[dict[str, Any]] = Field(default_factory=list)
    error_events_b: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls_a: int = 0
    tool_calls_b: int = 0


def diff_runs(run_a: RunRecord, run_b: RunRecord) -> RunDiff:
    """Compare two RunRecords and produce a structured diff."""

    def _duration(run: RunRecord) -> int | None:
        if run.ended_at:
            start = datetime.fromisoformat(run.started_at)
            end = datetime.fromisoformat(run.ended_at)
            return int((end - start).total_seconds() * 1000)
        return None

    def _final_output(run: RunRecord) -> str | None:
        for ev in reversed(run.events):
            val = ev.data.get("final_output") or ev.data.get("output") or ev.data.get("message")
            if isinstance(val, str) and val:
                return val
        return None

    def _error_events(run: RunRecord) -> list[dict[str, Any]]:
        return [ev.model_dump() for ev in run.events if "FAILED" in ev.type or "ERROR" in ev.type]

    def _tool_calls(run: RunRecord) -> int:
        return sum(1 for ev in run.events if ev.type == "TOOL_CALL")

    types_a = {ev.type for ev in run_a.events}
    types_b = {ev.type for ev in run_b.events}

    return RunDiff(
        run_a_id=run_a.id,
        run_b_id=run_b.id,
        status_a=run_a.status.value,
        status_b=run_b.status.value,
        runtime_a=run_a.runtime,
        runtime_b=run_b.runtime,
        duration_a_ms=_duration(run_a),
        duration_b_ms=_duration(run_b),
        event_count_a=len(run_a.events),
        event_count_b=len(run_b.events),
        types_only_in_a=sorted(types_a - types_b),
        types_only_in_b=sorted(types_b - types_a),
        types_common=sorted(types_a & types_b),
        final_output_a=_final_output(run_a),
        final_output_b=_final_output(run_b),
        error_events_a=_error_events(run_a),
        error_events_b=_error_events(run_b),
        tool_calls_a=_tool_calls(run_a),
        tool_calls_b=_tool_calls(run_b),
    )
