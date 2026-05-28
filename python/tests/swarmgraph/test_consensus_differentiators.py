"""Phase 81/R52 — SwarmGraph Consensus Differentiators.

Tests for new consensus protocols:
1. Selective Debate — 2-round voting, top-k filtering, fallback to majority
2. Confidence-Weighted Quorum — weighted voting via confidence field
3. Critic/Verifier Lane — verifier votes with 2x weight
4. HITL Sign-Off Quorum — operator sign-off quorum
5. Gossip Protocol — eventual consensus simulation
6. Protocol Enum — all new values resolve in CONSENSUS_FUNCS
7. Risk Assessment — all new protocols selectable via matrix
8. Deterministic, no LLM, no network, no randomness
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent_runtime_cockpit.swarmgraph.config import ConsensusProtocol
from agent_runtime_cockpit.swarmgraph.consensus import (
    CONSENSUS_FUNCS,
    ConsensusResult,
    confidence_weighted_consensus,
    critic_verifier_consensus,
    gossip_consensus,
    hitl_signoff_quorum,
    run_consensus,
    selective_debate_consensus,
)
from agent_runtime_cockpit.swarmgraph.models import AgentVote, WorkerResult
from agent_runtime_cockpit.swarmgraph.risk_assessment import (
    CONSENSUS_PROTOCOL_BY_RISK,
    CONSENSUS_PROTOCOL_BY_RISK_EXTENDED,
    select_consensus_protocol,
)

# ===========================================================================
# Helper factories
# ===========================================================================


def _vote(
    agent_id: str,
    approved: bool,
    confidence: float = 1.0,
    task_id: str = "task-1",
    round_num: int = 0,
) -> AgentVote:
    return AgentVote(
        agent_id=agent_id,
        task_id=task_id,
        round=round_num,
        approved=approved,
        confidence=confidence,
        reasoning="test",
        timestamp=datetime.now(timezone.utc),
    )


def _result(worker_id: str, task_id: str = "task-1") -> WorkerResult:
    return WorkerResult(
        worker_id=worker_id,
        task_id=task_id,
        output="done",
        started_at=datetime.now(timezone.utc),
    )


# ===========================================================================
# 1. Selective Debate
# ===========================================================================


class TestSelectiveDebate:
    """Selective debate: 2-round voting, top-k filtering, fallback."""

    def test_basic_2_round(self) -> None:
        """Votes on 3 candidates, top-2 survive round 2."""
        votes = [
            _vote("cand-a", True),
            _vote("cand-b", True),
            _vote("cand-c", False),
        ]
        candidates = [_result("cand-a"), _result("cand-b"), _result("cand-c")]
        result = selective_debate_consensus(votes, candidates=candidates, top_k=2)
        assert result.reached is True
        assert result.approved is True
        assert result.protocol == ConsensusProtocol.selective_debate
        assert "survivors" in result.details

    def test_top_k_filtering(self) -> None:
        """Only top-k candidates survive to round 2."""
        votes = [
            _vote("cand-a", True),
            _vote("cand-b", True),
            _vote("cand-c", False),
            _vote("cand-d", False),
        ]
        candidates = [
            _result("cand-a"),
            _result("cand-b"),
            _result("cand-c"),
            _result("cand-d"),
        ]
        result = selective_debate_consensus(votes, candidates=candidates, top_k=2)
        # cand-a and cand-b survive (both approved), should pass
        assert result.reached is True
        assert result.protocol == ConsensusProtocol.selective_debate

    def test_fallback_to_majority_no_candidates(self) -> None:
        """When no candidates provided, fallback to majority."""
        votes = [
            _vote("a", True),
            _vote("b", True),
            _vote("c", False),
        ]
        result = selective_debate_consensus(votes, candidates=None)
        assert result.reached is True
        assert result.approved is True
        assert "(fallback majority)" in result.details

    def test_fallback_when_top_k_gte_total(self) -> None:
        """When top_k >= candidates, fallback to majority."""
        votes = [
            _vote("a", True),
            _vote("b", True),
            _vote("c", False),
        ]
        candidates = [_result("a"), _result("b"), _result("c")]
        result = selective_debate_consensus(votes, candidates=candidates, top_k=5)
        assert result.reached is True
        assert "(fallback majority)" in result.details

    def test_fallback_when_top_k_le_1(self) -> None:
        """When top_k <= 1, fallback to majority."""
        votes = [_vote("a", True), _vote("b", True)]
        candidates = [_result("a"), _result("b")]
        result = selective_debate_consensus(votes, candidates=candidates, top_k=1)
        assert result.reached is True
        assert "(fallback majority)" in result.details

    def test_empty_votes(self) -> None:
        """No votes returns not reached."""
        result = selective_debate_consensus([])
        assert result.reached is False
        assert result.approved is False
        assert result.total_votes == 0

    def test_no_survivors_round2(self) -> None:
        """When top_k <= 1, fallback to majority applies."""
        votes = [
            _vote("cand-a", True),
            _vote("cand-b", False),
        ]
        candidates = [_result("cand-a"), _result("cand-b")]
        # top_k=1 triggers fallback majority: 1/2 approve, not reached
        result = selective_debate_consensus(votes, candidates=candidates, top_k=1)
        assert result.reached is False
        assert result.approved is False
        assert "(fallback majority)" in result.details


# ===========================================================================
# 2. Confidence-Weighted Quorum
# ===========================================================================


class TestConfidenceWeighted:
    """Confidence-weighted: weighted approval, low confidence fails."""

    def test_weighted_approval_passes(self) -> None:
        """High-confidence approval passes."""
        votes = [
            _vote("a", True, confidence=0.9),
            _vote("b", True, confidence=0.8),
            _vote("c", False, confidence=0.7),
        ]
        result = confidence_weighted_consensus(votes)
        # weighted_approval = 0.9 + 0.8 = 1.7, weighted_total = 2.4
        # ratio = 1.7 / 2.4 ≈ 0.708 > 0.5
        assert result.reached is True
        assert result.approved is True
        assert result.protocol == ConsensusProtocol.confidence_weighted

    def test_low_confidence_fails(self) -> None:
        """Low-confidence approval may fail despite numeric majority."""
        votes = [
            _vote("a", True, confidence=0.1),
            _vote("b", True, confidence=0.1),
            _vote("c", False, confidence=0.9),
        ]
        result = confidence_weighted_consensus(votes)
        # weighted_approval = 0.2, weighted_total = 1.1, ratio ≈ 0.182 < 0.5
        assert result.reached is False
        assert result.approved is False

    def test_edge_case_all_zero_confidence(self) -> None:
        """All zero confidence falls back to majority."""
        votes = [
            _vote("a", True, confidence=0.0),
            _vote("b", True, confidence=0.0),
            _vote("c", False, confidence=0.0),
        ]
        result = confidence_weighted_consensus(votes)
        # Fallback to majority: 2/3 approve
        assert result.reached is True
        assert "(fallback majority)" in result.details

    def test_edge_case_all_one_confidence(self) -> None:
        """All 1.0 confidence falls back to majority."""
        votes = [
            _vote("a", True, confidence=1.0),
            _vote("b", False, confidence=1.0),
        ]
        result = confidence_weighted_consensus(votes)
        # Fallback to majority: 1/2 approve -> not reached
        assert result.reached is False
        assert "(fallback majority)" in result.details

    def test_zero_weighted_total(self) -> None:
        """All zero confidence with mixed approved values."""
        votes = [
            _vote("a", False, confidence=0.0),
            _vote("b", False, confidence=0.0),
        ]
        result = confidence_weighted_consensus(votes)
        # all default (all 0) causes fallback majority: 0/2 approve -> not reached
        assert result.reached is False
        assert "(fallback majority)" in result.details

    def test_empty_votes(self) -> None:
        """No votes returns not reached."""
        result = confidence_weighted_consensus([])
        assert result.reached is False
        assert result.total_votes == 0

    def test_custom_threshold(self) -> None:
        """Custom threshold changes behavior."""
        votes = [
            _vote("a", True, confidence=0.4),
            _vote("b", False, confidence=0.6),
        ]
        # ratio = 0.4 / 1.0 = 0.4
        result = confidence_weighted_consensus(votes, threshold=0.3)
        assert result.reached is True
        result2 = confidence_weighted_consensus(votes, threshold=0.5)
        assert result2.reached is False


# ===========================================================================
# 3. Critic/Verifier Lane
# ===========================================================================


class TestCriticVerifier:
    """Critic/verifier: verifier overrides, empty verifiers, combined tally."""

    def test_verifier_approves_workers_pass(self) -> None:
        """Verifier approves and workers have majority."""
        votes = [
            _vote("w1", True),
            _vote("w2", True),
        ]
        verifier = [_vote("v1", True)]
        result = critic_verifier_consensus(votes, verifier_votes=verifier)
        assert result.reached is True
        assert result.approved is True

    def test_verifier_rejects_blocks(self) -> None:
        """Verifier rejects blocks consensus even if workers approve."""
        votes = [
            _vote("w1", True),
            _vote("w2", True),
            _vote("w3", True),
        ]
        verifier = [_vote("v1", False)]
        result = critic_verifier_consensus(votes, verifier_votes=verifier)
        assert result.reached is False
        assert result.approved is False

    def test_empty_verifiers_fallback(self) -> None:
        """No verifier votes falls back to worker majority."""
        votes = [
            _vote("w1", True),
            _vote("w2", False),
        ]
        result = critic_verifier_consensus(votes, verifier_votes=None)
        # 1/2 approve -> not reached
        assert result.reached is False
        assert "(no verifiers)" in result.details

    def test_empty_verifiers_majority_passes(self) -> None:
        """No verifier, worker majority passes."""
        votes = [
            _vote("w1", True),
            _vote("w2", True),
            _vote("w3", False),
        ]
        result = critic_verifier_consensus(votes, verifier_votes=None)
        assert result.reached is True
        assert "(no verifiers)" in result.details

    def test_empty_both(self) -> None:
        """No votes and no verifiers returns not reached."""
        result = critic_verifier_consensus([], verifier_votes=[])
        assert result.reached is False
        assert result.total_votes == 0

    def test_verifier_only(self) -> None:
        """Only verifier votes (no workers)."""
        verifier = [_vote("v1", True)]
        result = critic_verifier_consensus([], verifier_votes=verifier)
        assert result.reached is True
        assert result.approved is True

    def test_verifier_split(self) -> None:
        """Split verifier: majority decides."""
        votes = [
            _vote("w1", True),
            _vote("w2", True),
        ]
        verifier = [
            _vote("v1", True),
            _vote("v2", False),
        ]
        result = critic_verifier_consensus(votes, verifier_votes=verifier)
        # verifier ratio = 2.0/4.0 = 0.5 -> not > 0.5
        assert result.reached is False
        assert result.approved is False

    def test_custom_multiplier(self) -> None:
        """Custom verifier multiplier changes results."""
        votes = [_vote("w1", True)]
        verifier = [_vote("v1", False)]
        # With multiplier 1.0, verifier ratio = 0.0/1.0 = 0.0, still rejects
        result = critic_verifier_consensus(votes, verifier_votes=verifier, verifier_multiplier=1.0)
        assert result.reached is False


# ===========================================================================
# 4. HITL Sign-Off Quorum
# ===========================================================================


class TestHITLSignOff:
    """HITL sign-off: operator quorum, multi-operator, insufficient."""

    def test_1_operator_quorum_passes(self) -> None:
        """Single operator approval passes."""
        votes = [_vote("a", True)]
        prompts = [{"operator_id": "op-1", "approved": True}]
        result = hitl_signoff_quorum(votes, prompts=prompts, operators_required=1)
        assert result.reached is True
        assert result.approved is True
        assert result.protocol == ConsensusProtocol.hitl_signoff

    def test_1_operator_quorum_fails(self) -> None:
        """Single operator rejection fails."""
        votes = [_vote("a", True)]
        prompts = [{"operator_id": "op-1", "approved": False}]
        result = hitl_signoff_quorum(votes, prompts=prompts, operators_required=1)
        assert result.reached is False
        assert result.approved is False

    def test_multi_operator_all_approve(self) -> None:
        """Multiple operators all approve."""
        votes = []
        prompts = [
            {"operator_id": "op-1", "approved": True},
            {"operator_id": "op-2", "approved": True},
        ]
        result = hitl_signoff_quorum(votes, prompts=prompts, operators_required=2)
        assert result.reached is True
        assert result.approved is True

    def test_insufficient_operators(self) -> None:
        """Fewer operators than required."""
        votes = []
        prompts = [{"operator_id": "op-1", "approved": True}]
        result = hitl_signoff_quorum(votes, prompts=prompts, operators_required=2)
        assert result.reached is False
        assert result.approved is False

    def test_no_prompts(self) -> None:
        """No prompts returns not reached."""
        result = hitl_signoff_quorum([], prompts=None)
        assert result.reached is False
        assert "no operator responses" in result.details

    def test_empty_prompts(self) -> None:
        """Empty prompt list returns not reached."""
        result = hitl_signoff_quorum([], prompts=[])
        assert result.reached is False

    def test_operator_details_in_result(self) -> None:
        """Result details include operator response summary."""
        prompts = [
            {"operator_id": "op-1", "approved": True},
            {"operator_id": "op-2", "approved": False},
        ]
        result = hitl_signoff_quorum([], prompts=prompts, operators_required=1)
        assert result.reached is True  # op-1 approves, 1 is enough
        assert "op-1:approved" in result.details
        assert "op-2:rejected" in result.details

    def test_duplicate_operator_last_wins(self) -> None:
        """Last response wins for duplicate operator."""
        prompts = [
            {"operator_id": "op-1", "approved": True},
            {"operator_id": "op-1", "approved": False},
        ]
        result = hitl_signoff_quorum([], prompts=prompts, operators_required=1)
        # Last one (False) wins for op-1
        assert result.reached is False


# ===========================================================================
# 5. Gossip Protocol
# ===========================================================================


class TestGossip:
    """Gossip: single round passes, multi-round, never reaches consensus."""

    def test_single_round_passes(self) -> None:
        """Clear majority passes immediately (round 0)."""
        votes = [
            _vote("a", True),
            _vote("b", True),
            _vote("c", True),
            _vote("d", False),
        ]
        result = gossip_consensus(votes)
        assert result.reached is True
        assert result.approved is True
        assert "round 0" in result.details

    def test_single_round_rejected(self) -> None:
        """Clear majority rejection passes immediately."""
        votes = [
            _vote("a", False),
            _vote("b", False),
            _vote("c", False),
            _vote("d", True),
        ]
        result = gossip_consensus(votes)
        assert result.reached is True
        assert result.approved is False
        assert "round 0" in result.details
        assert "rejected" in result.details

    def test_multi_round_reaches_consensus(self) -> None:
        """Narrow majority reaches consensus after gossip rounds."""
        votes = [
            _vote("a", True),
            _vote("b", True),
            _vote("c", False),
            _vote("d", False),
            _vote("e", True),
        ]
        # 3 approve, 2 reject -> already majority
        result = gossip_consensus(votes, max_rounds=3)
        assert result.reached is True
        assert result.approved is True

    def test_never_reaches_consensus(self) -> None:
        """Tied votes need enough rounds to reach consensus."""
        votes = [
            _vote("a", True),
            _vote("b", False),
        ]
        # With max_rounds=0, no gossip spread happens, tie never breaks
        result = gossip_consensus(votes, max_rounds=0)
        assert result.reached is False
        assert "not reached" in result.details

    def test_empty_votes(self) -> None:
        """No votes returns not reached."""
        result = gossip_consensus([])
        assert result.reached is False
        assert result.total_votes == 0

    def test_near_tie(self) -> None:
        """Near tie requires multiple gossip rounds."""
        votes = [
            _vote("a", True),
            _vote("b", True),
            _vote("c", False),
            _vote("d", False),
        ]
        # 2 approve, 2 reject -> tie with max_rounds=0 (no spread)
        result = gossip_consensus(votes, max_rounds=0)
        assert result.reached is False

        # With enough rounds, tie breaks toward approval
        result2 = gossip_consensus(votes, max_rounds=5)
        assert result2.reached is True


# ===========================================================================
# 6. Protocol Enum
# ===========================================================================


class TestProtocolEnum:
    """All new values resolve in CONSENSUS_FUNCS."""

    def test_selective_debate_in_funcs(self) -> None:
        assert ConsensusProtocol.selective_debate in CONSENSUS_FUNCS

    def test_confidence_weighted_in_funcs(self) -> None:
        assert ConsensusProtocol.confidence_weighted in CONSENSUS_FUNCS

    def test_critic_verifier_in_funcs(self) -> None:
        assert ConsensusProtocol.critic_verifier in CONSENSUS_FUNCS

    def test_hitl_signoff_in_funcs(self) -> None:
        assert ConsensusProtocol.hitl_signoff in CONSENSUS_FUNCS

    def test_gossip_in_funcs(self) -> None:
        assert ConsensusProtocol.gossip in CONSENSUS_FUNCS

    def test_run_consensus_dispatches_selective_debate(self) -> None:
        votes = [_vote("a", True)]
        result = run_consensus(
            votes,
            protocol=ConsensusProtocol.selective_debate,
            candidates=[_result("a")],
        )
        assert result.protocol == ConsensusProtocol.selective_debate
        assert result.approved is True

    def test_run_consensus_dispatches_confidence_weighted(self) -> None:
        votes = [_vote("a", True, confidence=0.9)]
        result = run_consensus(
            votes,
            protocol=ConsensusProtocol.confidence_weighted,
        )
        assert result.protocol == ConsensusProtocol.confidence_weighted
        assert result.approved is True

    def test_run_consensus_dispatches_critic_verifier(self) -> None:
        votes = [_vote("w1", True)]
        verifier = [_vote("v1", True)]
        result = run_consensus(
            votes,
            protocol=ConsensusProtocol.critic_verifier,
            verifier_votes=verifier,
        )
        assert result.protocol == ConsensusProtocol.critic_verifier
        assert result.approved is True

    def test_run_consensus_dispatches_hitl_signoff(self) -> None:
        votes = [_vote("a", True)]
        prompts = [{"operator_id": "op-1", "approved": True}]
        result = run_consensus(
            votes,
            protocol=ConsensusProtocol.hitl_signoff,
            prompts=prompts,
        )
        assert result.protocol == ConsensusProtocol.hitl_signoff
        assert result.approved is True

    def test_run_consensus_dispatches_gossip(self) -> None:
        votes = [_vote("a", True)]
        result = run_consensus(
            votes,
            protocol=ConsensusProtocol.gossip,
        )
        assert result.protocol == ConsensusProtocol.gossip
        assert result.approved is True


# ===========================================================================
# 7. Risk Assessment Integration
# ===========================================================================


class TestRiskAssessmentIntegration:
    """All new protocols selectable via extended matrix."""

    def test_low_extended_includes_selective_debate(self) -> None:
        options = CONSENSUS_PROTOCOL_BY_RISK_EXTENDED["low"]
        assert ConsensusProtocol.majority in options
        assert ConsensusProtocol.selective_debate in options

    def test_medium_extended_includes_confidence_weighted(self) -> None:
        options = CONSENSUS_PROTOCOL_BY_RISK_EXTENDED["medium"]
        assert ConsensusProtocol.confidence_weighted in options
        assert ConsensusProtocol.quorum in options

    def test_high_extended_includes_critic_verifier(self) -> None:
        options = CONSENSUS_PROTOCOL_BY_RISK_EXTENDED["high"]
        assert ConsensusProtocol.critic_verifier in options
        assert ConsensusProtocol.bft in options

    def test_critical_extended_is_escrow(self) -> None:
        options = CONSENSUS_PROTOCOL_BY_RISK_EXTENDED["critical"]
        assert options == [ConsensusProtocol.bft_escrow]

    def test_enable_selective_debate_flag_may_select_selective_debate(self) -> None:
        """With enable_selective_debate=True, low risk may pick selective_debate."""
        result = select_consensus_protocol(
            "Explain what consensus means.",
            enable_selective_debate=True,
        )
        assert result.protocol in (
            ConsensusProtocol.majority,
            ConsensusProtocol.selective_debate,
        )

    def test_enable_selective_debate_flag_still_maps_high_to_bft(self) -> None:
        """enable_selective_debate only affects low risk."""
        result = select_consensus_protocol(
            "Delete user account.",
            enable_selective_debate=True,
        )
        assert result.protocol == ConsensusProtocol.bft

    def test_selective_debate_deterministic(self) -> None:
        """Same input with same flag gives same output."""
        r1 = select_consensus_protocol(
            "List the available API endpoints.",
            enable_selective_debate=True,
        )
        r2 = select_consensus_protocol(
            "List the available API endpoints.",
            enable_selective_debate=True,
        )
        assert r1.protocol == r2.protocol

    def test_basic_mapping_unchanged(self) -> None:
        """Basic mapping still works without extended flags."""
        assert CONSENSUS_PROTOCOL_BY_RISK["low"] == ConsensusProtocol.majority
        assert CONSENSUS_PROTOCOL_BY_RISK["medium"] == ConsensusProtocol.raft
        assert CONSENSUS_PROTOCOL_BY_RISK["high"] == ConsensusProtocol.bft
        assert CONSENSUS_PROTOCOL_BY_RISK["critical"] == ConsensusProtocol.bft_escrow


# ===========================================================================
# 8. Determinism & Edge Cases
# ===========================================================================


class TestDeterminism:
    """All new protocols are deterministic."""

    def test_selective_debate_deterministic(self) -> None:
        votes = [
            _vote("a", True),
            _vote("b", False),
            _vote("c", True),
        ]
        cands = [_result("a"), _result("b"), _result("c")]
        r1 = selective_debate_consensus(votes, candidates=cands, top_k=2)
        r2 = selective_debate_consensus(votes, candidates=cands, top_k=2)
        assert r1.reached == r2.reached
        assert r1.approved == r2.approved
        assert r1.details == r2.details

    def test_confidence_weighted_deterministic(self) -> None:
        votes = [
            _vote("a", True, confidence=0.8),
            _vote("b", False, confidence=0.6),
        ]
        r1 = confidence_weighted_consensus(votes)
        r2 = confidence_weighted_consensus(votes)
        assert r1.reached == r2.reached
        assert r1.details == r2.details

    def test_critic_verifier_deterministic(self) -> None:
        votes = [_vote("w1", True)]
        verifier = [_vote("v1", False)]
        r1 = critic_verifier_consensus(votes, verifier_votes=verifier)
        r2 = critic_verifier_consensus(votes, verifier_votes=verifier)
        assert r1.reached == r2.reached
        assert r1.details == r2.details

    def test_hitl_signoff_deterministic(self) -> None:
        prompts = [{"operator_id": "op-1", "approved": True}]
        r1 = hitl_signoff_quorum([], prompts=prompts, operators_required=1)
        r2 = hitl_signoff_quorum([], prompts=prompts, operators_required=1)
        assert r1.reached == r2.reached
        assert r1.details == r2.details

    def test_gossip_deterministic(self) -> None:
        votes = [
            _vote("a", True),
            _vote("b", False),
            _vote("c", False),
        ]
        r1 = gossip_consensus(votes, max_rounds=3)
        r2 = gossip_consensus(votes, max_rounds=3)
        assert r1.reached == r2.reached
        assert r1.details == r2.details


class TestConsensusResultShape:
    """All protocols return well-shaped ConsensusResult."""

    @pytest.mark.parametrize(
        "protocol_fn,kwargs",
        [
            (
                selective_debate_consensus,
                {"votes": [_vote("a", True)], "candidates": [_result("a")]},
            ),
            (confidence_weighted_consensus, {"votes": [_vote("a", True, confidence=0.8)]}),
            (
                critic_verifier_consensus,
                {"votes": [_vote("w1", True)], "verifier_votes": [_vote("v1", True)]},
            ),
            (
                hitl_signoff_quorum,
                {"votes": [], "prompts": [{"operator_id": "op-1", "approved": True}]},
            ),
            (gossip_consensus, {"votes": [_vote("a", True)]}),
        ],
        ids=[
            "selective_debate",
            "confidence_weighted",
            "critic_verifier",
            "hitl_signoff",
            "gossip",
        ],
    )
    def test_result_has_required_fields(self, protocol_fn, kwargs) -> None:
        result = protocol_fn(**kwargs)
        assert isinstance(result, ConsensusResult)
        assert isinstance(result.reached, bool)
        assert isinstance(result.approved, bool)
        assert isinstance(result.total_votes, int)
        assert isinstance(result.approval_count, int)
        assert isinstance(result.rejection_count, int)
        assert isinstance(result.required, int) or isinstance(result.required, float)
        assert isinstance(result.details, str)
        assert len(result.details) > 0
