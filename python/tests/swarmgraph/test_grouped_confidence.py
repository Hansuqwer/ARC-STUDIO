from __future__ import annotations

from swarmgraph.config import SwarmGraphConfig
from swarmgraph.decomposition import CopyDecomposition
from swarmgraph.models import TaskStatus, WorkerResult
from swarmgraph.nodes.consensus import _worker_confidence, run_consensus_round_with_results


def _make_tasks(outputs: list[str | None]) -> list:
    cfg = SwarmGraphConfig(num_workers=len(outputs), fan_out_threshold=0)
    tasks = CopyDecomposition().decompose("Implement A. Test B. Document C.", len(outputs), cfg)
    for index, (task, output) in enumerate(zip(tasks, outputs), start=1):
        task.assigned_agent_id = f"worker-{index}"
        if output is None:
            task.status = TaskStatus.failed
            task.result = WorkerResult(
                worker_id=f"worker-{index}",
                task_id=task.id,
                output="",
                error="boom",
            )
        else:
            task.status = TaskStatus.completed
            task.result = WorkerResult(
                worker_id=f"worker-{index}",
                task_id=task.id,
                output=output,
            )
    return tasks


def test_worker_confidence_scales_with_output() -> None:
    long_task = _make_tasks(["x" * 400])[0]
    short_task = _make_tasks(["ok"])[0]

    long_conf, _ = _worker_confidence(long_task)
    short_conf, _ = _worker_confidence(short_task)

    assert long_conf > short_conf
    assert 0.0 < short_conf <= 1.0
    assert long_conf <= 1.0


def test_worker_confidence_zero_for_error_and_missing() -> None:
    err_task = _make_tasks([None])[0]
    err_conf, err_reason = _worker_confidence(err_task)

    assert err_conf == 0.0
    assert "error" in err_reason


def test_grouped_votes_carry_real_confidence() -> None:
    tasks = _make_tasks(["x" * 400, "ok", "ok"])

    outcomes = run_consensus_round_with_results(tasks)

    assert len(outcomes) == 3
    votes = outcomes[0].consensus_result.votes
    confidences = sorted({round(v.confidence, 4) for v in votes})
    # Not all votes collapse to a single fixed confidence.
    assert len(confidences) >= 2
    meta = tasks[0].metadata["adaptive_consensus"]
    assert "mean_approval_confidence" in meta
    assert "weighted_approval_ratio" in meta
    assert 0.0 < meta["mean_approval_confidence"] <= 1.0
