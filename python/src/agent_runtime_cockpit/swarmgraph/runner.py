from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .config import ExecutionMode, SwarmGraphConfig
from .decomposition import DecompositionStrategy, parallelizability_score
from .detectors import (
    detect_consensus_failure,
    detect_coordination_deadlock,
    detect_resource_exhaustion,
)
from .events import (
    SwarmGraphEvent,
    SwarmGraphEventKind,
    emit_budget_event,
    emit_topology_event,
    emit_worker_event,
)
from .graph import build_swarm_graph
from .models import (
    SwarmStatus,
    SwarmTask,
    TaskStatus,
    WorkerResult,
)
from .nodes.approval import require_hitl_approval
from .nodes.consensus import (
    emit_consensus_events_for_outcomes,
    run_consensus_round_with_results,
)
from .nodes.queen import queen_assign, queen_decompose, queen_prepare_agents
from .nodes.worker import process_worker_results, worker_execute_async
from .providers import Provider
from .state import SwarmState


class CancellationToken(Protocol):
    is_cancelled: Any


class SwarmRunTaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    output: str = ""
    status: str


class SwarmRunResult(BaseModel):
    """Typed SDK result wrapper for the existing stable dict payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    swarm_id: str | None = None
    status: str
    rounds: int = Field(default=0, ge=0)
    total_tasks: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    failed_tasks: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0)
    error: str | None = None
    results: list[SwarmRunTaskResult] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SwarmRunResult:
        return cls.model_validate(payload)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SwarmGraphRunner:
    def __init__(
        self,
        config: SwarmGraphConfig | None = None,
        on_event: Callable[[SwarmGraphEvent], None] | None = None,
        decomposition_strategy: DecompositionStrategy | None = None,
        provider: Provider | None = None,
    ):
        self.config = config or SwarmGraphConfig()
        self.state: SwarmState | None = None
        self.events: list[SwarmGraphEvent] = []
        self._on_event = on_event
        self._decomposition_strategy = decomposition_strategy
        self._provider = provider

    def _emit(self, event: SwarmGraphEvent) -> None:
        self.events.append(event)
        if self._on_event is None:
            return
        try:
            self._on_event(event)
        except Exception:
            return

    def run(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        return _run_coro_sync(self.run_async(prompt, config, cancellation_token))

    def run_sync(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        return self.run(prompt, config, cancellation_token)

    def run_result(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> SwarmRunResult:
        return SwarmRunResult.from_dict(self.run(prompt, config, cancellation_token))

    async def run_async(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        cfg = config or self.config
        fan_out_score = parallelizability_score(prompt)
        effective_workers = cfg.num_workers if fan_out_score >= cfg.fan_out_threshold else 1
        runtime_cfg = cfg.model_copy(update={"num_workers": effective_workers})
        cfg = runtime_cfg
        self.state = SwarmState(config=cfg)
        self.state.status = SwarmStatus.running
        self.state.metadata["requested_workers"] = (config or self.config).num_workers
        self.state.metadata["effective_workers"] = effective_workers
        self.events = []

        if _token_cancelled(cancellation_token):
            self.state.status = SwarmStatus.cancelled
            self.state.error = "cancelled"
            self.state.updated_at = datetime.now(timezone.utc)
            return self._build_result()

        self._emit(
            SwarmGraphEvent(
                kind=SwarmGraphEventKind.audit,
                swarm_id=self.state.id,
                data={
                    "fan_out_score": fan_out_score,
                    "fan_out_threshold": cfg.fan_out_threshold,
                    "requested_workers": (config or self.config).num_workers,
                    "effective_workers": effective_workers,
                    "decision": "fan_out" if effective_workers > 1 else "single",
                },
                round=0,
            )
        )

        queen_prepare_agents(self.state, cfg.num_workers)
        self.state.save_checkpoint()

        if self._decomposition_strategy is None:
            tasks = queen_decompose(self.state, prompt)
        else:
            tasks = self._decomposition_strategy.decompose(prompt, cfg.num_workers, cfg)
        for t in tasks:
            self.state.tasks[t.id] = t

        topology = build_swarm_graph(self.state)
        self._emit(emit_topology_event(self.state, topology))
        previous_pending_count = -1

        for round_num in range(cfg.max_rounds):
            if _token_cancelled(cancellation_token):
                self.state.status = SwarmStatus.cancelled
                self.state.error = "cancelled"
                break
            self.state.current_round = round_num
            pending = self.state.get_pending_tasks()
            if not pending:
                break

            if self._budget_exhausted(cfg):
                self.state.status = SwarmStatus.failed
                self.state.error = "budget exhausted"
                self._emit(emit_budget_event(self.state, 0.0, cfg.budget_limit_usd))
                break

            assignment = queen_assign(self.state, pending)
            worker_results = await self._execute_workers_parallel(
                pending,
                assignment,
                cfg,
                cancellation_token,
            )

            if self.state.status == SwarmStatus.cancelled:
                break

            process_worker_results(pending, worker_results)

            if cfg.require_hitl:
                for task in pending:
                    if (
                        task.status == TaskStatus.completed
                        and task.result
                        and not task.result.error
                    ):
                        require_hitl_approval(task)
            else:
                outcomes = run_consensus_round_with_results(
                    pending, protocol=cfg.consensus_protocol.value
                )
                for event in emit_consensus_events_for_outcomes(self.state, outcomes):
                    self._emit(event)
                failure_event = detect_consensus_failure(outcomes, self.state)
                if failure_event is not None:
                    self._emit(failure_event)

            resource_event = detect_resource_exhaustion(self.state, cfg.budget_limit_usd)
            if resource_event is not None:
                self._emit(resource_event)

            deadlock_event = detect_coordination_deadlock(self.state, previous_pending_count)
            if deadlock_event is not None:
                self._emit(deadlock_event)
            previous_pending_count = len(self.state.get_pending_tasks())

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

    async def run_result_async(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> SwarmRunResult:
        payload = await self.run_async(prompt, config, cancellation_token)
        return SwarmRunResult.from_dict(payload)

    async def _execute_workers_parallel(
        self,
        pending: list[SwarmTask],
        assignment: dict[str, str],
        cfg: SwarmGraphConfig,
        cancellation_token: CancellationToken | None,
    ) -> list[WorkerResult]:
        if self.state is None:
            return []

        sem = asyncio.Semaphore(cfg.max_parallel_workers)

        async def bounded_execute(task: SwarmTask) -> WorkerResult | None:
            async with sem:
                if _token_cancelled(cancellation_token):
                    return None
                try:
                    worker_kwargs: dict[str, Any] = {
                        "mode": cfg.execution_mode,
                        "timeout": cfg.worker_timeout_seconds,
                        "cancellation_token": cancellation_token,
                    }
                    if (
                        cfg.execution_mode == ExecutionMode.gated_local
                        or self._provider is not None
                    ):
                        worker_kwargs.update(
                            {
                                "provider": self._provider,
                                "allow_paid_calls": cfg.allow_paid_calls,
                            }
                        )
                    return await worker_execute_async(
                        task,
                        **worker_kwargs,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    return WorkerResult(
                        worker_id=task.assigned_agent_id or "unknown",
                        task_id=task.id,
                        output="",
                        error=f"worker exception: {exc}",
                        started_at=datetime.now(timezone.utc),
                    )

        worker_tasks = [
            asyncio.create_task(bounded_execute(task)) for task in pending if task.id in assignment
        ]
        remaining = set(worker_tasks)
        worker_results: list[WorkerResult] = []

        try:
            while remaining:
                if _token_cancelled(cancellation_token):
                    for worker_task in remaining:
                        worker_task.cancel()
                    for task in pending:
                        if task.status not in (TaskStatus.completed, TaskStatus.failed):
                            task.status = TaskStatus.cancelled
                    self.state.status = SwarmStatus.cancelled
                    self.state.error = "cancelled"
                    break

                done, remaining = await asyncio.wait(
                    remaining,
                    timeout=0.05,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for worker_task in done:
                    try:
                        result = worker_task.result()
                    except asyncio.CancelledError:
                        continue
                    if result is None:
                        continue
                    worker_results.append(result)
                    self._record_worker_result(result, cfg)
                    if self.state.status == SwarmStatus.failed:
                        for pending_task in remaining:
                            pending_task.cancel()
                        remaining.clear()
                        break
        finally:
            for worker_task in remaining:
                worker_task.cancel()

        return worker_results

    def _record_worker_result(self, result: WorkerResult, cfg: SwarmGraphConfig) -> None:
        if self.state is None:
            return
        self._emit(emit_worker_event(self.state, result))
        if not cfg.enable_budget:
            return
        self.state.accumulated_cost_usd += result.cost_usd
        self._emit(
            emit_budget_event(
                self.state,
                result.cost_usd,
                cfg.budget_limit_usd,
            )
        )
        if (
            cfg.budget_limit_usd is not None
            and self.state.accumulated_cost_usd >= cfg.budget_limit_usd
        ):
            self.state.status = SwarmStatus.failed
            self.state.error = "budget exhausted"

    def _budget_exhausted(self, cfg: SwarmGraphConfig) -> bool:
        if self.state is None or not cfg.enable_budget or cfg.budget_limit_usd is None:
            return False
        return self.state.accumulated_cost_usd >= cfg.budget_limit_usd

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


def _token_cancelled(cancellation_token: CancellationToken | None) -> bool:
    if cancellation_token is None:
        return False
    marker = getattr(cancellation_token, "is_cancelled", False)
    if callable(marker):
        return bool(marker())
    return bool(marker)


def _run_coro_sync(coro) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] | None = None
    error: BaseException | None = None

    def run_in_thread() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except BaseException as exc:
            error = exc

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error is not None:
        raise error
    return result or {"status": "no_run", "error": "no run executed"}
