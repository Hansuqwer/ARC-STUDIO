from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .config import ConsensusProtocol
from .models import AgentVote, WorkerResult


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


def selective_debate_consensus(
    votes: list[AgentVote],
    candidates: list[WorkerResult] | None = None,
    top_k: int = 2,
    quorum: int | None = None,
) -> ConsensusResult:
    """Two-round selective debate consensus.

    First round tallies votes on candidates. Top-k candidates by approval
    proceed to the second round. Second round votes are cast only on
    top-k survivors.

    If only 1 round or top_k >= total, falls back to majority.

    Args:
        votes: Agent votes (first round only).
        candidates: Worker results for candidate ranking.
        top_k: Number of top candidates to advance.

    Returns:
        ConsensusResult with protocol='selective_debate'.

    """
    total = len(votes)
    if total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=1,
            protocol=ConsensusProtocol.selective_debate,
            details="selective_debate: no votes cast",
        )

    if candidates is None or top_k >= len(candidates) or top_k <= 1:
        # Fallback to simple majority
        approved_count = sum(1 for v in votes if v.approved)
        rejected_count = total - approved_count
        required = total // 2 + 1
        reached = approved_count >= required
        return ConsensusResult(
            reached=reached,
            approved=reached,
            total_votes=total,
            approval_count=approved_count,
            rejection_count=rejected_count,
            required=required,
            protocol=ConsensusProtocol.selective_debate,
            details=(
                f"selective_debate (fallback majority): {approved_count}/{required} required, "
                f"{approved_count}/{total} approved"
            ),
            votes=votes,
        )

    # Round 1: tally votes per candidate
    candidate_approvals: dict[str, int] = {}
    for v in votes:
        candidate_approvals[v.agent_id] = candidate_approvals.get(v.agent_id, 0) + (
            1 if v.approved else 0
        )

    # Sort candidates by approval count, take top_k
    sorted_candidates = sorted(candidate_approvals.items(), key=lambda x: -x[1])
    survivors = [cid for cid, _ in sorted_candidates[:top_k]]

    # Round 2: only votes on survivors count
    round2_votes = [v for v in votes if v.agent_id in survivors]
    round2_total = len(round2_votes)
    if round2_total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=total,
            required=top_k,
            protocol=ConsensusProtocol.selective_debate,
            details="selective_debate: no survivors in round 2",
            votes=votes,
        )

    round2_approved = sum(1 for v in round2_votes if v.approved)
    round2_required = round2_total // 2 + 1
    reached = round2_approved >= round2_required

    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=round2_approved,
        rejection_count=round2_total - round2_approved,
        required=round2_required,
        protocol=ConsensusProtocol.selective_debate,
        details=(
            f"selective_debate: round1 candidates={len(candidates)}, top_k={top_k}, "
            f"survivors={survivors}, round2 {round2_approved}/{round2_required} required"
        ),
        votes=votes,
    )


