"""
JobSupervisor — owns run lifecycle, cancellation, and orphan recovery (ADR-002).

Wires the EventBroker for live event streaming during execution.
Enforces workspace trust before starting runs (ADR-006 P2).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from ..audit.hitl import HitlPrompt, HitlResponse
from ..protocol.schemas import RunRecord, RunStatus
from ..security.trust import ensure_trusted
from ..storage.jsonl import JsonlTraceStore
from .event_broker import EventBroker
from .events import create_event

log = logging.getLogger(__name__)


class RunRequest(BaseModel):
    """Input for starting a run via the supervisor."""
    workflow_id: str
    runtime: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    prompt: Optional[str] = None
    profile_id: str = "stub"
    timeout_seconds: int = 300
    metadata: dict[str, Any] = Field(default_factory=dict)
    workspace_root: Optional[str] = None
    """Workspace root path for trust enforcement.

    If set, ``start_run()`` enforces workspace trust before execution.
    Untrusted workspaces raise ``WorkspaceUntrusted``.
    """
    workspace_trust_db: Optional[str] = None
    """Optional external trust DB path, primarily for tests/embedded daemons."""


@dataclass
class ActiveRun:
    """A currently-executing run managed by the supervisor."""
    run_id: str
    task: Optional[asyncio.Task] = None
    cancelled: bool = False


class HitlTimeoutError(TimeoutError):
    """Raised when a HITL prompt receives no response before timeout."""


class HitlNotFoundError(KeyError):
    """Raised when responding to an unknown or expired HITL prompt."""


class JobSupervisor:
    """Manages run lifecycle, cancellation, and orphan recovery.

    Delegates actual execution to an ``executor_fn`` callback.
    Events during execution are emitted through the EventBroker.
    """

    def __init__(
        self,
        store: JsonlTraceStore,
        broker: Optional[EventBroker] = None,
    ) -> None:
        self.store = store
        self.broker = broker or EventBroker(store)
        self._active_runs: dict[str, ActiveRun] = {}
        self._sequence_counters: dict[str, int] = {}
        self._pending_hitl: dict[str, asyncio.Future[HitlResponse]] = {}

    async def start_run(
        self,
        request: RunRequest,
        executor_fn: Callable,
    ) -> RunRecord:
        """Start a run asynchronously.

        ``executor_fn`` receives ``(run_id, request, emit_event)`` where
        ``emit_event`` is a callable to publish events during execution.

        Enforces workspace trust (ADR-006 P2): if ``request.workspace_root``
        is set, the workspace must be trusted. Raises ``WorkspaceUntrusted``
        if the workspace is not in the external trust database.
        """
        if request.workspace_root:
            trust_db = Path(request.workspace_trust_db) if request.workspace_trust_db else None
            if trust_db:
                ensure_trusted(Path(request.workspace_root), trust_db=trust_db)
            else:
                ensure_trusted(Path(request.workspace_root))

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        run = RunRecord(
            id=run_id,
            workflow_id=request.workflow_id,
            runtime=request.runtime or "unknown",
            status=RunStatus.PENDING,
            started_at=now,
            metadata=request.metadata,
        )
        self.store.save(run)
        self._sequence_counters[run_id] = 0
        active = ActiveRun(run_id=run_id)
        self._active_runs[run_id] = active
        task = asyncio.create_task(
            self._execute_run(run_id, request, executor_fn),
            name=f"run-{run_id}",
        )
        active.task = task
        return run

    async def _execute_run(
        self,
        run_id: str,
        request: RunRequest,
        executor_fn: Callable,
    ) -> None:
        """Internal: execute a run with lifecycle event emission."""
        start_ms = self._now_ms()
        try:
            self._emit_event(run_id, "RUN_STARTED", {
                "workflow_id": request.workflow_id,
                "runtime": request.runtime or "unknown",
            })
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.RUNNING
                self.store.save(run)

            await executor_fn(run_id, request, self._emit_event)

            duration = self._now_ms() - start_ms
            self._emit_event(run_id, "RUN_COMPLETED", {"duration_ms": duration})
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.COMPLETED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)

        except asyncio.CancelledError:
            self._emit_event(run_id, "RUN_CANCELLED", {"cancel_reason": "user_requested"})
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.CANCELLED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)

        except Exception as e:
            duration = self._now_ms() - start_ms
            self._emit_event(run_id, "RUN_FAILED", {
                "error": str(e),
                "error_detail": type(e).__name__,
            })
            run = self.store.load(run_id)
            if run:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                self.store.save(run)

        finally:
            self.broker.end_run(run_id)
            self._active_runs.pop(run_id, None)
            self._sequence_counters.pop(run_id, None)

    def _emit_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Create a schema-validated event and publish it through the broker."""
        seq = self._sequence_counters.get(run_id, 0)
        event = create_event(run_id, seq, event_type, data)
        self._sequence_counters[run_id] = seq + 1
        run = self.store.load(run_id)
        if run:
            run.events.append(event)
            self.store.save(run)
        self.broker.publish(run_id, event.model_dump())

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel an active run. Returns True if cancellation was requested."""
        active = self._active_runs.get(run_id)
        if active is None or active.task is None:
            return False
        active.cancelled = True
        active.task.cancel()
        try:
            await active.task
        except asyncio.CancelledError:
            pass
        return True

    async def recover_orphans(self) -> int:
        """Mark RUNNING runs from a previous supervisor session as FAILED."""
        recovered = 0
        for run_id in self.store.list_runs():
            run = self.store.load(run_id)
            if run and run.status == RunStatus.RUNNING:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.now(timezone.utc).isoformat()
                run.metadata["failure_reason"] = "supervisor_orphan"
                self.store.save(run)
                recovered += 1
        return recovered

    def get_active_run(self, run_id: str) -> Optional[ActiveRun]:
        """Return the ActiveRun for a run_id, or None if not active."""
        return self._active_runs.get(run_id)

    async def request_hitl(self, prompt: HitlPrompt) -> HitlResponse:
        """Emit a HITL prompt and wait for a single-user response.

        The prompt is persisted as a run event and streamed through the broker.
        ``respond_hitl()`` completes the pending future. On timeout the prompt
        is closed, a timeout event is emitted, and ``HitlTimeoutError`` is raised.
        """
        if prompt.hitl_id in self._pending_hitl:
            raise ValueError(f"HITL prompt already pending: {prompt.hitl_id}")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[HitlResponse] = loop.create_future()
        self._pending_hitl[prompt.hitl_id] = future
        self._emit_event(prompt.run_id, "HITL_PROMPT", {
            "hitl_id": prompt.hitl_id,
            "step_id": prompt.step_id,
            "prompt_text": prompt.prompt_text,
            "context": prompt.context,
            "options": prompt.options,
            "timeout_seconds": prompt.timeout_seconds,
            "created_at": prompt.created_at,
        })
        try:
            return await asyncio.wait_for(future, timeout=prompt.timeout_seconds)
        except asyncio.TimeoutError as exc:
            self._emit_event(prompt.run_id, "HITL_TIMEOUT", {
                "hitl_id": prompt.hitl_id,
                "timeout_seconds": prompt.timeout_seconds,
            })
            raise HitlTimeoutError(f"HITL prompt timed out: {prompt.hitl_id}") from exc
        finally:
            self._pending_hitl.pop(prompt.hitl_id, None)

    def respond_hitl(self, response: HitlResponse) -> None:
        """Resolve a pending HITL prompt and emit the response event."""
        future = self._pending_hitl.get(response.hitl_id)
        if future is None or future.done():
            raise HitlNotFoundError(response.hitl_id)
        future.set_result(response)
        self._emit_event(response.run_id, "HITL_RESPONSE", {
            "hitl_id": response.hitl_id,
            "decision": response.decision.value,
            "operator_id": response.operator_id,
            "modified_data": response.modified_data,
            "notes": response.notes,
            "responded_at": response.responded_at,
        })

    def pending_hitl(self, run_id: str | None = None) -> list[dict[str, str]]:
        """Return pending HITL ids. Kept minimal until persistence/CLI lands."""
        items: list[dict[str, str]] = []
        for hitl_id, future in self._pending_hitl.items():
            if future.done():
                continue
            items.append({"hitl_id": hitl_id})
        return items

    @staticmethod
    def _now_ms() -> int:
        import time
        return int(time.time() * 1000)
