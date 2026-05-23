"""Task execution engine with retry logic and async support."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from agent_runtime_cockpit.tasks.models import Task, TaskStatus, TaskType
from agent_runtime_cockpit.tasks.storage import TaskStorage

log = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks asynchronously with retry support."""

    def __init__(self, storage: TaskStorage) -> None:
        self.storage = storage
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
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
            target=self._execute_task_sync,
            args=(task,),
            daemon=True,
            name=f"Task-{task.id[:8]}",
        )
        thread.start()

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

            # Execute the task operation
            result = self._execute_operation(task)

            # Check if cancelled during execution
            if self._is_cancelled(task.id):
                task.transition_to(TaskStatus.CANCELLED)
                self.storage.update_task(task)
                log.info("Task %s cancelled during execution", task.id)
                return

            # Mark as completed
            task.result = result
            task.transition_to(TaskStatus.COMPLETED)
            self.storage.update_task(task)
            log.info("Task %s completed successfully", task.id)

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

    def _execute_operation(self, task: Task) -> dict[str, Any]:
        """Execute the task operation based on type."""
        if task.type == TaskType.RUN:
            return self._execute_run(task)
        elif task.type == TaskType.TRACE:
            return self._execute_trace(task)
        elif task.type == TaskType.AUDIT:
            return self._execute_audit(task)
        else:
            raise ValueError(f"Unknown task type: {task.type}")

    def _execute_run(self, task: Task) -> dict[str, Any]:
        """Execute a run task."""
        # TODO: Integrate with actual run execution
        # For now, return a placeholder result
        log.info("Executing run task: %s", task.operation)

        # Simulate work
        time.sleep(1.0)

        return {
            "run_id": f"run_{task.id[:8]}",
            "status": "completed",
            "audit_chain_ref": None,
            "cost_breakdown": {"total": 0.0},
        }

    def _execute_trace(self, task: Task) -> dict[str, Any]:
        """Execute a trace task."""
        # TODO: Integrate with actual trace execution
        log.info("Executing trace task: %s", task.operation)

        # Simulate work
        time.sleep(0.5)

        return {
            "trace_id": f"trace_{task.id[:8]}",
            "status": "completed",
            "events_count": 0,
        }

    def _execute_audit(self, task: Task) -> dict[str, Any]:
        """Execute an audit task."""
        # TODO: Integrate with actual audit execution
        log.info("Executing audit task: %s", task.operation)

        # Simulate work
        time.sleep(0.5)

        return {
            "audit_id": f"audit_{task.id[:8]}",
            "status": "completed",
            "verified": True,
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
