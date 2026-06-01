from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from .checkpoint import CheckpointStore
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
    AgentStatus,
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
from .notifications import NotificationHook
from .state import SwarmState

# Type alias for the optional guardrail callable (107.3).
# Defined after all imports to avoid E402 with forward-reference strings.
GuardrailFn: TypeAlias = Callable[[SwarmTask, WorkerResult], bool]


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
        checkpoint_store: CheckpointStore | None = None,
        guardrail: "GuardrailFn | None" = None,
        notification_hooks: list[NotificationHook] | None = None,
    ):
        self.config = config or SwarmGraphConfig()
        self.state: SwarmState | None = None
        self.events: list[SwarmGraphEvent] = []
        self._on_event = on_event
        self._decomposition_strategy = decomposition_strategy
        self._provider = provider
        self._checkpoint_store = checkpoint_store
        self._guardrail = guardrail
        self._notification_hooks: list[NotificationHook] = notification_hooks or []
        self._notification_tasks: list[asyncio.Task[None]] = []

    def _emit(self, event: SwarmGraphEvent) -> None:
        self.events.append(event)
        if self.state is not None:
            self.state.events.append(event.to_dict())
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass
        # Notification hooks (109.1): fire-and-forget async hooks.
        # Errors are caught inside each hook; they must never interrupt the run.
        for hook in self._notification_hooks:
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(hook.notify(event))
                task.add_done_callback(_consume_task_exception)
                self._notification_tasks.append(task)
            except Exception:
                pass

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
        resume_state: SwarmState | None = None,
    ) -> dict[str, Any]:
        self.events = []

        if resume_state is not None:
            cfg = resume_state.config
            self.state = resume_state
            self.state.status = SwarmStatus.running
            start_round = resume_state.current_round
            # Seed runner event list from checkpoint history so continuity is
            # preserved before the resume audit event is appended.
            seeded: list[SwarmGraphEvent] = []
            for evt_dict in resume_state.events:
                try:
                    seeded.append(
                        SwarmGraphEvent(
                            id=evt_dict["id"],
                            kind=SwarmGraphEventKind(evt_dict["kind"]),
                            swarm_id=evt_dict["swarm_id"],
                            data=evt_dict.get("data", {}),
                            round=evt_dict.get("round", 0),
                        )
                    )
                except Exception:
                    pass
            self.events = seeded
            # The state.events list is authoritative; runner.events is derived.
            # Do not double-append; _emit will add to state.events going forward.
            self._emit(
                SwarmGraphEvent(
                    kind=SwarmGraphEventKind.audit,
                    swarm_id=self.state.id,
                    data={
                        "decision": "resume",
                        "resumed_from": self.state.metadata.get("resumed_from"),
                        "resumed_from_round": start_round,
                        "pending_tasks": len(self.state.get_pending_tasks()),
                        "requeued_tasks": len(
                            self.state.metadata.get("resumed_requeued_tasks", [])
                        ),
                    },
                    round=start_round,
                )
            )
            topology = build_swarm_graph(self.state)
            self._emit(emit_topology_event(self.state, topology))
        else:
            cfg = config or self.config
            fan_out_score = parallelizability_score(prompt)
            effective_workers = cfg.num_workers if fan_out_score >= cfg.fan_out_threshold else 1
            runtime_cfg = cfg.model_copy(update={"num_workers": effective_workers})
            cfg = runtime_cfg
            self.state = SwarmState(config=cfg)
            self.state.status = SwarmStatus.running
            self.state.metadata["requested_workers"] = (config or self.config).num_workers
            self.state.metadata["effective_workers"] = effective_workers
            start_round = 0

            if _token_cancelled(cancellation_token):
                self.state.status = SwarmStatus.cancelled
                self.state.error = "cancelled"
                self.state.updated_at = datetime.now(timezone.utc)
                await self._drain_notifications()
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
            self._save_checkpoint()

            if self._decomposition_strategy is None:
                tasks = queen_decompose(self.state, prompt)
            else:
                tasks = self._decomposition_strategy.decompose(prompt, cfg.num_workers, cfg)
            for t in tasks:
                self.state.tasks[t.id] = t

            topology = build_swarm_graph(self.state)
            self._emit(emit_topology_event(self.state, topology))

        previous_pending_count = -1

        for round_num in range(start_round, cfg.max_rounds):
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

            ready_pending = [task for task in pending if self._parent_complete(task)]
            assignment = queen_assign(self.state, ready_pending)
            worker_results = await self._execute_workers_parallel(
                ready_pending,
                assignment,
                cfg,
                cancellation_token,
            )

            if self.state.status == SwarmStatus.cancelled:
                break

            process_worker_results(ready_pending, worker_results)

            if cfg.require_hitl:
                for task in ready_pending:
                    if (
                        task.status == TaskStatus.completed
                        and task.result
                        and not task.result.error
                    ):
                        require_hitl_approval(task)
            else:
                outcomes = run_consensus_round_with_results(
                    ready_pending, protocol=cfg.consensus_protocol.value
                )
                for event in emit_consensus_events_for_outcomes(self.state, outcomes):
                    self._emit(event)

                # Emit arena vote events for tasks with arena metadata
                if cfg.arena_battle_mode:
                    from .events import emit_arena_vote_event

                    for task in ready_pending:
                        if task.result and task.result.artifacts.get("arena_pair_id"):
                            arena_event = emit_arena_vote_event(
                                state=self.state,
                                task_id=task.id,
                                pair_id=task.result.artifacts["arena_pair_id"],
                                accepted_index=0,  # Winner is always index 0 in our design
                                winner_model=task.result.artifacts.get(
                                    "arena_winner_model", "unknown"
                                ),
                                loser_model=task.result.artifacts.get(
                                    "arena_loser_model", "unknown"
                                ),
                            )
                            self._emit(arena_event)

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

            self._save_checkpoint()

        if self.state.status not in (SwarmStatus.failed, SwarmStatus.cancelled):
            if self.state.all_tasks_completed():
                self.state.status = SwarmStatus.completed
            else:
                self.state.status = SwarmStatus.completed

        # Emit arena votes to server if arena_battle_mode is enabled
        if cfg.arena_battle_mode and self._provider is not None:
            provider_id = getattr(self._provider.capabilities(), "provider_id", "")
            if provider_id == "arena":
                from .events import ArenaVoteEvent
                from .vote_emitter import emit_arena_votes

                arena_vote_events = [evt for evt in self.events if isinstance(evt, ArenaVoteEvent)]
                if arena_vote_events:
                    # Import ArenaClient from ARC (not SDK)
                    try:
                        from agent_runtime_cockpit.arena.client import ArenaClient

                        arena_client = ArenaClient.from_env()
                        if arena_client:
                            await emit_arena_votes(arena_vote_events, arena_client)
                    except ImportError:
                        # ArenaClient not available (SDK-only usage), skip vote emission
                        pass

        self.state.updated_at = datetime.now(timezone.utc)
        await self._drain_notifications()
        return self._build_result()

    async def run_result_async(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> SwarmRunResult:
        payload = await self.run_async(prompt, config, cancellation_token)
        return SwarmRunResult.from_dict(payload)

    def _load_checkpoint_state(self, checkpoint_id: str) -> SwarmState:
        if self._checkpoint_store is None:
            raise ValueError("resume requires a checkpoint_store")
        checkpoint = self._checkpoint_store.load(checkpoint_id)
        return SwarmState.from_checkpoint(checkpoint)

    def resume(
        self,
        checkpoint_id: str,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        """Resume a run from a durable checkpoint, continuing from its round.

        Loads the checkpoint via the configured ``checkpoint_store`` and
        rehydrates :class:`SwarmState` so the round loop continues from the saved
        round and task state instead of starting over.
        """
        return _run_coro_sync(self.resume_async(checkpoint_id, cancellation_token))

    async def resume_async(
        self,
        checkpoint_id: str,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        resume_state = self._load_checkpoint_state(checkpoint_id)
        return await self.run_async(
            prompt="",
            cancellation_token=cancellation_token,
            resume_state=resume_state,
        )

    def resume_result(
        self,
        checkpoint_id: str,
        cancellation_token: CancellationToken | None = None,
    ) -> SwarmRunResult:
        return SwarmRunResult.from_dict(self.resume(checkpoint_id, cancellation_token))

    async def stream(
        self,
        prompt: str,
        config: SwarmGraphConfig | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator[SwarmGraphEvent]:
        queue: asyncio.Queue[SwarmGraphEvent] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_event(event: SwarmGraphEvent) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, event)

        runner = SwarmGraphRunner(
            config=config or self.config,
            on_event=on_event,
            decomposition_strategy=self._decomposition_strategy,
            provider=self._provider,
            checkpoint_store=self._checkpoint_store,
            guardrail=self._guardrail,
            notification_hooks=self._notification_hooks,
        )
        run_task = asyncio.create_task(runner.run_async(prompt, None, cancellation_token))

        while True:
            if run_task.done() and queue.empty():
                break
            try:
                yield await asyncio.wait_for(queue.get(), timeout=0.05)
            except TimeoutError:
                continue

        await run_task
        self.state = runner.state
        self.events = runner.events

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

        # Dependency gate: only schedule tasks whose parent is completed (or
        # have no parent). This turns parent_task_id into a real execution
        # dependency without requiring a separate scheduler — the runner's
        # round loop naturally retries pending tasks in subsequent rounds.
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
        # Guardrail check (107.3): if a guardrail is configured and rejects the
        # result, mark the task as failed before consensus and emit an error event.
        if self._guardrail is not None:
            task = self.state.tasks.get(result.task_id)
            if task is not None:
                try:
                    accepted = self._guardrail(task, result)
                except Exception:
                    accepted = False
                if not accepted:
                    failed_result = result.model_copy(update={"error": "guardrail rejected"})
                    task.result = failed_result
                    task.status = TaskStatus.failed
                    task.updated_at = datetime.now(timezone.utc)
                    self._emit(
                        SwarmGraphEvent(
                            kind=SwarmGraphEventKind.error,
                            swarm_id=self.state.id,
                            data={
                                "failure_mode": "guardrail_rejected",
                                "task_id": result.task_id,
                            },
                            round=self.state.current_round,
                        )
                    )
                    self._release_agent(result.worker_id, result.task_id)
                    return
        self._emit(emit_worker_event(self.state, result))
        self._release_agent(result.worker_id, result.task_id)
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

    def _save_checkpoint(self) -> None:
        if self.state is None:
            return
        checkpoint = self.state.save_checkpoint()
        if self._checkpoint_store is not None:
            self._checkpoint_store.save(checkpoint)

    def _parent_complete(self, task: SwarmTask) -> bool:
        if self.state is None:
            return True
        dependency_ids = list(task.dependency_task_ids)
        if task.parent_task_id is not None and task.parent_task_id not in dependency_ids:
            dependency_ids.append(task.parent_task_id)
        if not dependency_ids:
            return True
        for dependency_id in dependency_ids:
            dependency = self.state.tasks.get(dependency_id)
            if dependency is None or dependency.status != TaskStatus.completed:
                return False
        return True

    def _release_agent(self, worker_id: str, task_id: str) -> None:
        if self.state is None:
            return
        agent = self.state.agents.get(worker_id)
        if agent is None:
            return
        agent.status = AgentStatus.idle
        agent.current_task_id = None
        if task_id not in agent.completed_tasks:
            agent.completed_tasks.append(task_id)

    async def _drain_notifications(self) -> None:
        if not self._notification_tasks:
            return
        tasks = list(self._notification_tasks)
        self._notification_tasks.clear()
        await asyncio.gather(*tasks, return_exceptions=True)

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


def _consume_task_exception(task: asyncio.Task[None]) -> None:
    try:
        task.exception()
    except Exception:
        pass


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
