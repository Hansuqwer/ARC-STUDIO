"""Phase 31/R24 — Adaptive Consensus Protocol node.
Phase 32/R25 — Hardened: per-task selection, immutable-safe audit fields,
persistent metadata on tasks, event-compatible risk data.
Phase 33/R26 — Consensus Event Integration: ConsensusRoundOutcome model,
run_consensus_round_with_results(), consensus_result_to_metadata(), and
emit_consensus_events_for_outcomes().

Routes each task's consensus request through the deterministic risk assessor
to select the appropriate protocol. Critical-risk tasks use BFT + escrow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from ..config import ConsensusProtocol
from ..consensus import ConsensusResult, run_consensus
from ..consensus_escrow import ConsensusEscrow
from ..models import AgentVote, ApprovalDecision, SwarmTask, TaskStatus
from ..risk_assessment import ProtocolSelection, select_consensus_protocol

if TYPE_CHECKING:
    from ..events import ConsensusEvent
    from ..state import SwarmState


# ---------------------------------------------------------------------------
# Phase 33/R26 — ConsensusRoundOutcome
# ---------------------------------------------------------------------------


class ConsensusRoundOutcome(BaseModel):
    """Outcome of a single consensus round for one task.

    Preserves both the ApprovalDecision (for legacy callers) and the full
    ConsensusResult (for event emission and metadata persistence).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    decision: ApprovalDecision
    consensus_result: ConsensusResult


# ---------------------------------------------------------------------------
# JSON-safe consensus result summary helper
# ---------------------------------------------------------------------------


def consensus_result_to_metadata(result: ConsensusResult) -> dict[str, object]:
    """Convert a ConsensusResult into a JSON-safe dict for task metadata.

    Args:
        result: The consensus result to convert.

    Returns:
        A plain dict suitable for storage in task.metadata.

    """
    return {
        "reached": result.reached,
        "approved": result.approved,
        "total_votes": result.total_votes,
        "approval_count": result.approval_count,
        "rejection_count": result.rejection_count,
        "required": result.required,
        "protocol": result.protocol.value,
        "details": result.details,
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "risk_signals": list(result.risk_signals),
        "risk_rationale": result.risk_rationale,
        "votes": [
            {
                "agent_id": vote.agent_id,
                "task_id": vote.task_id,
                "round": vote.round,
                "approved": vote.approved,
                "confidence": vote.confidence,
                "reasoning": vote.reasoning,
                "timestamp": vote.timestamp.isoformat(),
            }
            for vote in result.votes
        ],
    }


# ---------------------------------------------------------------------------
# Phase 33/R26 — Event emission helper
# ---------------------------------------------------------------------------


def emit_consensus_events_for_outcomes(
    state: SwarmState,
    outcomes: list[ConsensusRoundOutcome],
) -> list[ConsensusEvent]:
    """Emit one ConsensusEvent per outcome.

    Args:
        state: Current swarm state.
        outcomes: List of consensus round outcomes.

    Returns:
        List of ConsensusEvent instances.

    """
    from ..events import emit_consensus_event

    return [
        emit_consensus_event(
            state,
            task_id=outcome.task_id,
            approval=outcome.decision,
            consensus_result=outcome.consensus_result,
        )
        for outcome in outcomes
    ]


# ---------------------------------------------------------------------------
# Phase 33/R26 — run_consensus_round_with_results
# ---------------------------------------------------------------------------


