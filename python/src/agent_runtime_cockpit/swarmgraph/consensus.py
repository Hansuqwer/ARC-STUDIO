from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .config import ConsensusProtocol
from .models import AgentVote


class ConsensusResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reached: bool
    approved: bool
    total_votes: int = Field(default=0, ge=0)
    approval_count: int = Field(default=0, ge=0)
    rejection_count: int = Field(default=0, ge=0)
    required: int = Field(default=0, ge=0)
    protocol: ConsensusProtocol = Field(default=ConsensusProtocol.majority)
    details: str = Field(default="", max_length=2048)
    votes: list[AgentVote] = Field(default_factory=list)

    # Phase 31/R24 — Adaptive Consensus Protocol audit fields
    risk_level: str = Field(default="", max_length=16)
    risk_score: int = Field(default=0, ge=0)
    risk_signals: list[str] = Field(default_factory=list, max_length=64)
    risk_rationale: str = Field(default="", max_length=4096)


def majority_consensus(
    votes: list[AgentVote],
    quorum: int | None = None,
) -> ConsensusResult:
    total = len(votes)
    if total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=quorum or 1,
            protocol=ConsensusProtocol.majority,
            details="no votes cast",
        )
    approved_count = sum(1 for v in votes if v.approved)
    rejected_count = total - approved_count
    required = quorum if quorum is not None else (total // 2 + 1)
    reached = approved_count >= required
    details = (
        f"majority: {approved_count}/{required} required, {approved_count}/{total} approved"
        if reached
        else f"not reached: {approved_count}/{required} required, {approved_count}/{total} approved"
    )
    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=approved_count,
        rejection_count=rejected_count,
        required=required,
        protocol=ConsensusProtocol.majority,
        details=details,
        votes=votes,
    )


def quorum_consensus(
    votes: list[AgentVote],
    quorum: int = 2,
) -> ConsensusResult:
    total = len(votes)
    if total < quorum:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=total,
            required=quorum,
            protocol=ConsensusProtocol.quorum,
            details=f"quorum not met: {total}/{quorum} voted",
        )
    approved_count = sum(1 for v in votes if v.approved)
    rejected_count = total - approved_count
    reached = approved_count >= quorum
    details = (
        f"quorum reached: {approved_count}/{quorum} approved"
        if reached
        else f"quorum not met: {approved_count}/{quorum} approved"
    )
    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=approved_count,
        rejection_count=rejected_count,
        required=quorum,
        protocol=ConsensusProtocol.quorum,
        details=details,
        votes=votes,
    )


def raft_consensus(
    votes: list[AgentVote],
    quorum: int | None = None,
) -> ConsensusResult:
    """Deterministic raft-style leader-based consensus.

    The leader is deterministically chosen as the agent with the lowest
    (lexicographically sorted) agent_id. The leader's vote decides approval.
    All votes are counted for the record.

    Args:
        votes: Agent votes to process.
        quorum: Ignored for raft; leader decides.

    Returns:
        ConsensusResult with raft protocol.
    """
    total = len(votes)
    if total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=1,
            protocol=ConsensusProtocol.raft,
            details="raft: no leader vote available",
        )

    leader_vote = sorted(votes, key=lambda v: v.agent_id)[0]
    approved_count = sum(1 for v in votes if v.approved)
    rejected_count = total - approved_count

    return ConsensusResult(
        reached=True,
        approved=leader_vote.approved,
        total_votes=total,
        approval_count=approved_count,
        rejection_count=rejected_count,
        required=1,
        protocol=ConsensusProtocol.raft,
        details=(
            f"raft: leader={leader_vote.agent_id} "
            f"approved={leader_vote.approved}, "
            f"{approved_count}/{total} approved"
        ),
        votes=votes,
    )


def bft_consensus(
    votes: list[AgentVote],
    quorum: int | None = None,
) -> ConsensusResult:
    """Deterministic Byzantine Fault Tolerant consensus.

    Requires at least 2/3 supermajority approval. Uses integer math to
    avoid floating-point precision issues.

    Args:
        votes: Agent votes to process.
        quorum: Optional explicit quorum override.

    Returns:
        ConsensusResult with bft protocol.
    """
    total = len(votes)
    required = quorum if quorum is not None else max(1, (2 * total + 2) // 3)

    if total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=required,
            protocol=ConsensusProtocol.bft,
            details=f"bft: no votes cast, {required} required",
        )

    approved_count = sum(1 for v in votes if v.approved)
    rejected_count = total - approved_count
    reached = approved_count >= required

    details = (
        f"bft: {approved_count}/{required} required, {approved_count}/{total} approved"
        if reached
        else (
            f"bft not reached: {approved_count}/{required} required, "
            f"{approved_count}/{total} approved"
        )
    )

    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=approved_count,
        rejection_count=rejected_count,
        required=required,
        protocol=ConsensusProtocol.bft,
        details=details,
        votes=votes,
    )


CONSENSUS_FUNCS = {
    ConsensusProtocol.majority: majority_consensus,
    ConsensusProtocol.quorum: quorum_consensus,
    ConsensusProtocol.raft: raft_consensus,
    ConsensusProtocol.bft: bft_consensus,
    ConsensusProtocol.bft_escrow: bft_consensus,
}


def run_consensus(
    votes: list[AgentVote],
    protocol: ConsensusProtocol = ConsensusProtocol.majority,
    quorum: int | None = None,
) -> ConsensusResult:
    """Run consensus using the specified protocol.

    Dispatches to the appropriate consensus function. For bft_escrow,
    the protocol field is set to bft_escrow (not bft) to distinguish
    the escrow-wrapped path.

    Args:
        votes: Agent votes to process.
        protocol: Which consensus protocol to use.
        quorum: Optional quorum override.

    Returns:
        ConsensusResult with the selected protocol.
    """
    func = CONSENSUS_FUNCS.get(protocol, majority_consensus)

    if protocol == ConsensusProtocol.quorum and quorum is not None:
        return quorum_consensus(votes, quorum=quorum)

    if protocol in (ConsensusProtocol.bft, ConsensusProtocol.bft_escrow):
        result = bft_consensus(votes, quorum=quorum)
        if protocol == ConsensusProtocol.bft_escrow:
            return result.model_copy(update={"protocol": ConsensusProtocol.bft_escrow})
        return result

    return func(votes, quorum=quorum)
