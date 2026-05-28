"""Consensus protocol evaluation harness — benchmark protocols against synthetic votes.

Provides:
- ``ConsensusEvalConfig`` — Pydantic model for eval configuration
- ``ConsensusEvalResult`` — Pydantic model for a single protocol eval result
- ``ConsensusEvalComparison`` — Pydantic model for multi-protocol comparison
- ``run_consensus_eval()`` — run eval for one or all protocols
- ``compare_protocols()`` — rank protocols by composite score
"""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

from ..swarmgraph.config import ConsensusProtocol
from ..swarmgraph.consensus import run_consensus
from ..swarmgraph.models import AgentVote

# Default set of protocols to benchmark
ALL_PROTOCOLS = [
    ConsensusProtocol.majority,
    ConsensusProtocol.quorum,
    ConsensusProtocol.raft,
    ConsensusProtocol.bft,
    ConsensusProtocol.bft_escrow,
]


class ConsensusEvalConfig(BaseModel):
    """Configuration for a consensus evaluation run.

    Attributes:
        protocols: List of protocol names to benchmark (empty = all).
        num_workers: Number of synthetic workers.
        num_rounds: Number of consensus rounds.
        synthetic_votes: If True, generate deterministic fake votes.
        consensus_escrow: If True, use escrow-wrapped protocols.
    """

    protocols: list[str] = Field(default_factory=list)
    num_workers: int = Field(default=4, ge=1, le=50)
    num_rounds: int = Field(default=3, ge=1, le=100)
    synthetic_votes: bool = True
    consensus_escrow: bool = False


class ConsensusEvalResult(BaseModel):
    """Result of evaluating a single consensus protocol.

    Attributes:
        protocol: Name of the protocol benchmarked.
        total_votes: Number of votes processed.
        rounds: Number of consensus rounds.
        duration_ms: Wall-clock time in milliseconds.
        consensus_reached: Whether consensus was reached.
        approval_count: Number of approved votes.
        quality_score: Simulated quality score (0-1).
        cost_score: Simulated token cost.
        latency_ms: Average latency in milliseconds.
        disagreement_rate: Fraction of votes that disagreed (0-1).
        escalation_rate: Fraction of rounds requiring HITL escalation (0-1).
    """

    protocol: str
    total_votes: int
    rounds: int
    duration_ms: int
    consensus_reached: bool
    approval_count: int
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cost_score: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    disagreement_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class ConsensusEvalComparison(BaseModel):
    """Comparison of multiple protocol eval results.

    Attributes:
        results: All eval results.
        best_protocol: Protocol with highest composite score.
        recommendation: Human-readable recommendation text.
    """

    results: list[ConsensusEvalResult]
    best_protocol: str
    recommendation: str


# ---------------------------------------------------------------------------
# Synthetic vote generation (deterministic, no randomness)
# ---------------------------------------------------------------------------


def _make_vote(
    agent_id: str, approved: bool, confidence: float, task_id: str, round_num: int
) -> AgentVote:
    """Create a single deterministic AgentVote."""
    import datetime

    return AgentVote(
        agent_id=agent_id,
        task_id=task_id,
        round=round_num,
        approved=approved,
        confidence=confidence,
        reasoning="synthetic eval vote",
        timestamp=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
    )


def _generate_synthetic_votes(
    num_workers: int,
    num_rounds: int,
    *,
    seed_offset: int = 0,
) -> list[list[AgentVote]]:
    """Generate deterministic synthetic votes per round.

    Vote distribution (deterministic hash-based):
    - ~60% approve with confidence 0.8
    - ~30% reject with confidence 0.7
    - ~10% approve with low confidence 0.3

    Returns a list of vote lists, one per round.
    """
    rounds: list[list[AgentVote]] = []
    for r in range(num_rounds):
        round_votes: list[AgentVote] = []
        for w in range(num_workers):
            agent_id = f"agent-{w}"
            task_id = f"task-{seed_offset}"
            # Deterministic pseudo-random based on worker index and round
            idx = (w + r + seed_offset) % 10
            if idx < 6:
                # Approve with high confidence
                vote = _make_vote(agent_id, True, 0.8, task_id, r)
            elif idx < 9:
                # Reject with moderate confidence
                vote = _make_vote(agent_id, False, 0.7, task_id, r)
            else:
                # Approve with low confidence
                vote = _make_vote(agent_id, True, 0.3, task_id, r)
            round_votes.append(vote)
        rounds.append(round_votes)
    return rounds


