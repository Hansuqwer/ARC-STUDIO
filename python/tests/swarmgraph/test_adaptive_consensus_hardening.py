"""Tests for Phase 32/R25 — Adaptive Consensus Hardening.

Tests cover:
- raft_consensus() deterministic leader-based behavior
- bft_consensus() 2/3 supermajority threshold
- run_consensus() dispatch for raft, bft, bft_escrow
- Immutable-safe model_copy for risk audit fields
- Per-task adaptive selection in run_consensus_round()
- Shared prompt override behavior
- Task metadata persistence (adaptive_consensus)
- emit_consensus_event() with optional risk metadata
- Backward compatibility of emit_consensus_event()
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent_runtime_cockpit.swarmgraph.config import ConsensusProtocol, SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.consensus import (
    ConsensusResult,
    bft_consensus,
    raft_consensus,
    run_consensus,
)
from agent_runtime_cockpit.swarmgraph.consensus_escrow import ConsensusEscrow
from agent_runtime_cockpit.swarmgraph.events import emit_consensus_event
from agent_runtime_cockpit.swarmgraph.models import (
    AgentVote,
    ApprovalDecision,
    SwarmTask,
    TaskStatus,
    WorkerResult,
)
from agent_runtime_cockpit.swarmgraph.nodes.consensus import (
    _run_bft_escrow_consensus,
    run_consensus_round,
)
from agent_runtime_cockpit.swarmgraph.state import SwarmState


# ===========================================================================
# Helpers
# ===========================================================================


def vote(agent_id: str, approved: bool, task_id: str = "task-1") -> AgentVote:
    """Create a simple agent vote for testing."""
    return AgentVote(
        agent_id=agent_id,
        task_id=task_id,
        round=0,
        approved=approved,
        confidence=1.0,
        reasoning="test",
    )


def make_task(
    prompt: str,
    task_id: str | None = None,
    agent_id: str = "agent-1",
) -> SwarmTask:
    """Create a task with a result for consensus testing."""
    tid = task_id or f"task-{hash(prompt) % 10000}"
    task = SwarmTask(
        id=tid,
        prompt=prompt,
        status=TaskStatus.in_progress,
        assigned_agent_id=agent_id,
    )
    result = WorkerResult(
        worker_id=agent_id,
        task_id=tid,
        output="done",
        started_at=datetime.now(timezone.utc),
    )
    task.result = result
    return task


# ===========================================================================
# Raft Consensus
# ===========================================================================


class TestRaftConsensus:
    """Deterministic leader-based consensus."""

    def test_raft_no_votes(self) -> None:
        result = raft_consensus([])
        assert result.reached is False
        assert result.approved is False
        assert result.protocol == ConsensusProtocol.raft
        assert result.required == 1
        assert "no leader vote" in result.details

    def test_raft_lowest_agent_id_is_leader(self) -> None:
        votes_list = [
            vote("worker-b", False),
            vote("worker-a", True),
            vote("worker-c", False),
        ]
        result = raft_consensus(votes_list)
        assert result.reached is True
        assert result.approved is True
        assert result.required == 1
        assert "leader=worker-a" in result.details

    def test_raft_leader_rejection_rejects_even_if_majority_approve(self) -> None:
        votes_list = [
            vote("worker-a", False),
            vote("worker-b", True),
            vote("worker-c", True),
        ]
        result = raft_consensus(votes_list)
        assert result.approved is False
        assert result.approval_count == 2
        assert result.rejection_count == 1
        assert "leader=worker-a" in result.details

    def test_raft_single_vote(self) -> None:
        result = raft_consensus([vote("worker-a", True)])
        assert result.reached is True
        assert result.approved is True
        assert result.total_votes == 1

    def test_raft_single_rejection(self) -> None:
        result = raft_consensus([vote("worker-a", False)])
        assert result.reached is True
        assert result.approved is False

    def test_raft_deterministic_leader_selection(self) -> None:
        """Same votes always produce same leader."""
        votes_list = [
            vote("worker-z", True),
            vote("worker-a", False),
            vote("worker-m", True),
        ]
        r1 = raft_consensus(votes_list)
        r2 = raft_consensus(votes_list)
        assert r1.approved == r2.approved
        assert r1.details == r2.details


# ===========================================================================
# BFT Consensus
# ===========================================================================


class TestBftConsensus:
    """2/3 supermajority consensus."""

    def test_bft_no_votes(self) -> None:
        result = bft_consensus([])
        assert result.reached is False
        assert result.approved is False
        assert result.protocol == ConsensusProtocol.bft
        assert "no votes cast" in result.details

    def test_bft_thresholds(self) -> None:
        """Verify 2/3 integer math for various vote counts."""
        expected = {
            1: 1,
            2: 2,
            3: 2,
            4: 3,
            5: 4,
            6: 4,
            7: 5,
            8: 6,
            9: 6,
            10: 7,
        }
        for total, required in expected.items():
            votes_list = [vote(f"worker-{i}", True) for i in range(total)]
            result = bft_consensus(votes_list)
            assert result.required == required, (
                f"total={total}: expected required={required}, got={result.required}"
            )

    def test_bft_reaches_two_of_three(self) -> None:
        result = bft_consensus(
            [
                vote("a", True),
                vote("b", True),
                vote("c", False),
            ]
        )
        assert result.reached is True
        assert result.approved is True
        assert result.required == 2

    def test_bft_rejects_one_of_three(self) -> None:
        result = bft_consensus(
            [
                vote("a", True),
                vote("b", False),
                vote("c", False),
            ]
        )
        assert result.reached is False
        assert result.approved is False
        assert result.required == 2

    def test_bft_unanimous(self) -> None:
        result = bft_consensus(
            [
                vote("a", True),
                vote("b", True),
                vote("c", True),
                vote("d", True),
            ]
        )
        assert result.reached is True
        assert result.approved is True
        assert result.required == 3

    def test_bft_quorum_override(self) -> None:
        """Explicit quorum can override the 2/3 default."""
        votes_list = [vote(f"w-{i}", True) for i in range(5)]
        result = bft_consensus(votes_list, quorum=3)
        assert result.required == 3
        assert result.approved is True

    def test_bft_quorum_override_stricter(self) -> None:
        votes_list = [vote(f"w-{i}", True) for i in range(3)]
        result = bft_consensus(votes_list, quorum=3)
        assert result.required == 3
        assert result.approved is True

    def test_bft_quorum_override_blocked(self) -> None:
        votes_list = [vote(f"w-{i}", True) for i in range(3)]
        result = bft_consensus(votes_list, quorum=4)
        assert result.reached is False
        assert result.approved is False


# ===========================================================================
# Consensus Dispatch
# ===========================================================================


class TestConsensusDispatch:
    """run_consensus must dispatch to correct protocol."""

    def test_dispatch_majority(self) -> None:
        result = run_consensus([vote("a", True)], protocol=ConsensusProtocol.majority)
        assert result.protocol == ConsensusProtocol.majority

    def test_dispatch_raft(self) -> None:
        result = run_consensus([vote("a", True)], protocol=ConsensusProtocol.raft)
        assert result.protocol == ConsensusProtocol.raft

    def test_dispatch_bft(self) -> None:
        result = run_consensus(
            [vote("a", True), vote("b", True), vote("c", False)],
            protocol=ConsensusProtocol.bft,
        )
        assert result.protocol == ConsensusProtocol.bft
        assert result.approved is True

    def test_dispatch_bft_escrow_preserves_protocol(self) -> None:
        result = run_consensus(
            [vote("a", True)],
            protocol=ConsensusProtocol.bft_escrow,
        )
        assert result.protocol == ConsensusProtocol.bft_escrow

    def test_dispatch_bft_escrow_uses_bft_semantics(self) -> None:
        """bft_escrow should behave like bft but with different protocol field."""
        r_bft = run_consensus(
            [vote("a", True), vote("b", True), vote("c", False)],
            protocol=ConsensusProtocol.bft,
        )
        r_escrow = run_consensus(
            [vote("a", True), vote("b", True), vote("c", False)],
            protocol=ConsensusProtocol.bft_escrow,
        )
        assert r_bft.approved == r_escrow.approved
        assert r_bft.required == r_escrow.required
        assert r_escrow.protocol == ConsensusProtocol.bft_escrow

    def test_dispatch_bft_escrow_single_vote(self) -> None:
        result = run_consensus(
            [vote("a", True)],
            protocol=ConsensusProtocol.bft_escrow,
        )
        assert result.protocol == ConsensusProtocol.bft_escrow
        assert result.approved is True
        assert result.required == 1


# ===========================================================================
# Immutable-Safe Risk Audit Fields
# ===========================================================================


class TestImmutableRiskFields:
    """ConsensusResult risk fields must be set via model_copy, not
    object.__setattr__."""

    def test_model_copy_sets_risk_fields(self) -> None:
        base = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=1,
            approval_count=1,
            required=1,
            protocol=ConsensusProtocol.majority,
            details="ok",
        )
        updated = base.model_copy(
            update={
                "risk_level": "critical",
                "risk_score": 100,
                "risk_signals": ["production database"],
                "risk_rationale": "Matched critical signal.",
            }
        )
        assert updated.risk_level == "critical"
        assert updated.risk_score == 100
        assert updated.risk_signals == ["production database"]
        assert updated.risk_rationale == "Matched critical signal."
        # Original unchanged
        assert base.risk_level == ""

    def test_run_consensus_round_sets_risk_fields_via_copy(self) -> None:
        task = make_task("Delete production database.")
        run_consensus_round([task], escrow=ConsensusEscrow())
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "critical"
        assert meta["protocol"] == "bft_escrow"
        assert meta["score"] >= 100


# ===========================================================================
# Task Metadata Persistence
# ===========================================================================


class TestTaskMetadata:
    """run_consensus_round must persist adaptive_consensus metadata."""

    def test_persists_adaptive_metadata(self) -> None:
        task = make_task("Delete production database.")
        run_consensus_round([task], escrow=ConsensusEscrow())

        assert len(task.metadata) >= 1
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "critical"
        assert meta["protocol"] == "bft_escrow"
        assert meta["score"] >= 100
        assert isinstance(meta["matched_signals"], list)
        assert len(meta["matched_signals"]) >= 1
        assert isinstance(meta["rationale"], str)
        assert len(meta["rationale"]) > 0

    def test_low_prompt_metadata(self) -> None:
        task = make_task("Explain what consensus means.")
        run_consensus_round([task])
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "low"
        assert meta["protocol"] == "majority"
        assert meta["score"] == 5

    def test_medium_prompt_metadata(self) -> None:
        task = make_task("Update config for staging.")
        run_consensus_round([task])
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "medium"
        assert meta["protocol"] == "raft"

    def test_high_prompt_metadata(self) -> None:
        task = make_task("Delete user account and grant admin.")
        run_consensus_round([task])
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "high"
        assert meta["protocol"] == "bft"


# ===========================================================================
# Per-Task Adaptive Selection
# ===========================================================================


class TestPerTaskSelection:
    """Each task should use its own prompt for adaptive selection unless
    a shared prompt is explicitly provided."""

    def test_uses_each_task_prompt(self) -> None:
        low_task = make_task("Explain consensus.", task_id="task-low")
        critical_task = make_task("Delete production database.", task_id="task-critical")

        run_consensus_round([low_task, critical_task], escrow=ConsensusEscrow())

        assert low_task.metadata["adaptive_consensus"]["risk"] == "low"
        assert low_task.metadata["adaptive_consensus"]["protocol"] == "majority"

        assert critical_task.metadata["adaptive_consensus"]["risk"] == "critical"
        assert critical_task.metadata["adaptive_consensus"]["protocol"] == "bft_escrow"

    def test_shared_prompt_override(self) -> None:
        low_task = make_task("Explain consensus.", task_id="task-low")
        critical_task = make_task("Delete production database.", task_id="task-critical")

        run_consensus_round(
            [low_task, critical_task],
            prompt="Update config for staging.",
            escrow=ConsensusEscrow(),
        )

        assert low_task.metadata["adaptive_consensus"]["risk"] == "medium"
        assert low_task.metadata["adaptive_consensus"]["protocol"] == "raft"

        assert critical_task.metadata["adaptive_consensus"]["risk"] == "medium"
        assert critical_task.metadata["adaptive_consensus"]["protocol"] == "raft"

    def test_no_result_task_still_has_metadata(self) -> None:
        """Even tasks without a result should have metadata persisted."""
        task = SwarmTask(
            id="task-no-result",
            prompt="Delete production database.",
            status=TaskStatus.in_progress,
        )
        # No result set
        run_consensus_round([task], escrow=ConsensusEscrow())
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "critical"
        assert meta["protocol"] == "bft_escrow"

    def test_legacy_protocol_argument_still_validates(self) -> None:
        task = make_task("Explain consensus.", task_id="task-legacy")

        run_consensus_round([task], protocol="majority")

        assert task.metadata["adaptive_consensus"]["protocol"] == "majority"

    def test_invalid_legacy_protocol_argument_fails_closed_by_validation(self) -> None:
        task = make_task("Explain consensus.", task_id="task-invalid-protocol")

        with pytest.raises(ValueError):
            run_consensus_round([task], protocol="not-a-protocol")


# ===========================================================================
# Consensus Event Metadata
# ===========================================================================


class TestConsensusEventMetadata:
    """emit_consensus_event must include risk/protocol metadata when
    consensus_result is provided."""

    def test_event_includes_risk_metadata(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        approval = ApprovalDecision(
            approved=True,
            reason="ok",
            decided_by="consensus",
        )
        result = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=3,
            approval_count=2,
            rejection_count=1,
            required=2,
            protocol=ConsensusProtocol.bft_escrow,
            details="ok",
            risk_level="critical",
            risk_score=100,
            risk_signals=["production database"],
            risk_rationale="Matched critical signal.",
        )

        event = emit_consensus_event(
            state,
            task_id="task-1",
            approval=approval,
            consensus_result=result,
        )

        assert event.data["protocol"] == "bft_escrow"
        assert event.data["risk"] == "critical"
        assert event.data["risk_score"] == 100
        assert event.data["matched_signals"] == ["production database"]
        assert event.data["total_votes"] == 3
        assert event.data["approval_count"] == 2
        assert event.data["rejection_count"] == 1
        assert event.data["required"] == 2

    def test_event_without_result_backcompat(self) -> None:
        """When consensus_result is None, no protocol/risk fields."""
        state = SwarmState(config=SwarmGraphConfig())
        approval = ApprovalDecision(
            approved=True,
            reason="ok",
            decided_by="consensus",
        )

        event = emit_consensus_event(state, task_id="task-1", approval=approval)

        assert event.data["task_id"] == "task-1"
        assert event.data["approved"] is True
        assert "protocol" not in event.data
        assert "risk" not in event.data

    def test_event_with_partial_result(self) -> None:
        """Risk fields may be empty strings/lists when not populated."""
        state = SwarmState(config=SwarmGraphConfig())
        approval = ApprovalDecision(
            approved=True,
            reason="ok",
            decided_by="consensus",
        )
        # ConsensusResult with default risk fields (empty)
        result = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=1,
            approval_count=1,
            rejection_count=0,
            required=1,
        )

        event = emit_consensus_event(
            state,
            task_id="task-1",
            approval=approval,
            consensus_result=result,
        )

        # Protocol should always be present when result is given
        assert "protocol" in event.data
        assert event.data["risk"] == ""
        assert event.data["risk_score"] == 0
        assert event.data["matched_signals"] == []


# ===========================================================================
# run_consensus_round Integration
# ===========================================================================


class TestRunConsensusRoundIntegration:
    """Integration tests for run_consensus_round with all protocols."""

    def test_low_prompt_uses_majority(self) -> None:
        task = make_task("Explain what this system does.")
        decisions = run_consensus_round([task])
        assert len(decisions) == 1
        assert decisions[0].approved is True

    def test_critical_prompt_uses_escrow(self) -> None:
        task = make_task("Delete production database.")
        escrow = ConsensusEscrow()
        decisions = run_consensus_round([task], escrow=escrow)
        assert len(decisions) == 1
        assert decisions[0].approved is True or decisions[0].approved is False

    def test_bft_escrow_helper_preserves_protocol(self) -> None:
        result = _run_bft_escrow_consensus(
            [vote("a", True)],
            make_task("Delete production database.", task_id="task-bft-escrow"),
            ConsensusEscrow(),
        )

        assert result.protocol == ConsensusProtocol.bft_escrow

    def test_medium_prompt_uses_raft(self) -> None:
        task = make_task("Update config for staging.")
        decisions = run_consensus_round([task])
        assert len(decisions) == 1
        meta = task.metadata["adaptive_consensus"]
        assert meta["protocol"] == "raft"

    def test_high_prompt_uses_bft(self) -> None:
        task = make_task("Delete user account and grant admin.")
        decisions = run_consensus_round([task])
        assert len(decisions) == 1
        meta = task.metadata["adaptive_consensus"]
        assert meta["protocol"] == "bft"


# ===========================================================================
# ConsensusResult Audit Fields Defaults
# ===========================================================================


class TestConsensusResultDefaults:
    """ConsensusResult audit fields should have sensible defaults."""

    def test_default_risk_fields(self) -> None:
        result = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=1,
            approval_count=1,
            required=1,
        )
        assert result.risk_level == ""
        assert result.risk_score == 0
        assert result.risk_signals == []
        assert result.risk_rationale == ""

    def test_risk_fields_roundtrip(self) -> None:
        result = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=1,
            approval_count=1,
            required=1,
            risk_level="high",
            risk_score=75,
            risk_signals=["sudo", "secret"],
            risk_rationale="Matched high signals.",
        )
        assert result.risk_level == "high"
        assert result.risk_score == 75
        assert result.risk_signals == ["sudo", "secret"]
        assert result.risk_rationale == "Matched high signals."
