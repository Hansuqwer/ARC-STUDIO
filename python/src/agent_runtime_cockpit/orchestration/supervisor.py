"""
JobSupervisor — owns run lifecycle, cancellation, and orphan recovery (ADR-002).

Wires the EventBroker for live event streaming during execution.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from ..protocol.schemas import RunRecord, RunStatus
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


@dataclass
class ActiveRun:
    """A currently-executing run managed by the supervisor."""
    run_id: str
    task: Optional[asyncio.Task] = None
    cancelled: bool = False


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

    async def start_run(
        self,
        request: RunRequest,
        executor_fn: Callable,
    ) -> RunRecord:
        """Start a run asynchronously.

        ``executor_fn`` receives ``(run_id, request, emit_event)`` where
        ``emit_event`` is a callable to publish events during execution.
        """
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

    @staticmethod
    def _now_ms() -> int:
        import time
        return int(time.time() * 1000)
