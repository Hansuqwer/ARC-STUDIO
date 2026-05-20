from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Protocol

from .config import ExecutionMode, SwarmGraphConfig
from .consensus import run_consensus
from .events import (
    SwarmGraphEvent,
    emit_budget_event,
    emit_consensus_event,
    emit_topology_event,
    emit_worker_event,
)
from .graph import build_swarm_graph
from .models import (
    AgentStatus,
    AgentVote,
    ApprovalDecision,
    SwarmFailureCause,
    SwarmStatus,
    SwarmTask,
    TaskStatus,
    WorkerResult,
)
from .nodes.approval import require_hitl_approval
from .nodes.consensus import run_consensus_round
from .nodes.queen import queen_assign, queen_decompose, queen_prepare_agents
from .nodes.worker import process_worker_results, worker_execute
from .state import SwarmState


class CancellationToken(Protocol):
    def is_cancelled(self) -> bool: ...


class SwarmGraphRunner:
    def __init__(self, config: SwarmGraphConfig | None = None):
        self.config = config or SwarmGraphConfig()
        self.state: SwarmState | None = None
        self.events: list[SwarmGraphEvent] = []

    def run(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        cfg = config or self.config
        self.state = SwarmState(config=cfg)
        self.state.status = SwarmStatus.running
        self.events = []

        if cancellation_token and cancellation_token.is_cancelled():
            self.state.status = SwarmStatus.cancelled
            self.state.error = "cancelled"
            self.state.updated_at = datetime.now(timezone.utc)
            return self._build_result()

        queen_prepare_agents(self.state, cfg.num_workers)
        self.state.save_checkpoint()

        tasks = queen_decompose(self.state, prompt)
        for t in tasks:
            self.state.tasks[t.id] = t

        topology = build_swarm_graph(self.state)
        self.events.append(emit_topology_event(self.state, topology))

        for round_num in range(cfg.max_rounds):
            if cancellation_token and cancellation_token.is_cancelled():
                self.state.status = SwarmStatus.cancelled
                self.state.error = "cancelled"
                break
            self.state.current_round = round_num
            pending = self.state.get_pending_tasks()
            if not pending:
                break

            assignment = queen_assign(self.state, pending)
            worker_results: list[WorkerResult] = []
            for task in pending:
                if cancellation_token and cancellation_token.is_cancelled():
                    task.status = TaskStatus.cancelled
                    self.state.status = SwarmStatus.cancelled
                    self.state.error = "cancelled"
                    break
                if task.id not in assignment:
                    continue
                result = worker_execute(
                    task,
                    mode=cfg.execution_mode,
                    timeout=cfg.worker_timeout_seconds,
                )
                worker_results.append(result)
                self.events.append(emit_worker_event(self.state, result))
                if cfg.enable_budget:
                    self.state.accumulated_cost_usd += result.cost_usd
                    self.events.append(emit_budget_event(
                        self.state, result.cost_usd, cfg.budget_limit_usd,
                    ))

            if self.state.status == SwarmStatus.cancelled:
                break

            process_worker_results(pending, worker_results)

            if cfg.require_hitl:
                for task in pending:
                    if task.status == TaskStatus.completed and task.result and not task.result.error:
                        require_hitl_approval(task)
            else:
                decisions = run_consensus_round(pending, protocol=cfg.consensus_protocol.value)
                for task, decision in zip(pending, decisions):
                    self.events.append(emit_consensus_event(self.state, task.id, decision))

            if cfg.enable_budget and cfg.budget_limit_usd is not None:
                if self.state.accumulated_cost_usd >= cfg.budget_limit_usd:
                    self.state.status = SwarmStatus.failed
                    self.state.error = "budget exhausted"
                    break

            self.state.save_checkpoint()

        if self.state.status not in (SwarmStatus.failed, SwarmStatus.cancelled):
            if self.state.all_tasks_completed():
                self.state.status = SwarmStatus.completed
            else:
                self.state.status = SwarmStatus.completed

        self.state.updated_at = datetime.now(timezone.utc)
        return self._build_result()

    def get_state(self) -> SwarmState | None:
        return self.state

    def get_events(self) -> list[SwarmGraphEvent]:
        return self.events

    def _build_result(self) -> dict[str, Any]:
        if not self.state:
            return {"status": "no_run", "error": "no run executed"}

        completed_tasks = [t for t in self.state.tasks.values() if t.status == TaskStatus.completed]
        failed_tasks = self.state.failed_tasks()

        return {
            "swarm_id": self.state.id,
            "status": self.state.status.value,
            "rounds": self.state.current_round + 1,
            "total_tasks": len(self.state.tasks),
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "total_cost_usd": self.state.accumulated_cost_usd,
            "error": self.state.error,
            "results": [
                {
                    "task_id": t.id,
                    "output": t.result.output if t.result else "",
                    "status": t.status.value,
                }
                for t in completed_tasks
            ],
            "events": [e.to_dict() for e in self.events],
        }
