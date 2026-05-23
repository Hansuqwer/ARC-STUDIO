"""Phase 31/R24 — Adaptive Consensus Protocol node.
Phase 32/R25 — Hardened: per-task selection, immutable-safe audit fields,
persistent metadata on tasks, event-compatible risk data.

Routes each task's consensus request through the deterministic risk assessor
to select the appropriate protocol. Critical-risk tasks use BFT + escrow.
"""

from __future__ import annotations

from ..config import ConsensusProtocol
from ..consensus import ConsensusResult, run_consensus
from ..consensus_escrow import ConsensusEscrow
from ..models import AgentVote, ApprovalDecision, SwarmTask, TaskStatus
from ..risk_assessment import ProtocolSelection, select_consensus_protocol


def run_consensus_round(
    tasks: list[SwarmTask],
    protocol: str = "majority",
    quorum: int | None = None,
    prompt: str | None = None,
    escrow: ConsensusEscrow | None = None,
) -> list[ApprovalDecision]:
    """Run adaptive consensus on a list of tasks.

    When ``prompt`` is explicitly provided, it is used as the shared prompt
    for all tasks. Otherwise each task uses its own ``task.prompt`` for
    per-task adaptive protocol selection.

    When ``prompt`` is None and no task prompts match any risk signals,
    the legacy ``protocol`` parameter is used as a fallback.

    Args:
        tasks: List of swarm tasks to reach consensus on.
        protocol: Fallback protocol (used when no adaptive selection occurs).
        quorum: Optional quorum size for quorum-based protocols.
        prompt: Optional shared prompt override. If None, per-task prompts used.
        escrow: Optional ConsensusEscrow instance for bft_escrow path.

    Returns:
        List of ApprovalDecision (one per task).
    """
    _ = ConsensusProtocol(protocol) if isinstance(protocol, str) else protocol  # noqa: F841 - kept for legacy compat

    decisions: list[ApprovalDecision] = []
    for task in tasks:
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
            decisions.append(
                ApprovalDecision(
                    approved=False,
                    reason="no result to approve",
                    decided_by="system",
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
        decisions.append(decision)

    return decisions


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