def _resolve_protocols(config: ConsensusEvalConfig) -> list[ConsensusProtocol]:
    """Resolve the list of protocols to benchmark."""
    if config.protocols:
        return [ConsensusProtocol(p) for p in config.protocols]
    # Use all protocols; if escrow is requested, prefer bft_escrow over bft
    protocols = list(ALL_PROTOCOLS)
    if config.consensus_escrow:
        # Move bft_escrow to the front; keep bft for comparison
        pass  # bft_escrow is already in the list
    return protocols


# ---------------------------------------------------------------------------
# Core evaluation functions
# ---------------------------------------------------------------------------


def run_consensus_eval(config: ConsensusEvalConfig | None = None) -> list[ConsensusEvalResult]:
    """Run consensus evaluation for configured protocols.

    Generates synthetic votes (deterministic, no LLM/network) and runs each
    protocol's consensus function. Collects timing, quality, and cost metrics.

    Args:
        config: Evaluation configuration. Uses defaults if None.

    Returns:
        List of ConsensusEvalResult, one per protocol.

    """
    config = config or ConsensusEvalConfig()
    protocols = _resolve_protocols(config)

    # Generate synthetic votes (shared across all protocols)
    all_rounds = _generate_synthetic_votes(
        config.num_workers,
        config.num_rounds,
    )

    results: list[ConsensusEvalResult] = []
    for protocol in protocols:
        total_votes = 0
        total_duration_ms = 0
        consensus_reached = True
        total_approval = 0
        total_disagreements = 0
        total_escalations = 0

        for round_votes in all_rounds:
            total_votes += len(round_votes)

            start = time.perf_counter()
            result = run_consensus(
                votes=round_votes,
                protocol=protocol,
            )
            elapsed = time.perf_counter() - start
            duration_ms = int(elapsed * 1000)
            total_duration_ms += duration_ms

            if not result.reached:
                consensus_reached = False

            total_approval += result.approval_count
            total_disagreements += result.rejection_count

            # Escalation heuristic: consensus not reached or requires HITL
            if not result.reached:
                total_escalations += 1

        # Compute metrics
        num_rounds = len(all_rounds)
        avg_disagreement_rate = total_disagreements / total_votes if total_votes > 0 else 0.0
        escalation_rate = total_escalations / num_rounds if num_rounds > 0 else 0.0

        # Simulated quality score: higher for protocols that reach consensus
        # with broad agreement
        quality_score = _compute_quality(
            protocol, total_approval, total_votes, consensus_reached, num_rounds
        )

        # Simulated cost score: token count estimate based on protocol complexity
        cost_score = _compute_cost(protocol, total_votes, num_rounds)

        # Latency: simulation based on protocol type
        avg_latency_ms = float(total_duration_ms)

        results.append(
            ConsensusEvalResult(
                protocol=protocol.value,
                total_votes=total_votes,
                rounds=num_rounds,
                duration_ms=total_duration_ms,
                consensus_reached=consensus_reached,
                approval_count=total_approval,
                quality_score=round(quality_score, 4),
                cost_score=round(cost_score, 2),
                latency_ms=round(avg_latency_ms, 2),
                disagreement_rate=round(avg_disagreement_rate, 4),
                escalation_rate=round(escalation_rate, 4),
            )
        )

    return results


