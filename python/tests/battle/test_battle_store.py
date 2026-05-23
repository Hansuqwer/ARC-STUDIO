"""Tests for battle store (Phase 34/R26A)."""

import tempfile
from pathlib import Path

import pytest

from agent_runtime_cockpit.battle import (
    BattleCandidate,
    BattleOutcome,
    BattleRun,
    BattleStatus,
    BattleTopology,
    BattleVote,
    ConsensusProtocol,
    EloRating,
    VoterType,
)
from agent_runtime_cockpit.battle.store import BattleStore


@pytest.fixture
def temp_store():
    """Create a temporary battle store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_battles.db"
        store = BattleStore(db_path=db_path)
        store.init_db()
        yield store


def test_store_initialization(temp_store):
    """Test battle store initialization."""
    assert temp_store.db_path.exists()


def test_insert_and_get_battle_run(temp_store):
    """Test inserting and retrieving a battle run."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        topology=BattleTopology.flat,
        consensus_protocol=ConsensusProtocol.majority,
    )

    temp_store.insert_battle_run(battle)
    retrieved = temp_store.get_battle_run(battle.id)

    assert retrieved is not None
    assert retrieved.id == battle.id
    assert retrieved.prompt == battle.prompt
    assert retrieved.workers == battle.workers
    assert retrieved.status == BattleStatus.pending


def test_update_battle_status(temp_store):
    """Test updating battle status."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
    )

    temp_store.insert_battle_run(battle)

    from datetime import datetime, timezone

    completed_at = datetime.now(timezone.utc).isoformat()
    temp_store.update_battle_status(
        battle.id,
        BattleStatus.completed.value,
        completed_at=completed_at,
    )

    retrieved = temp_store.get_battle_run(battle.id)
    assert retrieved.status == BattleStatus.completed
    assert retrieved.completed_at is not None


def test_insert_and_get_candidates(temp_store):
    """Test inserting and retrieving candidates."""
    battle = BattleRun(prompt="Test", workers=2)
    temp_store.insert_battle_run(battle)

    candidate1 = BattleCandidate(
        battle_id=battle.id,
        worker_id="worker-0",
        model_id="model-a",
        output="Output A",
    )
    candidate2 = BattleCandidate(
        battle_id=battle.id,
        worker_id="worker-1",
        model_id="model-b",
        output="Output B",
    )

    temp_store.insert_candidate(candidate1)
    temp_store.insert_candidate(candidate2)

    candidates = temp_store.get_candidates(battle.id)
    assert len(candidates) == 2
    assert candidates[0].worker_id == "worker-0"
    assert candidates[1].worker_id == "worker-1"


def test_insert_and_get_votes(temp_store):
    """Test inserting and retrieving votes."""
    battle = BattleRun(prompt="Test", workers=2)
    temp_store.insert_battle_run(battle)

    candidate = BattleCandidate(
        battle_id=battle.id,
        worker_id="worker-0",
        model_id="model-a",
        output="Output A",
    )
    temp_store.insert_candidate(candidate)

    vote = BattleVote(
        battle_id=battle.id,
        candidate_id=candidate.id,
        voter="judge-1",
        voter_type=VoterType.human,
        approved=True,
    )
    temp_store.insert_vote(vote)

    votes = temp_store.get_votes(battle.id)
    assert len(votes) == 1
    assert votes[0].candidate_id == candidate.id
    assert votes[0].approved is True


def test_insert_and_get_outcome(temp_store):
    """Test inserting and retrieving outcome."""
    battle = BattleRun(prompt="Test", workers=2)
    temp_store.insert_battle_run(battle)

    candidate = BattleCandidate(
        battle_id=battle.id,
        worker_id="worker-0",
        model_id="model-a",
        output="Output A",
    )
    temp_store.insert_candidate(candidate)

    outcome = BattleOutcome(
        battle_id=battle.id,
        winner_candidate_id=candidate.id,
        consensus_reached=True,
        consensus_result={"protocol": "majority"},
    )
    temp_store.insert_outcome(outcome)

    retrieved = temp_store.get_outcome(battle.id)
    assert retrieved is not None
    assert retrieved.winner_candidate_id == candidate.id
    assert retrieved.consensus_reached is True


def test_upsert_elo_rating(temp_store):
    """Test upserting ELO ratings."""
    rating = EloRating(model_id="model-a", rating=1500.0)
    temp_store.upsert_elo_rating(rating)

    retrieved = temp_store.get_elo_rating("model-a")
    assert retrieved is not None
    assert retrieved.rating == 1500.0

    # Update rating
    updated = EloRating(
        model_id="model-a",
        rating=1550.0,
        games_played=1,
        wins=1,
    )
    temp_store.upsert_elo_rating(updated)

    retrieved = temp_store.get_elo_rating("model-a")
    assert retrieved.rating == 1550.0
    assert retrieved.games_played == 1
    assert retrieved.wins == 1


def test_list_elo_ratings(temp_store):
    """Test listing ELO ratings."""
    ratings = [
        EloRating(model_id="model-a", rating=1600.0),
        EloRating(model_id="model-b", rating=1500.0),
        EloRating(model_id="model-c", rating=1700.0),
    ]

    for rating in ratings:
        temp_store.upsert_elo_rating(rating)

    leaderboard = temp_store.list_elo_ratings(limit=10)
    assert len(leaderboard) == 3
    # Should be sorted by rating descending
    assert leaderboard[0].model_id == "model-c"  # 1700
    assert leaderboard[1].model_id == "model-a"  # 1600
    assert leaderboard[2].model_id == "model-b"  # 1500


def test_list_battle_runs(temp_store):
    """Test listing battle runs."""
    battle1 = BattleRun(prompt="Test 1", workers=2, status=BattleStatus.completed)
    battle2 = BattleRun(prompt="Test 2", workers=4, status=BattleStatus.pending)

    temp_store.insert_battle_run(battle1)
    temp_store.insert_battle_run(battle2)

    all_battles = temp_store.list_battle_runs(limit=10)
    assert len(all_battles) == 2

    completed = temp_store.list_battle_runs(status=BattleStatus.completed.value, limit=10)
    assert len(completed) == 1
    assert completed[0].id == battle1.id