def confidence_weighted_consensus(
    votes: list[AgentVote],
    quorum: int | None = None,
    threshold: float = 0.5,
) -> ConsensusResult:
    """Confidence-weighted quorum consensus.

    Uses each vote's confidence (0-1) to weight the approval tally.
    Computes weighted approval ratio: sum(confidence where approved) /
    sum(all confidence). If >= threshold, passes.

    If no confidence values are set (all 0 or all 1), falls back to majority.

    Args:
        votes: Agent votes with confidence values.
        quorum: Optional minimum vote count quorum.
        threshold: Weighted approval ratio threshold (default 0.5).

    Returns:
        ConsensusResult with protocol='confidence_weighted'.

    """
    total = len(votes)
    if total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=1,
            protocol=ConsensusProtocol.confidence_weighted,
            details="confidence_weighted: no votes cast",
        )

    # Check if confidence is meaningful (not all 0 or all 1)
    confidences = [v.confidence for v in votes]
    all_default = all(c == 0.0 for c in confidences) or all(c == 1.0 for c in confidences)

    if all_default:
        # Fallback to simple majority
        approved_count = sum(1 for v in votes if v.approved)
        rejected_count = total - approved_count
        required = quorum if quorum is not None else (total // 2 + 1)
        reached = approved_count >= required
        return ConsensusResult(
            reached=reached,
            approved=reached,
            total_votes=total,
            approval_count=approved_count,
            rejection_count=rejected_count,
            required=required,
            protocol=ConsensusProtocol.confidence_weighted,
            details=(
                f"confidence_weighted (fallback majority): {approved_count}/{required} required, "
                f"{approved_count}/{total} approved"
            ),
            votes=votes,
        )

    weighted_approval = sum(v.confidence for v in votes if v.approved)
    weighted_total = sum(v.confidence for v in votes)

    if weighted_total == 0:
        # All zero confidence with approval=False — edge case
        approved_count = sum(1 for v in votes if v.approved)
        rejected_count = total - approved_count
        required = quorum if quorum is not None else (total // 2 + 1)
        reached = approved_count >= required
        return ConsensusResult(
            reached=reached,
            approved=reached,
            total_votes=total,
            approval_count=approved_count,
            rejection_count=rejected_count,
            required=required,
            protocol=ConsensusProtocol.confidence_weighted,
            details=(
                f"confidence_weighted (zero-weighted fallback): {approved_count}/{required} required, "
                f"{approved_count}/{total} approved"
            ),
            votes=votes,
        )

    ratio = weighted_approval / weighted_total
    reached = ratio >= threshold

    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=sum(1 for v in votes if v.approved),
        rejection_count=sum(1 for v in votes if not v.approved),
        required=1,
        protocol=ConsensusProtocol.confidence_weighted,
        details=(
            f"confidence_weighted: weighted_approval={weighted_approval:.4f}, "
            f"weighted_total={weighted_total:.4f}, ratio={ratio:.4f}, "
            f"threshold={threshold}, reached={reached}"
        ),
        votes=votes,
    )


def critic_verifier_consensus(
    votes: list[AgentVote],
    verifier_votes: list[AgentVote] | None = None,
    verifier_multiplier: float = 2.0,
    quorum: int | None = None,
) -> ConsensusResult:
    """Critic/verifier lane consensus.

    Verifier votes get multiplied weight. Combined tally checks:
    - If verifiers approve (weighted majority), then check worker majority.
    - Empty verifier list is handled gracefully (worker majority only).

    Args:
        votes: Regular worker votes.
        verifier_votes: Critic/model verifier votes.
        verifier_multiplier: Weight multiplier for verifier votes (default 2.0).
        quorum: Optional minimum vote count quorum.

    Returns:
        ConsensusResult with protocol='critic_verifier'.

    """
    total = len(votes)
    verifier_total = len(verifier_votes) if verifier_votes else 0

    if total == 0 and verifier_total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=1,
            protocol=ConsensusProtocol.critic_verifier,
            details="critic_verifier: no votes and no verifier votes",
        )

    # If no verifier votes, fall back to worker majority
    if verifier_total == 0:
        approved_count = sum(1 for v in votes if v.approved)
        rejected_count = total - approved_count
        required = quorum if quorum is not None else (total // 2 + 1)
        reached = approved_count >= required
        return ConsensusResult(
            reached=reached,
            approved=reached,
            total_votes=total,
            approval_count=approved_count,
            rejection_count=rejected_count,
            required=required,
            protocol=ConsensusProtocol.critic_verifier,
            details=(
                f"critic_verifier (no verifiers): {approved_count}/{required} required, "
                f"{approved_count}/{total} approved"
            ),
            votes=votes,
        )

    # Verifier weighted tally
    verifier_approved_weight = sum(verifier_multiplier for v in verifier_votes if v.approved)
    verifier_total_weight = sum(verifier_multiplier for _ in verifier_votes)
    verifier_ratio = (
        verifier_approved_weight / verifier_total_weight if verifier_total_weight > 0 else 0.0
    )

    # Worker majority
    worker_approved = sum(1 for v in votes if v.approved)
    worker_required = quorum if quorum is not None else (total // 2 + 1)
    worker_reached = worker_approved >= worker_required

    # Verifier must approve (ratio > 0.5) and workers must reach majority
    verifier_approves = verifier_ratio > 0.5
    reached = verifier_approves and worker_reached if total > 0 else verifier_approves

    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=worker_approved,
        rejection_count=total - worker_approved,
        required=worker_required,
        protocol=ConsensusProtocol.critic_verifier,
        details=(
            f"critic_verifier: verifier_ratio={verifier_ratio:.2f} "
            f"({'approves' if verifier_approves else 'rejects'}), "
            f"workers={worker_approved}/{worker_required} "
            f"({'reached' if worker_reached else 'not reached'}), "
            f"combined={'reached' if reached else 'not reached'}"
        ),
        votes=votes,
    )


def hitl_signoff_quorum(
    votes: list[AgentVote],
    prompts: list[dict] | None = None,
    operators_required: int = 1,
    quorum: int | None = None,
) -> ConsensusResult:
    """Human-in-the-loop sign-off quorum.

    Checks operator responses from HITL prompt dicts. Each dict should have
    at least 'operator_id' and 'approved' keys.

    Args:
        votes: Agent votes (for record keeping).
        prompts: List of HITL prompt dicts with operator responses.
        operators_required: Minimum distinct operators needed (default 1).

    Returns:
        ConsensusResult with protocol='hitl_signoff'.

    """
    total = len(votes)
    prompts = prompts or []

    if not prompts:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=total,
            required=operators_required,
            protocol=ConsensusProtocol.hitl_signoff,
            details="hitl_signoff: no operator responses collected",
            votes=votes,
        )

    # Collect distinct operator responses
    operator_responses: dict[str, bool] = {}
    for p in prompts:
        op_id = p.get("operator_id", "")
        op_approved = p.get("approved", False)
        if op_id:
            # Last response wins for each operator
            operator_responses[op_id] = op_approved

    distinct_operators = len(operator_responses)
    approved_operators = sum(1 for v in operator_responses.values() if v)
    reached = distinct_operators >= operators_required and approved_operators >= operators_required

    operator_details = ", ".join(
        f"{oid}:{'approved' if ok else 'rejected'}" for oid, ok in operator_responses.items()
    )

    return ConsensusResult(
        reached=reached,
        approved=reached,
        total_votes=total,
        approval_count=approved_operators,
        rejection_count=distinct_operators - approved_operators,
        required=operators_required,
        protocol=ConsensusProtocol.hitl_signoff,
        details=(
            f"hitl_signoff: {approved_operators}/{operators_required} operators "
            f"required, {distinct_operators} responded [{operator_details}]"
        ),
        votes=votes,
    )