def run_consensus_round_with_results(
    tasks: list[SwarmTask],
    protocol: str = "majority",
    quorum: int | None = None,
    prompt: str | None = None,
    escrow: ConsensusEscrow | None = None,
) -> list[ConsensusRoundOutcome]:
    """Run adaptive consensus on a list of tasks and return full outcomes.

    Same logic as run_consensus_round(), but returns ConsensusRoundOutcome
    instances that include both the ApprovalDecision and the ConsensusResult.
    Also persists ``task.metadata["consensus_result"]`` for each task.

    When ``prompt`` is explicitly provided, it is used as the shared prompt
    for all tasks. Otherwise each task uses its own ``task.prompt`` for
    per-task adaptive protocol selection.

    The legacy ``protocol`` parameter is retained for API compatibility and
    validation, but adaptive selection chooses the protocol for each task.

    Args:
        tasks: List of swarm tasks to reach consensus on.
        protocol: Legacy protocol value retained for API compatibility.
        quorum: Optional quorum size for quorum-based protocols.
        prompt: Optional shared prompt override. If None, per-task prompts used.
        escrow: Optional ConsensusEscrow instance for bft_escrow path.

    Returns:
        List of ConsensusRoundOutcome (one per task).

    """
    _legacy_protocol = ConsensusProtocol(protocol) if isinstance(protocol, str) else protocol

    outcomes: list[ConsensusRoundOutcome] = []
    grouped: dict[str, list[SwarmTask]] = {}
    for task in tasks:
        group_id = task.metadata.get("consensus_group")
        if isinstance(group_id, str) and group_id:
            grouped.setdefault(group_id, []).append(task)

    grouped_task_ids: set[str] = set()
    for group_tasks in grouped.values():
        if len(group_tasks) <= 1:
            continue
        outcomes.extend(
            _run_group_consensus_round(
                group_tasks,
                quorum=quorum,
                prompt=prompt,
                escrow=escrow,
            )
        )
        grouped_task_ids.update(task.id for task in group_tasks)

    for task in tasks:
        if task.id in grouped_task_ids:
            continue
        # Determine selection prompt: explicit shared prompt or per-task prompt
        selection_prompt = prompt if prompt is not None else task.prompt
        selection = select_consensus_protocol(selection_prompt)
        proto = selection.protocol

        # Persist selection in task metadata
        task.metadata["adaptive_consensus"] = {
            "risk": selection.risk,
            "protocol": selection.protocol.value,
            "score": selection.assessment.score,
            "matched_signals": list(selection.assessment.matched_signals),
            "rationale": selection.assessment.rationale,
        }

        if task.result is None or task.result.error:
            # No-result path: create a rejected consensus result
            consensus = ConsensusResult(
                reached=False,
                approved=False,
                total_votes=0,
                approval_count=0,
                rejection_count=0,
                required=1,
                protocol=proto,
                details="no result to approve",
                risk_level=selection.risk,
                risk_score=selection.assessment.score,
                risk_signals=list(selection.assessment.matched_signals),
                risk_rationale=selection.assessment.rationale,
            )
            task.metadata["consensus_result"] = consensus_result_to_metadata(consensus)
            decision = ApprovalDecision(
                approved=False,
                reason="no result to approve",
                decided_by="system",
            )
            outcomes.append(
                ConsensusRoundOutcome(
                    task_id=task.id,
                    decision=decision,
                    consensus_result=consensus,
                )
            )
            continue

        votes: list[AgentVote] = []
        if task.approval is None:
            vote = AgentVote(
                agent_id=task.assigned_agent_id or "system",
                task_id=task.id,
                round=0,
                approved=True,
                confidence=1.0,
                reasoning="result present",
            )
            votes.append(vote)

        # Run consensus (with escrow for bft_escrow protocol)
        if proto == ConsensusProtocol.bft_escrow and escrow is not None:
            consensus = _run_bft_escrow_consensus(votes, task, escrow, quorum)
        else:
            consensus = run_consensus(votes, protocol=proto, quorum=quorum)

        # Attach risk assessment audit fields via immutable-safe copy
        consensus = consensus.model_copy(
            update={
                "risk_level": selection.risk,
                "risk_score": selection.assessment.score,
                "risk_signals": list(selection.assessment.matched_signals),
                "risk_rationale": selection.assessment.rationale,
            }
        )

        task.votes = votes

        # Persist full consensus result summary in task metadata
        task.metadata["consensus_result"] = consensus_result_to_metadata(consensus)

        if consensus.reached:
            decision = ApprovalDecision(
                approved=True,
                reason=_format_decision_reason(consensus, selection),
                decided_by="consensus",
            )
            task.status = TaskStatus.completed
        else:
            decision = ApprovalDecision(
                approved=False,
                reason=_format_decision_reason(consensus, selection),
                decided_by="consensus",
            )
            task.status = TaskStatus.failed

        task.approval = decision
        outcomes.append(
            ConsensusRoundOutcome(
                task_id=task.id,
                decision=decision,
                consensus_result=consensus,
            )
        )

    return outcomes


