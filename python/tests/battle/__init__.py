"""Tests for battle package initialization."""


def test_battle_package_imports():
    """Test that battle package exports are available."""
    from agent_runtime_cockpit.battle import (
        BattleCandidate,
        BattleOutcome,
        BattleRun,
        BattleRunner,
        BattleStatus,
        BattleStore,
        BattleTopology,
        BattleVote,
        ConsensusProtocol,
        EloRating,
        VoterType,
        calculate_elo_change,
        calculate_elo_draw,
    )

    # Just verify imports work
    assert BattleRun is not None
    assert BattleCandidate is not None
    assert BattleVote is not None
    assert BattleOutcome is not None
    assert EloRating is not None
    assert BattleRunner is not None
    assert BattleStore is not None
    assert BattleStatus is not None
    assert BattleTopology is not None
    assert ConsensusProtocol is not None
    assert VoterType is not None
    assert calculate_elo_change is not None
    assert calculate_elo_draw is not None
