"""Task execution engine with retry logic and async support."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional

from agent_runtime_cockpit.events.bus import get_bus
from agent_runtime_cockpit.events.types import TaskCompleted, TaskFailed, TaskStateChanged
from agent_runtime_cockpit.tasks.models import Task, TaskStatus, TaskType
from agent_runtime_cockpit.tasks.storage import TaskStorage

log = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks asynchronously with retry support."""

    def __init__(self, storage: TaskStorage) -> None:
        self.storage = storage
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._task_threads: dict[str, threading.Thread] = {}
        self._cancel_flags: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start_worker(self) -> None:
        """Start background worker for processing tasks."""
        if self._running:
            log.warning("Task worker already running")
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="TaskWorker"
        )
        self._worker_thread.start()
        log.info("Task worker started")

    def stop_worker(self) -> None:
        """Stop background worker."""
        if not self._running:
            return

        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        self.wait_for_all(timeout=5.0)
        log.info("Task worker stopped")

    def _worker_loop(self) -> None:
        """Background worker loop for processing tasks."""
        while self._running:
            try:
                # Process tasks ready for retry
                retry_tasks = self.storage.get_tasks_for_retry()
                for task in retry_tasks:
                    if not self._running:
                        break
                    self._execute_task_async(task)

                # Clean up expired tasks
                self.storage.delete_expired_tasks()

                # Sleep before next iteration
                time.sleep(5.0)
            except Exception as e:
                log.error("Error in task worker loop: %s", e)
                time.sleep(5.0)

    def submit_task(self, task: Task) -> str:
        """Submit a new task for execution. Returns task ID."""
        self.storage.create_task(task)
        log.info("Task submitted: %s (type=%s, operation=%s)", task.id, task.type, task.operation)

        # Execute immediately in background
        self._execute_task_async(task)
        return task.id

    def _execute_task_async(self, task: Task) -> None:
        """Execute task in background thread."""
        thread = threading.Thread(
            target=self._execute_task_thread,
            args=(task,),
            daemon=True,
            name=f"Task-{task.id[:8]}",
        )
        with self._lock:
            self._task_threads[task.id] = thread
        thread.start()

    def _execute_task_thread(self, task: Task) -> None:
        """Run one task and unregister the worker thread when done."""
        try:
            self._execute_task_sync(task)
        finally:
            with self._lock:
                self._task_threads.pop(task.id, None)

    def wait_for_all(self, timeout: float = 5.0) -> None:
        """Wait for currently running task threads to finish.

        Used by graceful shutdown and tests to prevent SQLite tempdirs from being
        deleted while background task threads still hold storage references.
        """
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                threads = list(self._task_threads.values())
            if not threads:
                return
            remaining = max(0.0, deadline - time.monotonic())
            if remaining <= 0:
                return
            for thread in threads:
                thread.join(timeout=min(remaining, 0.1))

    def _publish_task_event(self, task: Task, event_type: str, extra: dict | None = None) -> None:
        """Publish a task lifecycle event to the event bus."""
        bus = get_bus()
        started = getattr(task, "started_at", None) or ""
        ended = getattr(task, "ended_at", None) or ""
        duration_ms = 0
        if started and ended:
            try:
                from datetime import datetime

                s = datetime.fromisoformat(started)
                e = datetime.fromisoformat(ended)
                duration_ms = int((e - s).total_seconds() * 1000)
            except Exception:
                pass
        if event_type == "task_state_changed":
            bus.publish(
                TaskStateChanged(
                    task_id=task.id,
                    task_type=task.type.value,
                    operation=task.operation,
                    old_status="pending",
                    new_status=task.status.value,
                )
            )
        elif event_type == "task_completed":
            bus.publish(
                TaskCompleted(
                    task_id=task.id,
                    task_type=task.type.value,
                    operation=task.operation,
                    duration_ms=duration_ms,
                )
            )
        elif event_type == "task_failed":
            bus.publish(
                TaskFailed(
                    task_id=task.id,
                    task_type=task.type.value,
                    operation=task.operation,
                    error=task.error or "",
                    duration_ms=duration_ms,
                )
            )

    def _execute_task_sync(self, task: Task) -> None:
        """Execute task synchronously with error handling."""
        try:
            # Check if task is cancelled
            if self._is_cancelled(task.id):
                log.info("Task %s cancelled before execution", task.id)
                return

            # Transition to running
            task.transition_to(TaskStatus.RUNNING)
            self.storage.update_task(task)
            self._publish_task_event(task, "task_state_changed")

            # Execute the task operation
            result = self._execute_operation(task)

            # Check if cancelled during execution
            if self._is_cancelled(task.id):
                task.transition_to(TaskStatus.CANCELLED)
                self.storage.update_task(task)
                log.info("Task %s cancelled during execution", task.id)
                self._publish_task_event(task, "task_state_changed")
                return

            # Mark as completed
            task.result = result
            task.transition_to(TaskStatus.COMPLETED)
            self.storage.update_task(task)
            log.info("Task %s completed successfully", task.id)
            self._publish_task_event(task, "task_completed")

        except Exception as e:
            log.error("Task %s failed: %s", task.id, e)
            task.error = str(e)
            task.transition_to(TaskStatus.FAILED)

            # Schedule retry if applicable
            if task.should_retry():
                task.retry_count += 1
                task.next_retry_at = task.calculate_next_retry()
                log.info(
                    "Task %s will retry (attempt %d/%d) at %s",
                    task.id,
                    task.retry_count,
                    task.max_retries,
                    task.next_retry_at,
                )

            self.storage.update_task(task)
            self._publish_task_event(task, "task_failed")

    def _execute_operation(self, task: Task) -> dict[str, Any]:
        """Execute the task operation based on type."""
        if task.type == TaskType.RUN:
            # Check if this is an eval operation
            if task.operation == "eval":
                return self._execute_eval(task)
            return self._execute_run(task)
        elif task.type == TaskType.TRACE:
            return self._execute_trace(task)
        elif task.type == TaskType.AUDIT:
            return self._execute_audit(task)
        else:
            raise ValueError(f"Unknown task type: {task.type}")

    def _execute_run(self, task: Task) -> dict[str, Any]:
        """Execute a run task using runtime routing."""
        import asyncio
        from pathlib import Path

        from ..orchestration import runtime_router
        from ..storage.jsonl import JsonlTraceStore

        log.info("Executing run task: %s", task.operation)

        workflow_id = task.params.get("workflow_id", task.operation)
        workspace = Path(task.params.get("workspace", "."))
        runtime = task.params.get("runtime", "auto")
        allow_paid_calls = task.params.get("allow_paid_calls", False)

        routed = runtime_router.resolve(workspace, runtime, allow_paid_calls=allow_paid_calls)
        coro = routed.adapter.run_workflow(workflow_id, task.params)

        # Adapter.run_workflow is async; run in a fresh event loop in this thread
        run = asyncio.run(coro)

        store = JsonlTraceStore(workspace / ".arc" / "traces")
        store.save(run)

        # B2P-19: write a keyed (HMAC) audit checkpoint for this run path (no-op without a key).
        try:
            from ..audit.run_keyed_audit import write_run_keyed_audit

            write_run_keyed_audit(
                run.id,
                status=run.status.value,
                workflow_id=run.workflow_id,
                event_count=len(run.events),
                workspace_root=workspace,
            )
        except Exception:  # noqa: BLE001 - audit is best-effort; never break the run
            log.debug("keyed run audit checkpoint skipped", exc_info=True)

        # B2P-12: opt-in memory extraction from the run path (redaction-first; default off via env).
        # The extractor applies the canonical Redactor before building memory nodes, so no raw
        # secret/PII text enters the memory graph. Enable with ARC_MEMORY_AUTO_EXTRACT=1.
        if os.environ.get("ARC_MEMORY_AUTO_EXTRACT") == "1":
            try:
                from ..memory_graph.store import MemoryGraphStore, extract_memories_from_runs

                snapshot = extract_memories_from_runs(workspace / ".arc" / "traces", limit=5)
                MemoryGraphStore(workspace / ".arc" / "memory" / "graph.json").merge(snapshot)
            except Exception:  # noqa: BLE001 - memory extraction is best-effort; never break the run
                log.debug("memory extraction skipped", exc_info=True)

        return {
            "run_id": run.id,
            "status": run.status.value,
            "workflow_id": run.workflow_id,
            "event_count": len(run.events),
        }

    def _execute_trace(self, task: Task) -> dict[str, Any]:
        """Execute a trace task — load an existing run and return stats."""
        from pathlib import Path

        from ..storage.jsonl import JsonlTraceStore

        log.info("Executing trace task: %s", task.operation)

        workspace = Path(task.params.get("workspace", "."))
        run_id = task.params.get("run_id", task.operation)
        store = JsonlTraceStore(workspace / ".arc" / "traces")
        run = store.load(run_id)

        if run is None:
            return {
                "run_id": run_id,
                "status": "not_found",
                "events_count": 0,
                "first_event": None,
                "last_event": None,
            }

        events = run.events
        first_event = events[0].timestamp if events else None
        last_event = events[-1].timestamp if events else None

        return {
            "run_id": run_id,
            "status": run.status.value,
            "events_count": len(events),
            "first_event": first_event,
            "last_event": last_event,
        }

    def _execute_audit(self, task: Task) -> dict[str, Any]:
        """Execute an audit task — verify audit chain on an existing run."""
        from pathlib import Path

        from ..audit.streaming_verifier import StreamingAuditVerifier
        from ..storage.jsonl import JsonlTraceStore

        log.info("Executing audit task: %s", task.operation)

        workspace = Path(task.params.get("workspace", "."))
        run_id = task.params.get("run_id", task.operation)
        store = JsonlTraceStore(workspace / ".arc" / "traces")
        run = store.load(run_id)

        if run is None:
            return {
                "run_id": run_id,
                "status": "not_found",
                "verified": False,
                "records_checked": 0,
            }

        audit_path = run.audit_path
        if not audit_path:
            return {
                "run_id": run_id,
                "status": "no_audit_chain",
                "verified": False,
                "records_checked": 0,
            }

        verifier = StreamingAuditVerifier()
        result = verifier.verify_auto(Path(audit_path))

        return {
            "run_id": run_id,
            "status": "completed",
            "verified": result.ok,
            "mode": result.mode,
            "records_checked": result.records_checked,
            "reason": result.reason,
            "duration_ms": result.duration_ms,
        }

    def _execute_eval(self, task: Task) -> dict[str, Any]:
        """Execute an eval task: load goldens, run eval, save artifacts, publish event."""
        from pathlib import Path

        from ..evals.artifact import EvalArtifactStore, build_artifact
        from ..evals.golden import GoldenTrace, eval_run as do_eval
        from ..storage.jsonl import JsonlTraceStore

        log.info("Executing eval task: %s", task.operation)
        workspace = Path(task.params.get("workspace", "."))
        run_id = task.params.get("run_id", task.operation)
        golden_dir = task.params.get("golden_dir", "")

        store = JsonlTraceStore(workspace / ".arc" / "traces")
        run = store.load(run_id)

        if run is None:
            return {"run_id": run_id, "status": "not_found", "eval_completed": False}

        # Load goldens
        goldens: list[GoldenTrace] = []
        if golden_dir:
            import json as _json_mod

            gd = Path(golden_dir)
            if gd.is_dir():
                for gf in sorted(gd.glob("*.json")):
                    try:
                        raw = _json_mod.loads(gf.read_text())
                        if isinstance(raw, dict):
                            goldens.append(GoldenTrace.model_validate(raw))
                        elif isinstance(raw, list):
                            for item in raw:
                                goldens.append(GoldenTrace.model_validate(item))
                    except Exception:
                        continue

        if not goldens:
            from ..evals.golden import list_goldens

            goldens = list_goldens(workspace)

        if not goldens:
            return {"run_id": run_id, "status": "no_goldens", "eval_completed": False}

        art_store = EvalArtifactStore(workspace)
        all_results = []
        for golden in goldens:
            result = do_eval(run, golden)
            all_results.append(result.model_dump())
            art_store.write(build_artifact(run_id, golden.id, [result.model_dump()]))

        passed = sum(1 for r in all_results if r.get("passed"))
        total = len(all_results)
        pass_rate = round(passed / total, 4) if total > 0 else 0.0
        failures_count = total - passed

        # Publish EvalCompleted event
        try:
            from ..events.bus import get_bus
            from ..events.types import EvalCompleted

            bus = get_bus()
            bus.publish(
                EvalCompleted(
                    run_id=run_id,
                    pass_rate=pass_rate,
                    total=total,
                    failures_count=failures_count,
                )
            )
        except Exception:
            log.warning("Failed to publish EvalCompleted event", exc_info=True)

        return {
            "run_id": run_id,
            "status": "completed",
            "eval_completed": True,
            "passed": passed,
            "total": total,
            "pass_rate": pass_rate,
            "failures_count": failures_count,
            "artifacts_saved": len(all_results),
        }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task. Returns True if cancelled."""
        task = self.storage.get_task(task_id)
        if not task:
            log.warning("Task not found: %s", task_id)
            return False

        # Check if task can be cancelled
        if task.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
            log.warning("Task %s already in terminal state: %s", task_id, task.status)
            return False

        # Set cancel flag
        with self._lock:
            if task_id not in self._cancel_flags:
                self._cancel_flags[task_id] = threading.Event()
            self._cancel_flags[task_id].set()

        # Update task status
        if task.can_transition_to(TaskStatus.CANCELLED):
            task.transition_to(TaskStatus.CANCELLED)
            self.storage.update_task(task)
            log.info("Task %s cancelled", task_id)
            return True

        return False

    def _is_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled."""
        with self._lock:
            if task_id in self._cancel_flags:
                return self._cancel_flags[task_id].is_set()
        return False

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current task status."""
        return self.storage.get_task(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 100,
    ) -> list[Task]:
        """List tasks with optional filters."""
        return self.storage.list_tasks(status=status, task_type=task_type, limit=limit)