def gossip_consensus(
    votes: list[AgentVote],
    quorum: int | None = None,
    max_rounds: int = 3,
) -> ConsensusResult:
    """Gossip protocol simulating eventual consensus.

    All votes are collected. If >50% agree after N simulation rounds,
    consensus is reached. Uses deterministic simulation: each round
    spreads the majority opinion.

    Args:
        votes: Agent votes to process.
        quorum: Ignored; uses >50% threshold.
        max_rounds: Maximum gossip rounds (default 3).

    Returns:
        ConsensusResult with protocol='gossip'.

    """
    total = len(votes)
    if total == 0:
        return ConsensusResult(
            reached=False,
            approved=False,
            total_votes=0,
            required=1,
            protocol=ConsensusProtocol.gossip,
            details="gossip: no votes cast",
        )

    approved_count = sum(1 for v in votes if v.approved)
    rejected_count = total - approved_count
    threshold = total // 2 + 1

    # Round 0: initial tally
    if approved_count >= threshold:
        return ConsensusResult(
            reached=True,
            approved=True,
            total_votes=total,
            approval_count=approved_count,
            rejection_count=rejected_count,
            required=threshold,
            protocol=ConsensusProtocol.gossip,
            details=f"gossip: reached in round 0, {approved_count}/{total} approve",
            votes=votes,
        )

    if rejected_count >= threshold:
        return ConsensusResult(
            reached=True,
            approved=False,
            total_votes=total,
            approval_count=approved_count,
            rejection_count=rejected_count,
            required=threshold,
            protocol=ConsensusProtocol.gossip,
            details=f"gossip: reached (rejected) in round 0, {rejected_count}/{total} reject",
            votes=votes,
        )

    # Simulate gossip rounds: majority opinion spreads
    approve = approved_count
    reject = rejected_count
    for round_num in range(1, max_rounds + 1):
        # Each round, sway some undecided toward the current leader
        # Ties sway toward approval
        if approve > reject or (approve == reject and round_num % 2 == 1):
            # Approval is winning — sway some reject to approve
            sway = max(1, (reject * (round_num)) // (max_rounds + 1))
            approve += min(sway, reject)
            reject -= min(sway, reject)
        elif reject > approve or (approve == reject and round_num % 2 == 0):
            sway = max(1, (approve * (round_num)) // (max_rounds + 1))
            reject += min(sway, approve)
            approve -= min(sway, approve)

        if approve >= threshold:
            return ConsensusResult(
                reached=True,
                approved=True,
                total_votes=total,
                approval_count=approved_count,
                rejection_count=rejected_count,
                required=threshold,
                protocol=ConsensusProtocol.gossip,
                details=(
                    f"gossip: reached in round {round_num}/{max_rounds}, "
                    f"final {approve}/{total} approve"
                ),
                votes=votes,
            )
        if reject >= threshold:
            return ConsensusResult(
                reached=True,
                approved=False,
                total_votes=total,
                approval_count=approved_count,
                rejection_count=rejected_count,
                required=threshold,
                protocol=ConsensusProtocol.gossip,
                details=(
                    f"gossip: reached (rejected) in round {round_num}/{max_rounds}, "
                    f"final {reject}/{total} reject"
                ),
                votes=votes,
            )

    # Never reached consensus within max rounds
    return ConsensusResult(
        reached=False,
        approved=False,
        total_votes=total,
        approval_count=approved_count,
        rejection_count=rejected_count,
        required=threshold,
        protocol=ConsensusProtocol.gossip,
        details=(
            f"gossip: not reached after {max_rounds} rounds, "
            f"approve={approve}, reject={reject}, need {threshold}"
        ),
        votes=votes,
    )


CONSENSUS_FUNCS = {
    ConsensusProtocol.majority: majority_consensus,
    ConsensusProtocol.quorum: quorum_consensus,
    ConsensusProtocol.raft: raft_consensus,
    ConsensusProtocol.bft: bft_consensus,
    ConsensusProtocol.bft_escrow: bft_consensus,
    ConsensusProtocol.selective_debate: selective_debate_consensus,
    ConsensusProtocol.confidence_weighted: confidence_weighted_consensus,
    ConsensusProtocol.critic_verifier: critic_verifier_consensus,
    ConsensusProtocol.hitl_signoff: hitl_signoff_quorum,
    ConsensusProtocol.gossip: gossip_consensus,
}


def run_consensus(
    votes: list[AgentVote],
    protocol: ConsensusProtocol = ConsensusProtocol.majority,
    quorum: int | None = None,
    **kwargs: Any,
) -> ConsensusResult:
    """Run consensus using the specified protocol.

    Dispatches to the appropriate consensus function. For bft_escrow,
    the protocol field is set to bft_escrow (not bft) to distinguish
    the escrow-wrapped path.

    Args:
        votes: Agent votes to process.
        protocol: Which consensus protocol to use.
        quorum: Optional quorum override.
        **kwargs: Additional protocol-specific keyword arguments
            (e.g. candidates, verifier_votes, prompts, top_k, max_rounds).

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

    # Only pass quorum if it's not None, so protocol defaults apply
    func_kwargs: dict[str, Any] = dict(kwargs)
    if quorum is not None:
        func_kwargs["quorum"] = quorum
    return func(votes, **func_kwargs)