def _worker_confidence(task: SwarmTask) -> tuple[float, str]:
    """Derive a deterministic per-worker vote confidence and reasoning.

    Confidence is computed from observable worker-result signals rather than a
    fixed 1.0, so confidence-weighted/quorum protocols can differentiate strong
    and weak worker outputs:

    - Missing result or error -> 0.0 (no confidence, vote is a rejection).
    - Empty output -> low confidence (0.2).
    - Otherwise scale by output substance (length) and presence of artifacts,
      clamped to [0.3, 1.0].

    The computation is pure and order-independent, preserving determinism.
    """
    result = task.result
    if result is None:
        return 0.0, "missing worker result"
    if result.error:
        return 0.0, f"worker error: {result.error[:120]}"

    output = result.output or ""
    if not output.strip():
        return 0.2, "worker result present but empty output"

    # Length signal: saturates around ~400 chars of substance.
    length_signal = min(1.0, len(output.strip()) / 400.0)
    artifact_bonus = 0.1 if result.artifacts else 0.0
    confidence = round(min(1.0, max(0.3, 0.3 + 0.6 * length_signal + artifact_bonus)), 4)
    reasoning = (
        f"worker result present (len={len(output.strip())}, "
        f"artifacts={len(result.artifacts)}, confidence={confidence})"
    )
    return confidence, reasoning


def _run_group_consensus_round(
    tasks: list[SwarmTask],
    quorum: int | None = None,
    prompt: str | None = None,
    escrow: ConsensusEscrow | None = None,
) -> list[ConsensusRoundOutcome]:
    group_prompt = prompt or str(tasks[0].metadata.get("consensus_prompt") or tasks[0].prompt)
    selection = select_consensus_protocol(group_prompt)
    proto = selection.protocol

    votes: list[AgentVote] = []
    for task in tasks:
        confidence, reasoning = _worker_confidence(task)
        votes.append(
            AgentVote(
                agent_id=task.assigned_agent_id
                or (task.result.worker_id if task.result else "system"),
                task_id=tasks[0].id,
                round=0,
                approved=task.result is not None and task.result.error is None,
                confidence=confidence,
                reasoning=reasoning,
            )
        )

    if proto == ConsensusProtocol.bft_escrow and escrow is not None:
        consensus = _run_bft_escrow_consensus(votes, tasks[0], escrow, quorum)
    else:
        consensus = run_consensus(votes, protocol=proto, quorum=quorum)

    consensus = consensus.model_copy(
        update={
            "risk_level": selection.risk,
            "risk_score": selection.assessment.score,
            "risk_signals": list(selection.assessment.matched_signals),
            "risk_rationale": selection.assessment.rationale,
        }
    )

    decision = ApprovalDecision(
        approved=consensus.approved,
        reason=_format_decision_reason(consensus, selection),
        decided_by="consensus",
    )

    approving = [v.confidence for v in votes if v.approved]
    mean_confidence = round(sum(approving) / len(approving), 4) if approving else 0.0
    weighted_total = sum(v.confidence for v in votes)
    weighted_ratio = (
        round(sum(v.confidence for v in votes if v.approved) / weighted_total, 4)
        if weighted_total > 0
        else 0.0
    )

    outcomes: list[ConsensusRoundOutcome] = []
    summary = consensus_result_to_metadata(consensus)
    for task in tasks:
        task.votes = list(votes)
        task.metadata["adaptive_consensus"] = {
            "risk": selection.risk,
            "protocol": selection.protocol.value,
            "score": selection.assessment.score,
            "matched_signals": list(selection.assessment.matched_signals),
            "rationale": selection.assessment.rationale,
            "grouped_votes": len(votes),
            "mean_approval_confidence": mean_confidence,
            "weighted_approval_ratio": weighted_ratio,
        }
        task.metadata["consensus_result"] = summary
        task.approval = decision
        task.status = (
            TaskStatus.completed
            if consensus.approved and task.result is not None and task.result.error is None
            else TaskStatus.failed
        )
        outcomes.append(
            ConsensusRoundOutcome(
                task_id=task.id,
                decision=decision,
                consensus_result=consensus,
            )
        )
    return outcomes


