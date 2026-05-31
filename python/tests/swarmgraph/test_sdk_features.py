from __future__ import annotations

import pytest
from typer.testing import CliRunner

from swarmgraph.checkpoint import JsonFileCheckpointStore
from swarmgraph.cli import app
from swarmgraph.config import SwarmGraphConfig
from swarmgraph.decomposition import CopyDecomposition
from swarmgraph.models import TaskStatus, WorkerResult
from swarmgraph.nodes.consensus import run_consensus_round_with_results
from swarmgraph.runner import SwarmGraphRunner


def test_swarmgraph_run_cli_json() -> None:
    result = CliRunner().invoke(app, ["run", "Explain consensus", "--json"])

    assert result.exit_code == 0
    assert '"status": "completed"' in result.output


def test_swarmgraph_run_cli_writes_checkpoints(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", "Explain consensus", "--checkpoint-dir", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    assert list(tmp_path.glob("*.json"))


@pytest.mark.asyncio
async def test_stream_yields_typed_events() -> None:
    runner = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1))

    events = [event async for event in runner.stream("Explain consensus")]

    assert events
    assert events[0].kind.value == "audit"
    assert runner.get_state() is not None


def test_json_file_checkpoint_store_roundtrip(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    runner = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1), checkpoint_store=store)

    runner.run("Explain consensus")
    checkpoint_id = store.list_ids()[0]
    checkpoint = store.load(checkpoint_id)

    assert checkpoint.id == checkpoint_id
    assert checkpoint.config.max_rounds == 1


def test_grouped_consensus_uses_multiple_worker_votes() -> None:
    cfg = SwarmGraphConfig(num_workers=3, fan_out_threshold=0)
    tasks = CopyDecomposition().decompose("Implement A. Test B. Document C.", 3, cfg)
    for index, task in enumerate(tasks, start=1):
        task.assigned_agent_id = f"worker-{index}"
        task.status = TaskStatus.completed
        task.result = WorkerResult(
            worker_id=f"worker-{index}",
            task_id=task.id,
            output="ok",
        )

    outcomes = run_consensus_round_with_results(tasks)

    assert len(outcomes) == 3
    assert all(outcome.consensus_result.total_votes == 3 for outcome in outcomes)
    assert all(task.metadata["adaptive_consensus"]["grouped_votes"] == 3 for task in tasks)


def test_checkpoint_store_rejects_path_escape(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)

    with pytest.raises(ValueError):
        store.load("../escape")


def test_cli_stream_outputs_jsonl_events() -> None:
    result = CliRunner().invoke(app, ["run", "Explain consensus", "--stream"])

    assert result.exit_code == 0
    assert '"kind": "audit"' in result.output
