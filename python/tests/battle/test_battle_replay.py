"""Battle replay determinism tests (Phase 34.3/R26A)."""

import json
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.battle import (
    BattleRun,
    BattleRunner,
    BattleTopology,
    ConsensusProtocol,
)
from agent_runtime_cockpit.battle.store import BattleStore
from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore


def _run_battle_for_replay(
    workspace: Path,
    *,
    workers: int,
    consensus_protocol: ConsensusProtocol,
) -> tuple[str, list[str], list[dict]]:
    db_path = workspace / "battles.db"
    store = BattleStore(db_path=db_path)
    store.init_db()
    battle = BattleRun(
        prompt="Write a deterministic replay smoke test",
        workers=workers,
        topology=BattleTopology.flat,
        consensus_protocol=consensus_protocol,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=store, workspace=workspace)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    run_id = result["run_id"]
    run_record = IndexedTraceStore(
        trace_dir=workspace / ".arc" / "traces",
        db_path=workspace / ".arc" / "arc.db",
    ).load(run_id)
    assert run_record is not None

    return (
        run_id,
        [event.type for event in run_record.events],
        [event.model_dump() for event in run_record.events],
    )


def _replay_events(workspace: Path, run_id: str) -> list[dict]:
    replayed = CliRunner().invoke(
        app,
        ["runs", "replay", run_id, "--workspace", str(workspace), "--json"],
    )
    assert replayed.exit_code == 0, replayed.output
    payload = json.loads(replayed.output)["data"]
    assert payload["run_id"] == run_id
    assert payload["event_count"] == len(payload["events"])
    return payload["events"]


def test_battle_replay_preserves_event_sequence_for_2_worker_majority():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id, original_types, original_events = _run_battle_for_replay(
            workspace,
            workers=2,
            consensus_protocol=ConsensusProtocol.majority,
        )

        replayed_events = _replay_events(workspace, run_id)

        assert [event["type"] for event in replayed_events] == original_types
        assert replayed_events == original_events


def test_battle_replay_preserves_event_sequence_for_4_worker_quorum():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id, original_types, original_events = _run_battle_for_replay(
            workspace,
            workers=4,
            consensus_protocol=ConsensusProtocol.quorum,
        )

        replayed_events = _replay_events(workspace, run_id)

        assert [event["type"] for event in replayed_events] == original_types
        assert replayed_events == original_events


def test_battle_replay_includes_battle_metadata_without_reexecution():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id, _, _ = _run_battle_for_replay(
            workspace,
            workers=2,
            consensus_protocol=ConsensusProtocol.quorum,
        )

        replayed_events = _replay_events(workspace, run_id)
        battle_events = [event for event in replayed_events if event["type"].startswith("BATTLE_")]

        assert [event["sequence"] for event in replayed_events] == list(range(len(replayed_events)))
        assert battle_events
        assert battle_events[0]["data"]["workers"] == 2
        assert battle_events[0]["data"]["consensus_protocol"] == "quorum"
        assert battle_events[-1]["type"] == "BATTLE_COMPLETED"
