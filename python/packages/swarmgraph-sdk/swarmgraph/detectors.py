from __future__ import annotations

from .events import SwarmGraphEvent, SwarmGraphEventKind
from .nodes.consensus import ConsensusRoundOutcome
from .state import SwarmState


def detect_consensus_failure(
    outcomes: list[ConsensusRoundOutcome],
    state: SwarmState,
) -> SwarmGraphEvent | None:
    if not outcomes:
        return None
    rejected = sum(1 for outcome in outcomes if not outcome.decision.approved)
    if rejected <= len(outcomes) / 2:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "consensus_failure",
            "rejected_count": rejected,
            "total": len(outcomes),
        },
        round=state.current_round,
    )


def detect_resource_exhaustion(
    state: SwarmState,
    budget_limit: float | None,
) -> SwarmGraphEvent | None:
    if budget_limit is None or budget_limit <= 0:
        return None
    ratio = state.accumulated_cost_usd / budget_limit
    if ratio < 0.8:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "resource_exhaustion",
            "ratio": round(ratio, 3),
            "accumulated": state.accumulated_cost_usd,
            "limit": budget_limit,
        },
        round=state.current_round,
    )


def detect_coordination_deadlock(
    state: SwarmState,
    previous_pending_count: int,
) -> SwarmGraphEvent | None:
    current_pending = len(state.get_pending_tasks())
    if current_pending <= 0:
        return None
    if current_pending != previous_pending_count or state.current_round < 1:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "coordination_deadlock",
            "stuck_tasks": current_pending,
            "rounds_stuck": 2,
        },
        round=state.current_round,
    )
