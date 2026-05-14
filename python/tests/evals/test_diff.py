"""Tests for run diff."""
from datetime import datetime, timezone
from agent_runtime_cockpit.evals.diff import diff_runs
from agent_runtime_cockpit.protocol.schemas import RunRecord, RunEvent, RunStatus


def _make_run(run_id: str, status: RunStatus, event_types: list[str], runtime: str = "swarmgraph"):
    now = datetime.now(timezone.utc)
    events = [
        RunEvent(type=et, timestamp=now.isoformat(), run_id=run_id, sequence=i, data={})
        for i, et in enumerate(event_types)
    ]
    return RunRecord(
        id=run_id,
        workflow_id="wf-test",
        runtime=runtime,
        status=status,
        started_at=now.isoformat(),
        ended_at=now.isoformat(),
        events=events,
    )


def test_diff_same_run():
    run = _make_run("run-a", RunStatus.COMPLETED, ["RUN_STARTED", "NODE_STARTED", "RUN_COMPLETED"])
    d = diff_runs(run, run)
    assert d.run_a_id == "run-a"
    assert d.run_b_id == "run-a"
    assert d.event_count_a == 3
    assert d.event_count_b == 3
    assert d.types_only_in_a == []
    assert d.types_only_in_b == []
    assert d.tool_calls_a == 0
    assert d.status_a == "completed"


def test_diff_different_runs():
    a = _make_run("run-a", RunStatus.COMPLETED, ["RUN_STARTED", "TOOL_CALL", "RUN_COMPLETED"])
    b = _make_run("run-b", RunStatus.FAILED, ["RUN_STARTED", "RUN_FAILED"], runtime="langgraph")
    d = diff_runs(a, b)
    assert d.run_a_id == "run-a"
    assert d.run_b_id == "run-b"
    assert d.status_a == "completed"
    assert d.status_b == "failed"
    assert d.runtime_a == "swarmgraph"
    assert d.runtime_b == "langgraph"
    assert "TOOL_CALL" in d.types_only_in_a
    assert "RUN_FAILED" in d.types_only_in_b
    assert "RUN_STARTED" in d.types_common
    assert d.tool_calls_a == 1
    assert d.tool_calls_b == 0


def test_diff_error_events():
    events = ["RUN_STARTED", "NODE_FAILED"]
    run = _make_run("run-err", RunStatus.FAILED, events)
    events[-1] = "RUN_COMPLETED"
    ok_run = _make_run("run-ok", RunStatus.COMPLETED, events)
    d = diff_runs(ok_run, run)
    assert len(d.error_events_b) >= 1
    assert d.types_only_in_b == ["NODE_FAILED"]
    assert d.types_only_in_a == ["RUN_COMPLETED"]


def test_diff_duration():
    now = datetime.now(timezone.utc)
    a = RunRecord(
        id="fast", workflow_id="wf", runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now.isoformat(),
        ended_at=now.isoformat(),
        events=[],
    )
    later = datetime.now(timezone.utc).isoformat()
    b = RunRecord(
        id="slow", workflow_id="wf", runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now.isoformat(),
        ended_at=later,
        events=[],
    )
    d = diff_runs(a, b)
    assert d.duration_a_ms is not None
    assert d.duration_b_ms is not None
    assert d.duration_b_ms >= d.duration_a_ms
