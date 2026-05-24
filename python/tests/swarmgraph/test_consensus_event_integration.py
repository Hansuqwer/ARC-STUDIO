"""Tests for Phase 33/R26 — Consensus Event Integration.

Tests cover:
- run_consensus_round_with_results() returns ConsensusRoundOutcome
- Old run_consensus_round() API backward compatibility
- task.metadata["consensus_result"] contains full summary
- No-result tasks get rejected consensus summary
- emit_consensus_events_for_outcomes() emits one event per outcome
- Mixed-risk tasks emit different protocols
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent_runtime_cockpit.swarmgraph.config import ConsensusProtocol, SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.consensus import ConsensusResult
from agent_runtime_cockpit.swarmgraph.consensus_escrow import ConsensusEscrow
from agent_runtime_cockpit.swarmgraph.events import SwarmGraphEventKind
from agent_runtime_cockpit.swarmgraph.models import (
    ApprovalDecision,
    SwarmTask,
    TaskStatus,
    WorkerResult,
)
from agent_runtime_cockpit.swarmgraph.nodes.consensus import (
    ConsensusRoundOutcome,
    emit_consensus_events_for_outcomes,
    run_consensus_round,
    run_consensus_round_with_results,
)
from agent_runtime_cockpit.swarmgraph.state import SwarmState

# ===========================================================================
# Helpers
# ===========================================================================


def make_task(
    prompt: str,
    task_id: str = "task-1",
    agent_id: str = "agent-1",
) -> SwarmTask:
    """Create a task with a result for consensus testing."""
    task = SwarmTask(
        id=task_id,
        prompt=prompt,
        status=TaskStatus.in_progress,
        assigned_agent_id=agent_id,
    )
    task.result = WorkerResult(
        worker_id=agent_id,
        task_id=task_id,
        output="done",
        started_at=datetime.now(timezone.utc),
    )
    return task


# ===========================================================================
# ConsensusRoundOutcome Model
# ===========================================================================


class TestConsensusRoundOutcome:
    """ConsensusRoundOutcome must exist with correct fields."""

    def test_model_exists(self) -> None:
        result = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=1,
            approval_count=1,
            required=1,
        )
        outcome = ConsensusRoundOutcome(
            task_id="task-1",
            decision=ApprovalDecision(approved=True, reason="ok", decided_by="consensus"),
            consensus_result=result,
        )
        assert outcome.task_id == "task-1"
        assert outcome.decision.approved is True
        assert outcome.consensus_result is result

    def test_model_frozen(self) -> None:
        result = ConsensusResult(
            reached=True,
            approved=True,
            total_votes=1,
            approval_count=1,
            required=1,
        )
        outcome = ConsensusRoundOutcome(
            task_id="task-1",
            decision=ApprovalDecision(approved=True, reason="ok", decided_by="consensus"),
            consensus_result=result,
        )
        with pytest.raises(Exception):
            outcome.task_id = "changed"  # type: ignore[misc]


# ===========================================================================
# run_consensus_round_with_results
# ===========================================================================


class TestRunConsensusRoundWithResults:
    """run_consensus_round_with_results() returns outcomes."""

    def test_returns_outcomes(self) -> None:
        task = make_task("Explain consensus.")
        outcomes = run_consensus_round_with_results([task])
        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome.task_id == task.id
        assert outcome.decision.approved is True
        assert outcome.consensus_result.protocol == ConsensusProtocol.majority
        assert outcome.consensus_result.risk_level == "low"

    def test_returns_outcomes_for_critical(self) -> None:
        task = make_task("Delete production database.")
        outcomes = run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome.task_id == task.id
        assert outcome.decision.approved is True
        assert outcome.consensus_result.protocol == ConsensusProtocol.bft_escrow
        assert outcome.consensus_result.risk_level == "critical"


# ===========================================================================
# Legacy API Backward Compatibility
# ===========================================================================


class TestLegacyAPI:
    """Old run_consensus_round() must still return list[ApprovalDecision]."""

    def test_legacy_api_still_returns_decisions(self) -> None:
        task = make_task("Explain consensus.")
        decisions = run_consensus_round([task])
        assert len(decisions) == 1
        assert isinstance(decisions[0], ApprovalDecision)

    def test_legacy_api_approves_low_risk(self) -> None:
        task = make_task("Explain consensus.")
        decisions = run_consensus_round([task])
        assert decisions[0].approved is True

    def test_legacy_api_critical_with_escrow(self) -> None:
        task = make_task("Delete production database.")
        decisions = run_consensus_round([task], escrow=ConsensusEscrow())
        assert len(decisions) == 1
        assert decisions[0].approved is True or decisions[0].approved is False


# ===========================================================================
# Task Metadata - consensus_result
# ===========================================================================


class TestTaskMetadataConsensusResult:
    """task.metadata["consensus_result"] must contain full summary."""

    def test_metadata_contains_consensus_result_summary(self) -> None:
        task = make_task("Delete production database.")
        run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        summary = task.metadata["consensus_result"]
        assert summary["approved"] is True
        assert summary["protocol"] == "bft_escrow"
        assert summary["risk_level"] == "critical"
        assert summary["risk_score"] >= 100
        assert summary["total_votes"] == 1
        assert summary["approval_count"] == 1
        assert summary["required"] == 1
        assert len(summary["votes"]) == 1
        assert summary["votes"][0]["agent_id"] == "agent-1"

    def test_metadata_low_risk(self) -> None:
        task = make_task("Explain consensus.")
        run_consensus_round_with_results([task])
        summary = task.metadata["consensus_result"]
        assert summary["approved"] is True
        assert summary["protocol"] == "majority"
        assert summary["risk_level"] == "low"

    def test_metadata_medium_risk(self) -> None:
        task = make_task("Update config for staging.")
        run_consensus_round_with_results([task])
        summary = task.metadata["consensus_result"]
        assert summary["approved"] is True
        assert summary["protocol"] == "raft"
        assert summary["risk_level"] == "medium"

    def test_metadata_high_risk(self) -> None:
        task = make_task("Delete user account and grant admin.")
        run_consensus_round_with_results([task])
        summary = task.metadata["consensus_result"]
        assert summary["approved"] is True
        assert summary["protocol"] == "bft"
        assert summary["risk_level"] == "high"


# ===========================================================================
# No-Result Task
# ===========================================================================


class TestNoResultTask:
    """Tasks without a result must still get a rejected consensus summary."""

    def test_no_result_task_gets_rejected_consensus_summary(self) -> None:
        task = SwarmTask(
            id="task-no-result",
            prompt="Delete production database.",
            status=TaskStatus.in_progress,
        )
        outcomes = run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        assert len(outcomes) == 1
        assert outcomes[0].decision.approved is False
        assert outcomes[0].consensus_result.approved is False

        summary = task.metadata["consensus_result"]
        assert summary["approved"] is False
        assert summary["protocol"] == "bft_escrow"
        assert summary["risk_level"] == "critical"
        assert summary["total_votes"] == 0
        assert summary["votes"] == []

    def test_no_result_task_still_has_adaptive_metadata(self) -> None:
        task = SwarmTask(
            id="task-no-result",
            prompt="Delete production database.",
            status=TaskStatus.in_progress,
        )
        run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        meta = task.metadata["adaptive_consensus"]
        assert meta["risk"] == "critical"
        assert meta["protocol"] == "bft_escrow"

    def test_no_result_task_low_risk(self) -> None:
        task = SwarmTask(
            id="task-no-result-low",
            prompt="Explain consensus.",
            status=TaskStatus.in_progress,
        )
        outcomes = run_consensus_round_with_results([task])
        assert outcomes[0].decision.approved is False
        summary = task.metadata["consensus_result"]
        assert summary["approved"] is False
        assert summary["protocol"] == "majority"
        assert summary["risk_level"] == "low"
        assert summary["total_votes"] == 0


# ===========================================================================
# Event Emission
# ===========================================================================


class TestEventEmission:
    """emit_consensus_events_for_outcomes must emit one event per outcome."""

    def test_emit_events_includes_metadata(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        task = make_task("Delete production database.")
        outcomes = run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        events = emit_consensus_events_for_outcomes(state, outcomes)
        assert len(events) == 1
        event = events[0]
        assert event.kind == SwarmGraphEventKind.consensus
        assert event.data["task_id"] == task.id
        assert event.data["protocol"] == "bft_escrow"
        assert event.data["risk"] == "critical"
        assert event.data["risk_score"] >= 100
        assert event.data["total_votes"] == 1

    def test_emit_events_low_risk(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        task = make_task("Explain consensus.")
        outcomes = run_consensus_round_with_results([task])
        events = emit_consensus_events_for_outcomes(state, outcomes)
        assert len(events) == 1
        event = events[0]
        assert event.data["protocol"] == "majority"
        assert event.data["risk"] == "low"
        assert event.data["total_votes"] == 1
        assert event.data["approval_count"] == 1

    def test_emit_events_no_result_task(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        task = SwarmTask(
            id="task-no-result",
            prompt="Delete production database.",
            status=TaskStatus.in_progress,
        )
        outcomes = run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        events = emit_consensus_events_for_outcomes(state, outcomes)
        assert len(events) == 1
        event = events[0]
        assert event.data["task_id"] == task.id
        assert event.data["approved"] is False
        assert event.data["protocol"] == "bft_escrow"
        assert event.data["risk"] == "critical"
        # No votes for no-result tasks
        assert event.data["total_votes"] == 0


# ===========================================================================
# Mixed-Risk Tasks
# ===========================================================================


class TestMixedRiskTasks:
    """Per-task mixed risks must generate different event protocols."""

    def test_mixed_task_risks_emit_different_protocols(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        low = make_task("Explain consensus.", task_id="low")
        critical = make_task("Delete production database.", task_id="critical")
        outcomes = run_consensus_round_with_results([low, critical], escrow=ConsensusEscrow())
        events = emit_consensus_events_for_outcomes(state, outcomes)
        by_task = {event.data["task_id"]: event for event in events}

        assert by_task["low"].data["protocol"] == "majority"
        assert by_task["low"].data["risk"] == "low"

        assert by_task["critical"].data["protocol"] == "bft_escrow"
        assert by_task["critical"].data["risk"] == "critical"

    def test_mixed_three_risk_levels(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        low = make_task("Explain consensus.", task_id="low")
        medium = make_task("Update config for staging.", task_id="medium")
        high = make_task("Delete user account.", task_id="high")

        outcomes = run_consensus_round_with_results([low, medium, high])
        events = emit_consensus_events_for_outcomes(state, outcomes)
        by_task = {event.data["task_id"]: event for event in events}

        assert by_task["low"].data["protocol"] == "majority"
        assert by_task["low"].data["risk"] == "low"

        assert by_task["medium"].data["protocol"] == "raft"
        assert by_task["medium"].data["risk"] == "medium"

        assert by_task["high"].data["protocol"] == "bft"
        assert by_task["high"].data["risk"] == "high"

    def test_mixed_with_no_result_task(self) -> None:
        state = SwarmState(config=SwarmGraphConfig())
        low = make_task("Explain consensus.", task_id="low")
        no_result = SwarmTask(
            id="no-result",
            prompt="Delete production database.",
            status=TaskStatus.in_progress,
        )

        outcomes = run_consensus_round_with_results([low, no_result], escrow=ConsensusEscrow())
        events = emit_consensus_events_for_outcomes(state, outcomes)
        by_task = {event.data["task_id"]: event for event in events}

        assert len(events) == 2
        assert by_task["low"].data["protocol"] == "majority"
        assert by_task["low"].data["approved"] is True

        assert by_task["no-result"].data["protocol"] == "bft_escrow"
        assert by_task["no-result"].data["approved"] is False
        assert by_task["no-result"].data["total_votes"] == 0


# ===========================================================================
# JSON-Safe Metadata
# ===========================================================================


class TestJsonSafeMetadata:
    """consensus_result metadata must be JSON-serializable."""

    def test_metadata_is_json_serializable(self) -> None:
        import json

        task = make_task("Explain consensus.")
        run_consensus_round_with_results([task])
        summary = task.metadata["consensus_result"]

        # Should not raise
        serialized = json.dumps(summary, ensure_ascii=False)
        assert isinstance(serialized, str)

        # Verify round-trip
        parsed = json.loads(serialized)
        assert parsed["approved"] is True
        assert parsed["protocol"] == "majority"
        assert parsed["risk_level"] == "low"

    def test_metadata_votes_json_serializable(self) -> None:
        import json

        task = make_task("Delete production database.", agent_id="agent-42")
        run_consensus_round_with_results([task], escrow=ConsensusEscrow())
        summary = task.metadata["consensus_result"]

        serialized = json.dumps(summary, ensure_ascii=False)
        parsed = json.loads(serialized)

        assert len(parsed["votes"]) == 1
        assert parsed["votes"][0]["agent_id"] == "agent-42"
        assert parsed["votes"][0]["approved"] is True
        # timestamp should be an ISO format string
        assert "T" in parsed["votes"][0]["timestamp"]
