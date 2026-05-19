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


CONSENSUS_FUNCS = {
    ConsensusProtocol.majority: majority_consensus,
    ConsensusProtocol.quorum: quorum_consensus,
}


def run_consensus(
    votes: list[AgentVote],
    protocol: ConsensusProtocol = ConsensusProtocol.majority,
    quorum: int | None = None,
) -> ConsensusResult:
    func = CONSENSUS_FUNCS.get(protocol, majority_consensus)
    if protocol == ConsensusProtocol.quorum and quorum is not None:
        return quorum_consensus(votes, quorum=quorum)
    return func(votes, quorum=quorum)
