"""Tests for battle runner (Phase 34/R26A)."""

import tempfile
from pathlib import Path

import pytest

from agent_runtime_cockpit.battle import (
    BattleRun,
    BattleRunner,
    BattleStatus,
    BattleTopology,
    ConsensusProtocol,
)
from agent_runtime_cockpit.battle.store import BattleStore
from agent_runtime_cockpit.protocol.events import validate_event_data
from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
from agent_runtime_cockpit.storage.sqlite import SqliteStore


@pytest.fixture
def temp_store():
    """Create a temporary battle store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_battles.db"
        store = BattleStore(db_path=db_path)
        store.init_db()
        yield store


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_runner_creation(temp_store):
    """Test battle runner creation."""
    runner = BattleRunner(store=temp_store)
    assert runner.store == temp_store
    assert runner.events == []


def test_run_battle_2_workers(temp_store):
    """Test running a battle with 2 workers."""
    battle = BattleRun(
        prompt="Write a function to check if a number is prime",
        workers=2,
        topology=BattleTopology.flat,
        consensus_protocol=ConsensusProtocol.majority,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    assert result["battle_id"] == battle.id
    assert len(result["candidates"]) == 2
    assert len(result["votes"]) > 0
    assert "outcome" in result

    # Verify battle was stored
    stored_battle = temp_store.get_battle_run(battle.id)
    assert stored_battle.status == BattleStatus.completed


def test_run_battle_4_workers(temp_store):
    """Test running a battle with 4 workers."""
    battle = BattleRun(
        prompt="Write a function to sort a list",
        workers=4,
        topology=BattleTopology.flat,
        consensus_protocol=ConsensusProtocol.quorum,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    assert len(result["candidates"]) == 4
    assert len(result["votes"]) > 0


def test_run_battle_with_custom_models(temp_store):
    """Test running a battle with custom model IDs."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store)
    result = runner.run_battle(
        battle,
        worker_models=["model-a", "model-b"],
    )

    assert result["status"] == "completed"
    candidates = result["candidates"]
    assert candidates[0]["model_id"] == "model-a"
    assert candidates[1]["model_id"] == "model-b"


def test_run_battle_invalid_runtime_mode(temp_store):
    """Test running a battle with invalid runtime mode."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="provider-backed",  # Not supported
    )

    runner = BattleRunner(store=temp_store)
    result = runner.run_battle(battle)

    assert result["status"] == "failed"
    assert "Only fake/offline runtime mode is supported" in result["error"]


def test_run_battle_invalid_workers(temp_store):
    """Test running a battle with invalid number of workers."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=3,  # Not supported (only 2 or 4)
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store)
    result = runner.run_battle(battle)

    assert result["status"] == "failed"
    assert "Only 2 or 4 workers are supported" in result["error"]


def test_run_battle_emits_events(temp_store):
    """Test that battle runner emits events."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store)
    runner.run_battle(battle)

    events = runner.get_events()
    assert len(events) > 0

    # Check for expected event types
    event_types = [e["type"] for e in events]
    assert "BATTLE_STARTED" in event_types
    assert "BATTLE_CANDIDATE_READY" in event_types
    assert "BATTLE_CONSENSUS_REACHED" in event_types
    assert "BATTLE_COMPLETED" in event_types

    for event in events:
        assert validate_event_data(event["type"], event["data"]) == []


def test_run_battle_updates_elo_ratings(temp_store):
    """Test that battle runner updates ELO ratings."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store)
    runner.run_battle(
        battle,
        worker_models=["model-a", "model-b"],
    )

    # Check that ELO ratings were created/updated
    rating_a = temp_store.get_elo_rating("model-a")
    rating_b = temp_store.get_elo_rating("model-b")

    assert rating_a is not None
    assert rating_b is not None

    # One should have won, one should have lost
    total_games = rating_a.games_played + rating_b.games_played
    assert total_games > 0


# ── Phase 34.1: Battle Run/Trace Integration Tests ──────────────────────────


