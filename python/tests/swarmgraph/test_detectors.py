from __future__ import annotations

from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.consensus import ConsensusResult
from agent_runtime_cockpit.swarmgraph.detectors import (
    detect_consensus_failure,
    detect_coordination_deadlock,
    detect_resource_exhaustion,
)
from agent_runtime_cockpit.swarmgraph.events import SwarmGraphEventKind
from agent_runtime_cockpit.swarmgraph.models import ApprovalDecision, SwarmTask
from agent_runtime_cockpit.swarmgraph.nodes.consensus import ConsensusRoundOutcome
from agent_runtime_cockpit.swarmgraph.state import SwarmState
from agent_runtime_cockpit.swarmgraph import runner as runner_module
from agent_runtime_cockpit.swarmgraph.runner import SwarmGraphRunner
from agent_runtime_cockpit.swarmgraph.models import WorkerResult


def _outcome(task_id: str, approved: bool) -> ConsensusRoundOutcome:
    return ConsensusRoundOutcome(
        task_id=task_id,
        decision=ApprovalDecision(approved=approved, reason="test"),
        consensus_result=ConsensusResult(
            reached=approved,
            approved=approved,
            total_votes=1,
            approval_count=1 if approved else 0,
            rejection_count=0 if approved else 1,
            required=1,
        ),
    )


def test_detect_consensus_failure_when_majority_rejected() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    event = detect_consensus_failure(
        [_outcome("a", False), _outcome("b", False), _outcome("c", True)],
        state,
    )

    assert event is not None
    assert event.kind == SwarmGraphEventKind.error
    assert event.data["failure_mode"] == "consensus_failure"
    assert event.data["rejected_count"] == 2


def test_detect_consensus_failure_ignores_non_majority() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    assert detect_consensus_failure([_outcome("a", False), _outcome("b", True)], state) is None


def test_detect_resource_exhaustion_at_eighty_percent() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    state.accumulated_cost_usd = 8.0

    event = detect_resource_exhaustion(state, 10.0)

    assert event is not None
    assert event.data["failure_mode"] == "resource_exhaustion"
    assert event.data["ratio"] == 0.8


def test_detect_resource_exhaustion_below_threshold_returns_none() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    state.accumulated_cost_usd = 7.9

    assert detect_resource_exhaustion(state, 10.0) is None


def test_detect_coordination_deadlock_when_pending_count_sticks() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    state.current_round = 1
    task = SwarmTask(prompt="pending")
    state.tasks[task.id] = task

    event = detect_coordination_deadlock(state, previous_pending_count=1)

    assert event is not None
    assert event.data["failure_mode"] == "coordination_deadlock"
    assert event.data["stuck_tasks"] == 1


def test_detect_coordination_deadlock_ignores_first_round() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    task = SwarmTask(prompt="pending")
    state.tasks[task.id] = task

    assert detect_coordination_deadlock(state, previous_pending_count=1) is None


def test_detectors_do_not_modify_state() -> None:
    state = SwarmState(config=SwarmGraphConfig())
    state.accumulated_cost_usd = 8.0
    before = state.model_dump()

    detect_resource_exhaustion(state, 10.0)

    assert state.model_dump() == before


def test_runner_emits_resource_exhaustion_event(monkeypatch) -> None:
    async def cost_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="ok",
            cost_usd=0.8,
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", cost_worker)
    cfg = SwarmGraphConfig(
        num_workers=1,
        max_rounds=1,
        enable_budget=True,
        budget_limit_usd=1.0,
    )
    result = SwarmGraphRunner(config=cfg).run("Explain consensus")

    errors = [event for event in result["events"] if event["kind"] == "error"]
    assert any(event["data"].get("failure_mode") == "resource_exhaustion" for event in errors)


def test_runner_emits_consensus_failure_event(monkeypatch) -> None:
    async def failed_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="",
            error="boom",
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", failed_worker)
    result = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1)).run("Explain consensus")

    errors = [event for event in result["events"] if event["kind"] == "error"]
    assert any(event["data"].get("failure_mode") == "consensus_failure" for event in errors)
