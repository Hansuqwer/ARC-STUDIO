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


@pytest.fixture
def temp_store():
    """Create a temporary battle store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_battles.db"
        store = BattleStore(db_path=db_path)
        store.init_db()
        yield store


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
