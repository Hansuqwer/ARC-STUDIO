"""Battle consensus escrow verification tests."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.battle.models import (
    BattleCandidate,
    BattleRun,
    BattleVote,
    ConsensusProtocol,
    VoterType,
)
from agent_runtime_cockpit.battle.runner import BattleRunner


def _vote(*, approved: bool = True, candidate_id: str = "candidate-1") -> BattleVote:
    return BattleVote(
        battle_id="battle-1",
        candidate_id=candidate_id,
        voter="worker-1",
        voter_type=VoterType.model,
        approved=approved,
        reasoning="deterministic vote",
    )


def test_escrow_valid_reveal_is_accepted(tmp_path):
    runner = BattleRunner(workspace=tmp_path)

    revealed = runner._create_verified_escrow_vote(_vote())

    assert revealed.commit_hash is not None
    assert len(revealed.commit_hash) == 64
    assert revealed.reveal_nonce is not None
    assert runner._verify_battle_vote_reveal(revealed) is True


def test_escrow_changed_vote_rejected(tmp_path):
    runner = BattleRunner(workspace=tmp_path)

    revealed = runner._create_verified_escrow_vote(_vote(approved=True))
    tampered = revealed.model_copy(update={"approved": False})

    with pytest.raises(ValueError, match="does not match commitment"):
        runner._verify_battle_vote_reveal(tampered)


def test_escrow_nonce_mismatch_rejected(tmp_path):
    runner = BattleRunner(workspace=tmp_path)

    revealed = runner._create_verified_escrow_vote(_vote())
    tampered = revealed.model_copy(update={"reveal_nonce": "0" * 64})

    with pytest.raises(ValueError, match="does not match commitment"):
        runner._verify_battle_vote_reveal(tampered)


@pytest.mark.parametrize("commit_hash", [None, "not-a-sha256", "a" * 63, "a" * 65])
def test_escrow_malformed_commit_rejected(tmp_path, commit_hash):
    runner = BattleRunner(workspace=tmp_path)

    malformed = _vote().model_copy(update={"commit_hash": commit_hash, "reveal_nonce": "1" * 64})

    with pytest.raises(ValueError, match="Malformed battle vote commit hash"):
        runner._verify_battle_vote_reveal(malformed)


def test_normal_non_escrow_behavior_keeps_plain_votes(tmp_path):
    runner = BattleRunner(workspace=tmp_path)
    battle = BattleRun(
        id="battle-no-escrow",
        prompt="Pick best answer",
        workers=2,
        consensus_protocol=ConsensusProtocol.majority,
        consensus_escrow=False,
    )
    candidates = [
        BattleCandidate(
            id="candidate-1",
            battle_id=battle.id,
            worker_id="worker-0",
            model_id="fake-0",
            output="A",
        ),
        BattleCandidate(
            id="candidate-2",
            battle_id=battle.id,
            worker_id="worker-1",
            model_id="fake-1",
            output="B",
        ),
    ]

    votes = runner._run_consensus_voting(battle, candidates)

    assert len(votes) == 4
    assert all(vote.commit_hash is None for vote in votes)
    assert all(vote.reveal_nonce is None for vote in votes)


def test_escrow_events_emitted_only_for_verified_votes(tmp_path):
    runner = BattleRunner(workspace=tmp_path)
    battle = BattleRun(
        prompt="Pick best answer",
        workers=2,
        consensus_protocol=ConsensusProtocol.majority,
        consensus_escrow=True,
    )

    result = runner.run_battle(battle, worker_models=["fake-a", "fake-b"])

    assert result["status"] == "completed"
    vote_events = [event["type"] for event in result["events"]]
    assert vote_events.count("BATTLE_VOTE_COMMITTED") == 4
    assert vote_events.count("BATTLE_VOTE_REVEALED") == 4

    stored_votes = runner.store.get_votes(battle.id)
    assert len(stored_votes) == 4
    assert all(runner._verify_battle_vote_reveal(vote) for vote in stored_votes)
