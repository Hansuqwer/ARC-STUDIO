"""Tests for golden trace evaluation."""
from datetime import datetime, timezone
from agent_runtime_cockpit.evals.golden import GoldenTrace, eval_run
from agent_runtime_cockpit.protocol.schemas import RunRecord, RunEvent, RunStatus


def _make_run(run_id: str, status: RunStatus, event_types: list[str]):
    now = datetime.now(timezone.utc)
    events = [
        RunEvent(type=et, timestamp=now.isoformat(), run_id=run_id, sequence=i,
                 data={"final_output": "Hello World" if et == "RUN_COMPLETED" else {}})
        for i, et in enumerate(event_types)
    ]
    return RunRecord(
        id=run_id, workflow_id="wf-test", runtime="swarmgraph",
        status=status, started_at=now.isoformat(), events=events,
    )


def test_eval_perfect_match():
    run = _make_run("run-1", RunStatus.COMPLETED, ["RUN_STARTED", "RUN_COMPLETED"])
    golden = GoldenTrace(id="g-1", workflow_id="wf-test", expected_status=RunStatus.COMPLETED,
                         expected_event_types=["RUN_STARTED", "RUN_COMPLETED"],
                         expected_final_output_contains="Hello")
    result = eval_run(run, golden)
    assert result.passed
    assert result.score == 1.0
    assert result.status_match


def test_eval_status_mismatch():
    run = _make_run("run-2", RunStatus.FAILED, ["RUN_STARTED", "RUN_FAILED"])
    golden = GoldenTrace(id="g-1", workflow_id="wf-test", expected_status=RunStatus.COMPLETED)
    result = eval_run(run, golden)
    assert not result.passed
    assert not result.status_match


def test_eval_event_type_mismatch():
    run = _make_run("run-3", RunStatus.COMPLETED, ["RUN_STARTED"])
    golden = GoldenTrace(id="g-1", workflow_id="wf-test", expected_status=RunStatus.COMPLETED,
                         expected_event_types=["RUN_STARTED", "RUN_COMPLETED"])
    result = eval_run(run, golden)
    assert not result.event_type_match
    # score = 2/3 rounded, status + output match keeps passed=True
    assert result.passed


def test_eval_output_contains_fail():
    run = _make_run("run-4", RunStatus.COMPLETED, ["RUN_STARTED", "RUN_COMPLETED"])
    golden = GoldenTrace(id="g-1", workflow_id="wf-test", expected_status=RunStatus.COMPLETED,
                         expected_final_output_contains="Bonjour")
    result = eval_run(run, golden)
    assert not result.output_contains_match


def test_eval_score_partial():
    run = _make_run("run-5", RunStatus.COMPLETED, ["RUN_STARTED"])
    golden = GoldenTrace(id="g-1", workflow_id="wf-test", expected_status=RunStatus.COMPLETED,
                         expected_event_types=["RUN_STARTED", "RUN_COMPLETED"])
    result = eval_run(run, golden)
    # score = 2/3 (status + output match, no event type match)
    assert result.score == round(2.0 / 3.0, 2)
