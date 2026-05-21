from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ApprovalDecision, WorkerResult
from .state import SwarmState


class SwarmGraphEventKind(str, Enum):
    topology = "topology"
    consensus = "consensus"
    worker = "worker"
    hitl = "hitl"
    audit = "audit"
    budget = "budget"
    state_transition = "state_transition"
    error = "error"


class SwarmGraphEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    kind: SwarmGraphEventKind
    swarm_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    round: int = Field(default=0, ge=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "swarm_id": self.swarm_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "round": self.round,
        }


class TopologyEvent(SwarmGraphEvent):
    pass


class ConsensusEvent(SwarmGraphEvent):
    pass


class WorkerEvent(SwarmGraphEvent):
    pass


class HITLEvent(SwarmGraphEvent):
    pass


class AuditEvent(SwarmGraphEvent):
    pass


class BudgetEvent(SwarmGraphEvent):
    pass


def emit_topology_event(state: SwarmState, topology: Any) -> TopologyEvent:
    event = TopologyEvent(
        kind=SwarmGraphEventKind.topology,
        swarm_id=state.id,
        data={"topology": topology.to_dict() if hasattr(topology, 'to_dict') else topology},
        round=state.current_round,
    )
    return event


def emit_worker_event(state: SwarmState, worker_result: WorkerResult) -> WorkerEvent:
    event = WorkerEvent(
        kind=SwarmGraphEventKind.worker,
        swarm_id=state.id,
        data={
            "worker_id": worker_result.worker_id,
            "task_id": worker_result.task_id,
            "duration_seconds": worker_result.duration_seconds,
            "cost_usd": worker_result.cost_usd,
            "has_error": worker_result.error is not None,
        },
        round=state.current_round,
    )
    return event


def emit_consensus_event(
    state: SwarmState,
    task_id: str,
    approval: ApprovalDecision,
) -> ConsensusEvent:
    event = ConsensusEvent(
        kind=SwarmGraphEventKind.consensus,
        swarm_id=state.id,
        data={
            "task_id": task_id,
            "approved": approval.approved,
            "reason": approval.reason,
            "decided_by": approval.decided_by,
        },
        round=state.current_round,
    )
    return event


def emit_hitl_event(
    state: SwarmState,
    task_id: str,
    token_id: str,
    action: str = "pending",
) -> HITLEvent:
    event = HITLEvent(
        kind=SwarmGraphEventKind.hitl,
        swarm_id=state.id,
        data={
            "task_id": task_id,
            "token_id": token_id,
            "action": action,
        },
        round=state.current_round,
    )
    return event


def emit_budget_event(
    state: SwarmState,
    cost_usd: float,
    limit_usd: float | None,
) -> BudgetEvent:
    event = BudgetEvent(
        kind=SwarmGraphEventKind.budget,
        swarm_id=state.id,
        data={
            "cost_usd": cost_usd,
            "limit_usd": limit_usd,
            "accumulated": state.accumulated_cost_usd,
            "exhausted": limit_usd is not None and state.accumulated_cost_usd >= limit_usd,
        },
        round=state.current_round,
    )
    return event