# ---------------------------------------------------------------------------
# Phase 33/R26 — Legacy run_consensus_round wrapper
# ---------------------------------------------------------------------------


def run_consensus_round(
    tasks: list[SwarmTask],
    protocol: str = "majority",
    quorum: int | None = None,
    prompt: str | None = None,
    escrow: ConsensusEscrow | None = None,
) -> list[ApprovalDecision]:
    """Run adaptive consensus on a list of tasks.

    Legacy API: delegates to run_consensus_round_with_results() and returns
    only ApprovalDecision instances. New code should prefer
    run_consensus_round_with_results() for full outcome data.

    When ``prompt`` is explicitly provided, it is used as the shared prompt
    for all tasks. Otherwise each task uses its own ``task.prompt`` for
    per-task adaptive protocol selection.

    The legacy ``protocol`` parameter is retained for API compatibility and
    validation, but adaptive selection chooses the protocol for each task.

    Args:
        tasks: List of swarm tasks to reach consensus on.
        protocol: Legacy protocol value retained for API compatibility.
        quorum: Optional quorum size for quorum-based protocols.
        prompt: Optional shared prompt override. If None, per-task prompts used.
        escrow: Optional ConsensusEscrow instance for bft_escrow path.

    Returns:
        List of ApprovalDecision (one per task).

    """
    outcomes = run_consensus_round_with_results(
        tasks,
        protocol=protocol,
        quorum=quorum,
        prompt=prompt,
        escrow=escrow,
    )
    return [outcome.decision for outcome in outcomes]


def _run_bft_escrow_consensus(
    votes: list[AgentVote],
    task: SwarmTask,
    escrow: ConsensusEscrow,
    quorum: int | None = None,
) -> ConsensusResult:
    """Run BFT consensus wrapped with escrow commit-reveal.

    Generates per-vote nonces, commits each vote to escrow, reveals and
    verifies, then tallies. Clears commits after completion.
    """
    from ..consensus_escrow import _generate_nonce

    revealed_votes = []
    for vote in votes:
        nonce = _generate_nonce()
        commit = escrow.commit(vote, nonce=nonce)
        revealed = escrow.reveal(vote, nonce=nonce, commit=commit)
        if escrow.verify(revealed):
            revealed_votes.append(revealed)

    consensus = escrow.tally(revealed_votes, protocol=ConsensusProtocol.bft, quorum=quorum)
    consensus = consensus.model_copy(update={"protocol": ConsensusProtocol.bft_escrow})

    escrow.clear_commits()

    return consensus


def _format_decision_reason(
    result: ConsensusResult,
    selection: ProtocolSelection | None,
) -> str:
    """Build a decision reason string that includes risk assessment context."""
    parts = [result.details]
    if selection is not None:
        parts.append(
            f"risk={selection.risk}(score={selection.assessment.score})"
            f" protocol={selection.protocol.value}"
        )
    return " | ".join(parts)
