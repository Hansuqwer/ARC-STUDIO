"""Tests for battle models (Phase 34/R26A)."""

from datetime import datetime

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
    calculate_elo_change,
    calculate_elo_draw,
)


def test_battle_run_creation():
    """Test BattleRun model creation."""
    battle = BattleRun(
        prompt="Test prompt",
        workers=2,
        topology=BattleTopology.flat,
        consensus_protocol=ConsensusProtocol.majority,
    )

    assert battle.id.startswith("battle-")
    assert battle.prompt == "Test prompt"
    assert battle.workers == 2
    assert battle.topology == BattleTopology.flat
    assert battle.consensus_protocol == ConsensusProtocol.majority
    assert battle.status == BattleStatus.pending
    assert battle.runtime_mode == "fake/offline"
    assert isinstance(battle.created_at, datetime)


def test_battle_run_validation():
    """Test BattleRun validation."""
    # Workers must be between 2 and 4
    with pytest.raises(Exception):
        BattleRun(prompt="Test", workers=1)

    with pytest.raises(Exception):
        BattleRun(prompt="Test", workers=5)


def test_battle_candidate_creation():
    """Test BattleCandidate model creation."""
    candidate = BattleCandidate(
        battle_id="battle-123",
        worker_id="worker-0",
        model_id="fake-model",
        output="Test output",
    )

    assert candidate.id.startswith("candidate-")
    assert candidate.battle_id == "battle-123"
    assert candidate.worker_id == "worker-0"
    assert candidate.model_id == "fake-model"
    assert candidate.output == "Test output"
    assert isinstance(candidate.created_at, datetime)


def test_battle_candidate_immutable():
    """Test BattleCandidate is immutable."""
    candidate = BattleCandidate(
        battle_id="battle-123",
        worker_id="worker-0",
        model_id="fake-model",
        output="Test output",
    )

    with pytest.raises(Exception):
        candidate.output = "Modified output"


def test_battle_vote_creation():
    """Test BattleVote model creation."""
    vote = BattleVote(
        battle_id="battle-123",
        candidate_id="candidate-456",
        voter="judge-1",
        voter_type=VoterType.human,
        approved=True,
        reasoning="Good solution",
    )

    assert vote.id.startswith("vote-")
    assert vote.battle_id == "battle-123"
    assert vote.candidate_id == "candidate-456"
    assert vote.voter == "judge-1"
    assert vote.voter_type == VoterType.human
    assert vote.approved is True
    assert vote.reasoning == "Good solution"
    assert isinstance(vote.created_at, datetime)


def test_battle_vote_with_escrow():
    """Test BattleVote with commit-reveal fields."""
    vote = BattleVote(
        battle_id="battle-123",
        candidate_id="candidate-456",
        voter="judge-1",
        voter_type=VoterType.model,
        approved=True,
        commit_hash="abc123",
        reveal_nonce="xyz789",
    )

    assert vote.commit_hash == "abc123"
    assert vote.reveal_nonce == "xyz789"


def test_battle_outcome_creation():
    """Test BattleOutcome model creation."""
    outcome = BattleOutcome(
        battle_id="battle-123",
        winner_candidate_id="candidate-456",
        consensus_reached=True,
        consensus_result={"protocol": "majority", "votes": 3},
    )

    assert outcome.id.startswith("outcome-")
    assert outcome.battle_id == "battle-123"
    assert outcome.winner_candidate_id == "candidate-456"
    assert outcome.consensus_reached is True
    assert outcome.consensus_result["protocol"] == "majority"
    assert isinstance(outcome.completed_at, datetime)


def test_battle_outcome_no_consensus():
    """Test BattleOutcome when no consensus reached."""
    outcome = BattleOutcome(
        battle_id="battle-123",
        winner_candidate_id=None,
        consensus_reached=False,
        consensus_result={"protocol": "majority", "votes": 1},
    )

    assert outcome.winner_candidate_id is None
    assert outcome.consensus_reached is False


def test_elo_rating_creation():
    """Test EloRating model creation."""
    rating = EloRating(model_id="fake-model")

    assert rating.model_id == "fake-model"
    assert rating.rating == 1500.0  # Default ELO
    assert rating.games_played == 0
    assert rating.wins == 0
    assert rating.losses == 0
    assert rating.draws == 0
    assert isinstance(rating.last_updated, datetime)


def test_elo_rating_with_stats():
    """Test EloRating with game statistics."""
    rating = EloRating(
        model_id="fake-model",
        rating=1600.0,
        games_played=10,
        wins=7,
        losses=2,
        draws=1,
    )

    assert rating.rating == 1600.0
    assert rating.games_played == 10
    assert rating.wins == 7
    assert rating.losses == 2
    assert rating.draws == 1


def test_calculate_elo_change():
    """Test ELO rating change calculation."""
    winner_rating = 1500.0
    loser_rating = 1500.0

    new_winner, new_loser = calculate_elo_change(winner_rating, loser_rating)

    # Winner should gain points, loser should lose points
    assert new_winner > winner_rating
    assert new_loser < loser_rating

    # Total rating should be conserved
    assert abs((new_winner + new_loser) - (winner_rating + loser_rating)) < 0.01


def test_calculate_elo_change_upset():
    """Test ELO rating change when lower-rated player wins."""
    winner_rating = 1400.0  # Lower rated
    loser_rating = 1600.0  # Higher rated

    new_winner, new_loser = calculate_elo_change(winner_rating, loser_rating)

    # Winner should gain more points (upset victory)
    gain = new_winner - winner_rating
    loss = loser_rating - new_loser

    assert gain > 16  # Should gain more than average
    assert loss > 16  # Loser should lose more than average


def test_calculate_elo_draw():
    """Test ELO rating change for a draw."""
    rating_a = 1500.0
    rating_b = 1500.0

    new_a, new_b = calculate_elo_draw(rating_a, rating_b)

    # Equal ratings should stay equal after draw
    assert abs(new_a - rating_a) < 0.01
    assert abs(new_b - rating_b) < 0.01


def test_calculate_elo_draw_unequal():
    """Test ELO rating change for draw with unequal ratings."""
    rating_a = 1400.0  # Lower rated
    rating_b = 1600.0  # Higher rated

    new_a, new_b = calculate_elo_draw(rating_a, rating_b)

    # Lower rated player should gain points from draw
    assert new_a > rating_a
    # Higher rated player should lose points from draw
    assert new_b < rating_b
