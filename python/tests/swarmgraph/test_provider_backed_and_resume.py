from __future__ import annotations

import pytest

from swarmgraph import EchoProvider, JsonFileCheckpointStore, SwarmGraphConfig, SwarmGraphRunner
from swarmgraph.config import ExecutionMode
from swarmgraph.models import SwarmTask, TaskStatus
from swarmgraph.nodes.queen import queen_prepare_agents
from swarmgraph.state import SwarmState


# ---------------------------------------------------------------------------
# PR2: provider_backed execution mode
# ---------------------------------------------------------------------------


def test_provider_backed_runs_through_injected_provider() -> None:
    cfg = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        max_rounds=1,
        num_workers=1,
    )
    runner = SwarmGraphRunner(config=cfg, provider=EchoProvider())

    result = runner.run_result("Explain consensus")

    assert result.status == "completed"
    assert result.completed_tasks == 1
    assert result.results[0].output.startswith("echo: ")


def test_provider_backed_without_provider_fails_task() -> None:
    cfg = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        max_rounds=1,
        num_workers=1,
    )
    runner = SwarmGraphRunner(config=cfg)

    result = runner.run_result("Explain consensus")

    assert result.failed_tasks == 1


def test_gated_local_still_denies_paid_calls_by_default() -> None:
    cfg = SwarmGraphConfig(
        execution_mode=ExecutionMode.gated_local,
        allow_paid_calls=False,
        max_rounds=1,
        num_workers=1,
    )
    runner = SwarmGraphRunner(config=cfg, provider=EchoProvider())

    result = runner.run_result("Explain consensus")

    # Paid-call gate denies gated_local even though a provider is present.
    assert result.failed_tasks == 1


def test_provider_backed_emits_worker_events() -> None:
    cfg = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        max_rounds=1,
        num_workers=1,
    )
    runner = SwarmGraphRunner(config=cfg, provider=EchoProvider())
    runner.run("Explain consensus")

    kinds = {event.kind.value for event in runner.get_events()}
    assert "worker" in kinds


# ---------------------------------------------------------------------------
# PR3: checkpoint resume
# ---------------------------------------------------------------------------


def test_resume_requires_checkpoint_store() -> None:
    runner = SwarmGraphRunner()
    with pytest.raises(ValueError, match="checkpoint_store"):
        runner.resume("anything")


def test_resume_missing_checkpoint_errors(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    runner = SwarmGraphRunner(checkpoint_store=store)
    with pytest.raises(FileNotFoundError):
        runner.resume("ckpt-does-not-exist")


def test_resume_rejects_path_escape(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    runner = SwarmGraphRunner(checkpoint_store=store)
    with pytest.raises(ValueError):
        runner.resume("../escape")


def test_resume_continues_from_saved_round(tmp_path) -> None:
    """A checkpoint saved at round 1 with a pending task resumes from round 1."""
    store = JsonFileCheckpointStore(tmp_path)
    cfg = SwarmGraphConfig(max_rounds=3, num_workers=1)

    # Hand-build a state paused at round 1 with one pending task and a worker.
    state = SwarmState(config=cfg)
    queen_prepare_agents(state, cfg.num_workers)
    state.current_round = 1
    worker_id = next(iter(state.agents))
    pending = SwarmTask(
        prompt="resume me",
        status=TaskStatus.pending,
        assigned_agent_id=worker_id,
    )
    state.tasks[pending.id] = pending
    checkpoint = state.save_checkpoint()
    store.save(checkpoint)

    runner = SwarmGraphRunner(config=cfg, checkpoint_store=store)
    result = runner.resume_result(checkpoint.id)

    resumed = runner.get_state()
    assert resumed is not None
    assert resumed.metadata["resumed_from"] == checkpoint.id
    assert resumed.metadata["resumed_from_round"] == 1
    # Continued from round >= 1 (did not restart at round 0).
    assert resumed.current_round >= 1
    # The previously-pending task was processed during resume.
    assert result.status == "completed"
    assert resumed.tasks[pending.id].status in (TaskStatus.completed, TaskStatus.failed)


def test_resume_emits_resume_audit_event(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    cfg = SwarmGraphConfig(max_rounds=2, num_workers=1)
    state = SwarmState(config=cfg)
    queen_prepare_agents(state, cfg.num_workers)
    state.current_round = 1
    task = SwarmTask(
        prompt="x",
        status=TaskStatus.pending,
        assigned_agent_id=next(iter(state.agents)),
    )
    state.tasks[task.id] = task
    store.save(state.save_checkpoint())
    ckpt_id = store.list_ids()[0]

    runner = SwarmGraphRunner(config=cfg, checkpoint_store=store)
    runner.resume(ckpt_id)

    decisions = [e.data.get("decision") for e in runner.get_events() if e.kind.value == "audit"]
    assert "resume" in decisions