def test_battle_run_creates_arc_run_record(temp_store, temp_workspace):
    """Test that battle run creates an ARC run record in SQLite."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store, workspace=temp_workspace)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    assert "run_id" in result
    assert "trace_path" in result

    run_id = result["run_id"]

    # Verify SQLite run record exists
    db_path = temp_workspace / ".arc" / "arc.db"
    sqlite_store = SqliteStore(db_path=db_path)
    run_metadata = sqlite_store.get_run(run_id)

    assert run_metadata is not None
    assert run_metadata["id"] == run_id
    assert run_metadata["workflow_id"] == f"battle:{battle.id}"
    assert run_metadata["runtime"] == "swarmgraph-battle"
    assert run_metadata["status"] == "completed"


def test_battle_run_creates_jsonl_trace(temp_store, temp_workspace):
    """Test that battle run creates a JSONL trace file."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store, workspace=temp_workspace)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    trace_path = Path(result["trace_path"])

    # Verify trace file exists
    assert trace_path.exists()
    assert trace_path.suffix == ".jsonl"

    # Verify trace file is not empty
    content = trace_path.read_text()
    assert len(content) > 0


def test_battle_trace_contains_battle_events(temp_store, temp_workspace):
    """Test that battle trace contains battle events."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store, workspace=temp_workspace)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    run_id = result["run_id"]

    # Load the run record
    trace_dir = temp_workspace / ".arc" / "traces"
    db_path = temp_workspace / ".arc" / "arc.db"
    store = IndexedTraceStore(trace_dir=trace_dir, db_path=db_path)
    run_record = store.load(run_id)

    assert run_record is not None
    assert len(run_record.events) > 0

    # Check for expected event types
    event_types = [e.type for e in run_record.events]
    assert "RUN_STARTED" in event_types
    assert "BATTLE_STARTED" in event_types
    assert "BATTLE_CANDIDATE_READY" in event_types
    assert "BATTLE_CONSENSUS_REACHED" in event_types
    assert "BATTLE_COMPLETED" in event_types
    assert "RUN_COMPLETED" in event_types


def test_battle_run_metadata_includes_battle_info(temp_store, temp_workspace):
    """Test that battle run metadata includes battle-specific information."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        topology=BattleTopology.flat,
        consensus_protocol=ConsensusProtocol.majority,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store, workspace=temp_workspace)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    run_id = result["run_id"]

    # Load the run record
    trace_dir = temp_workspace / ".arc" / "traces"
    db_path = temp_workspace / ".arc" / "arc.db"
    store = IndexedTraceStore(trace_dir=trace_dir, db_path=db_path)
    run_record = store.load(run_id)

    assert run_record is not None
    assert run_record.metadata["kind"] == "battle"
    assert run_record.metadata["battle_id"] == battle.id
    assert run_record.metadata["workers"] == 2
    assert run_record.metadata["topology"] == "flat"
    assert run_record.metadata["consensus_protocol"] == "majority"
    assert run_record.metadata["runtime_mode"] == "fake/offline"
    assert "winner_candidate_id" in run_record.metadata


def test_battle_run_can_be_queried_via_runs_cli(temp_store, temp_workspace):
    """Test that battle runs can be queried via arc runs commands."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        runtime_mode="fake/offline",
    )

    runner = BattleRunner(store=temp_store, workspace=temp_workspace)
    result = runner.run_battle(battle)

    assert result["status"] == "completed"
    run_id = result["run_id"]

    # Verify run can be loaded via IndexedTraceStore (used by arc runs get)
    trace_dir = temp_workspace / ".arc" / "traces"
    db_path = temp_workspace / ".arc" / "arc.db"
    store = IndexedTraceStore(trace_dir=trace_dir, db_path=db_path)

    # Test load (used by arc runs get)
    run_record = store.load(run_id)
    assert run_record is not None
    assert run_record.id == run_id

    # Test trace_path (used by arc runs trace)
    trace_path = store.trace_path(run_id)
    assert trace_path.exists()

    # Test list_runs (used by arc runs list)
    run_ids = store.list_runs()
    assert run_id in run_ids
