"""Swarmgraph failure-mode detectors.

Read-only observers — they inspect state/results and return a typed
``SwarmGraphEvent`` when a failure condition is met, or ``None`` otherwise.
They never mutate state.

Phase 106 slices 1-3 implemented detectors 1-3:
  - detect_consensus_failure
  - detect_resource_exhaustion
  - detect_coordination_deadlock

Phase 107 (this file) adds detectors 4-10:
  - detect_worker_timeout
  - detect_budget_warning
  - detect_stale_tasks
  - detect_protocol_mismatch
  - detect_provider_degraded
  - detect_empty_output
  - detect_all_failed
"""

from __future__ import annotations

from .events import SwarmGraphEvent, SwarmGraphEventKind
from .models import TaskStatus, WorkerResult
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


# ---------------------------------------------------------------------------
# Phase 107 detectors 4-10
# ---------------------------------------------------------------------------


def detect_worker_timeout(
    results: list[WorkerResult],
    state: SwarmState,
) -> SwarmGraphEvent | None:
    """Detector 4: one or more workers returned a timeout error."""
    timed_out = [r for r in results if r.error == "timeout"]
    if not timed_out:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "worker_timeout",
            "timed_out_count": len(timed_out),
            "timed_out_tasks": [r.task_id for r in timed_out],
        },
        round=state.current_round,
    )


def detect_budget_warning(
    state: SwarmState,
    budget_limit: float | None,
    threshold: float = 0.5,
) -> SwarmGraphEvent | None:
    """Detector 5: accumulated cost is approaching the budget limit (default 50%).

    Fires once when the ratio first crosses ``threshold``. Callers should track
    whether this has already fired to avoid repeat events if desired; the
    detector itself is stateless.
    """
    if budget_limit is None or budget_limit <= 0:
        return None
    ratio = state.accumulated_cost_usd / budget_limit
    if ratio < threshold:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "budget_warning",
            "ratio": round(ratio, 3),
            "accumulated": state.accumulated_cost_usd,
            "limit": budget_limit,
            "threshold": threshold,
        },
        round=state.current_round,
    )


def detect_stale_tasks(
    state: SwarmState,
    stale_rounds: int = 3,
) -> SwarmGraphEvent | None:
    """Detector 6: tasks have been pending/assigned for more than stale_rounds rounds.

    A task is stale if it is still in pending or assigned status AND the swarm
    has executed more than ``stale_rounds`` rounds total, suggesting a systemic
    scheduling problem rather than normal latency.
    """
    if state.current_round < stale_rounds:
        return None
    stale = [
        t for t in state.tasks.values() if t.status in (TaskStatus.pending, TaskStatus.assigned)
    ]
    if not stale:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "stale_tasks",
            "stale_count": len(stale),
            "stale_task_ids": [t.id for t in stale],
            "current_round": state.current_round,
            "stale_rounds_threshold": stale_rounds,
        },
        round=state.current_round,
    )


def detect_protocol_mismatch(
    outcomes: list[ConsensusRoundOutcome],
    state: SwarmState,
) -> SwarmGraphEvent | None:
    """Detector 7: consensus did not reach quorum in any outcome this round.

    Quorum failure (reached=False on all outcomes) suggests the configured
    protocol is too strict for the current worker count or task diversity.
    """
    if not outcomes:
        return None
    unreached = [o for o in outcomes if not o.consensus_result.reached]
    if not unreached or len(unreached) < len(outcomes):
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "protocol_mismatch",
            "unreached_count": len(unreached),
            "total": len(outcomes),
        },
        round=state.current_round,
    )


def detect_provider_degraded(
    results: list[WorkerResult],
    state: SwarmState,
) -> SwarmGraphEvent | None:
    """Detector 8: at least one worker result has a degraded error string.

    Provider adapters set ``result.error`` to a string starting with the mode
    name (e.g. ``gated_local error: ...``). A degraded provider response is a
    softer signal than a full timeout — the call completed but the provider
    returned a degraded/reduced result.
    """
    degraded = [r for r in results if r.error and "degraded" in r.error.lower()]
    if not degraded:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "provider_degraded",
            "degraded_count": len(degraded),
            "degraded_tasks": [r.task_id for r in degraded],
        },
        round=state.current_round,
    )


def detect_empty_output(
    results: list[WorkerResult],
    state: SwarmState,
) -> SwarmGraphEvent | None:
    """Detector 9: one or more workers succeeded (no error) but returned empty output.

    Empty non-error output suggests a provider configuration issue or a prompt
    that consistently produces no response — not a hard failure, but a quality signal.
    """
    empty = [r for r in results if not r.error and not r.output.strip()]
    if not empty:
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "empty_output",
            "empty_count": len(empty),
            "empty_tasks": [r.task_id for r in empty],
        },
        round=state.current_round,
    )


def detect_all_failed(
    state: SwarmState,
) -> SwarmGraphEvent | None:
    """Detector 10: every task in the swarm has failed or been cancelled.

    Fires when there are tasks and none are in a terminal success state,
    indicating a total swarm failure rather than individual task errors.
    """
    if not state.tasks:
        return None
    terminal_failures = {TaskStatus.failed, TaskStatus.cancelled}
    all_tasks = list(state.tasks.values())
    if not all(t.status in terminal_failures for t in all_tasks):
        return None
    return SwarmGraphEvent(
        kind=SwarmGraphEventKind.error,
        swarm_id=state.id,
        data={
            "failure_mode": "all_failed",
            "total_tasks": len(all_tasks),
            "failed_count": sum(1 for t in all_tasks if t.status == TaskStatus.failed),
            "cancelled_count": sum(1 for t in all_tasks if t.status == TaskStatus.cancelled),
        },
        round=state.current_round,
    )