def _compute_quality(
    protocol: ConsensusProtocol,
    approval_count: int,
    total_votes: int,
    consensus_reached: bool,
    num_rounds: int,
) -> float:
    """Compute a simulated quality score (0-1)."""
    if total_votes == 0:
        return 0.0

    approval_rate = approval_count / total_votes

    # Base quality: approval rate
    base = approval_rate

    # Bonus for reaching consensus
    consensus_bonus = 0.2 if consensus_reached else 0.0

    # Protocol-specific modifiers
    protocol_bonus = {
        ConsensusProtocol.bft: 0.05,  # Byzantine tolerance premium
        ConsensusProtocol.bft_escrow: 0.08,  # Escrow adds security
        ConsensusProtocol.raft: 0.03,  # Leader efficiency
        ConsensusProtocol.quorum: 0.02,
        ConsensusProtocol.majority: 0.01,
    }.get(protocol, 0.0)

    score = min(1.0, base * 0.7 + consensus_bonus + protocol_bonus)
    return max(0.0, score)


def _compute_cost(protocol: ConsensusProtocol, total_votes: int, num_rounds: int) -> float:
    """Compute a simulated cost score (token count)."""
    # Base cost per vote
    base = total_votes * 50  # 50 tokens per vote baseline

    # Protocol overhead
    overhead = {
        ConsensusProtocol.majority: 1.0,
        ConsensusProtocol.quorum: 1.1,
        ConsensusProtocol.raft: 1.3,  # Leader election overhead
        ConsensusProtocol.bft: 1.8,  # BFT message overhead
        ConsensusProtocol.bft_escrow: 2.2,  # Escrow adds extra messages
    }.get(protocol, 1.0)

    return base * overhead * num_rounds


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _composite_score(result: ConsensusEvalResult, all_results: list[ConsensusEvalResult]) -> float:
    """Compute a composite score (0-1) for ranking protocols.

    Formula: quality * 0.4 + (1 - cost_ratio) * 0.3 + (1 - latency_ratio) * 0.2 + (1 - disagreement) * 0.1

    Cost and latency are normalized against the max across results.
    """
    max_cost = max(r.cost_score for r in all_results) if all_results else 1
    max_latency = max(r.latency_ms for r in all_results) if all_results else 1

    cost_ratio = result.cost_score / max_cost if max_cost > 0 else 0
    latency_ratio = result.latency_ms / max_latency if max_latency > 0 else 0

    score = (
        result.quality_score * 0.4
        + (1.0 - cost_ratio) * 0.3
        + (1.0 - latency_ratio) * 0.2
        + (1.0 - result.disagreement_rate) * 0.1
    )
    return max(0.0, min(1.0, score))


def compare_protocols(results: list[ConsensusEvalResult]) -> ConsensusEvalComparison:
    """Compare protocol eval results and recommend the best protocol.

    Args:
        results: Eval results from run_consensus_eval().

    Returns:
        ConsensusEvalComparison with ranking and recommendation.

    """
    if not results:
        return ConsensusEvalComparison(
            results=[],
            best_protocol="none",
            recommendation="No results to compare.",
        )

    scored = [(r, _composite_score(r, results)) for r in results]
    scored.sort(key=lambda x: x[1], reverse=True)

    best_result, best_score = scored[0]

    # Build recommendation text
    details = []
    for r, s in scored:
        marker = "★" if s == best_score else " "
        details.append(
            f"  {marker} {r.protocol}: composite={s:.4f} quality={r.quality_score:.4f} cost={r.cost_score:.1f} latency={r.latency_ms:.1f}ms disagree={r.disagreement_rate:.4f}"
        )

    recommendation_lines = [
        f"Best protocol: {best_result.protocol} (composite score: {best_score:.4f})",
        "",
        "Rankings:",
        *details,
    ]
    if best_score < 0.4:
        recommendation_lines.append("")
        recommendation_lines.append(
            "Note: Low composite scores — consider adjusting worker count or protocol selection."
        )

    return ConsensusEvalComparison(
        results=[r for r, _ in scored],
        best_protocol=best_result.protocol,
        recommendation="\n".join(recommendation_lines),
    )
