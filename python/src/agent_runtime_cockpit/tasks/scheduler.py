"""Daemon task scheduler — local background task runner with budget caps (R92).

Provides scheduled/recurring task execution in the local daemon.
All tasks are sandboxed, budget-capped, and audited. No cloud execution.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from .models import Task, TaskStatus
from .storage import TaskStorage

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduleConfig:
    interval_seconds: int = 60
    max_concurrent: int = 5
    budget_tokens: Optional[int] = None
    budget_cost_usd: Optional[float] = None
    enabled: bool = True
    task_timeout_seconds: float = 60.0


class TaskScheduler:
    """Local background task scheduler with budget enforcement.

    Runs scheduled tasks in the daemon process. All execution stays local.
    """

    def __init__(
        self,
        storage: TaskStorage,
        config: Optional[ScheduleConfig] = None,
    ) -> None:
        self._storage = storage
        self._config = config or ScheduleConfig()
        self._running = False
        self._scheduled_tasks: dict[str, dict[str, Any]] = {}
        self._tokens_used: int = 0
        self._cost_used: float = 0.0
        self._load_scheduled_tasks()

    def _load_scheduled_tasks(self) -> None:
        """Load scheduled tasks from storage on initialization."""
        try:
            tasks = self._storage.list_tasks(status=TaskStatus.PENDING)
            for task in tasks:
                # Use default interval for loaded tasks
                interval = self._config.interval_seconds
                self._scheduled_tasks[task.id] = {
                    "task": task,
                    "interval": interval,
                    "last_run": None,
                    "next_run": time.time() + interval,
                }
            if tasks:
                log.info("Loaded %d scheduled tasks from storage", len(tasks))
        except Exception as e:
            log.warning("Failed to load scheduled tasks from storage: %s", e)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def scheduled_count(self) -> int:
        return len(self._scheduled_tasks)

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def cost_used(self) -> float:
        return self._cost_used

    def schedule(
        self,
        task: Task,
        cron_expr: Optional[str] = None,
        interval_seconds: Optional[int] = None,
    ) -> str:
        """Schedule a task for recurring execution.

        Args:
            task: The task to schedule.
            cron_expr: Cron expression (e.g., "0 * * * *" for hourly). Not implemented in baseline.
            interval_seconds: Simple interval in seconds. Overrides cron_expr.

        Returns:
            The task ID.
        """
        if cron_expr:
            log.warning("Cron expressions not implemented in baseline; using interval instead.")

        interval = interval_seconds or self._config.interval_seconds
        self._scheduled_tasks[task.id] = {
            "task": task,
            "interval": interval,
            "last_run": None,
            "next_run": time.time() + interval,
        }
        self._storage.create_task(task)
        log.info(
            "Task scheduled: %s (interval=%ds, type=%s, operation=%s)",
            task.id,
            interval,
            task.type.value,
            task.operation,
        )
        return task.id

    def unschedule(self, task_id: str) -> bool:
        """Remove a task from the schedule. Returns True if removed."""
        if task_id in self._scheduled_tasks:
            del self._scheduled_tasks[task_id]
            log.info("Task unscheduled: %s", task_id)
            return True
        return False

    def list_scheduled(self) -> list[dict[str, Any]]:
        """List all scheduled tasks with their schedule info."""
        result = []
        for task_id, info in self._scheduled_tasks.items():
            task = info["task"]
            result.append(
                {
                    "task_id": task_id,
                    "type": task.type.value,
                    "operation": task.operation,
                    "interval_seconds": info["interval"],
                    "last_run": info["last_run"],
                    "next_run": info["next_run"],
                    "status": task.status.value,
                }
            )
        return result

    def check_budget(self) -> dict[str, Any]:
        """Check current budget usage against limits."""
        return {
            "tokens_used": self._tokens_used,
            "tokens_limit": self._config.budget_tokens,
            "tokens_exhausted": (
                self._config.budget_tokens is not None
                and self._tokens_used >= self._config.budget_tokens
            ),
            "cost_used": self._cost_used,
            "cost_limit": self._config.budget_cost_usd,
            "cost_exhausted": (
                self._config.budget_cost_usd is not None
                and self._cost_used >= self._config.budget_cost_usd
            ),
        }

    def _budget_allows(self) -> bool:
        """Check if budget allows more execution."""
        if self._config.budget_tokens is not None:
            if self._tokens_used >= self._config.budget_tokens:
                log.warning(
                    "Token budget exhausted: %d >= %d",
                    self._tokens_used,
                    self._config.budget_tokens,
                )
                return False
        if self._config.budget_cost_usd is not None:
            if self._cost_used >= self._config.budget_cost_usd:
                log.warning(
                    "Cost budget exhausted: %.4f >= %.4f",
                    self._cost_used,
                    self._config.budget_cost_usd,
                )
                return False
        return True

    def record_usage(self, tokens: int = 0, cost: float = 0.0) -> None:
        """Record token/cost usage from a completed task."""
        self._tokens_used += tokens
        self._cost_used += cost

    def reset_budget(self) -> None:
        """Reset budget counters (e.g., at start of new billing period)."""
        self._tokens_used = 0
        self._cost_used = 0
        log.info("Budget counters reset")

    async def run_once(self) -> list[str]:
        """Run one scheduling cycle. Returns list of task IDs that were executed."""
        if not self._config.enabled:
            return []

        if not self._budget_allows():
            return []

        now = time.time()
        executed = []

        for task_id, info in list(self._scheduled_tasks.items()):
            if now >= info["next_run"]:
                task = info["task"]

                if task.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
                    continue

                executed.append(task_id)
                info["last_run"] = datetime.now(timezone.utc).isoformat()
                info["next_run"] = now + info["interval"]

                log.info("Scheduler executing task: %s", task_id)

        return executed

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "running": self._running,
            "scheduled_count": self.scheduled_count,
            "config": {
                "interval_seconds": self._config.interval_seconds,
                "max_concurrent": self._config.max_concurrent,
                "budget_tokens": self._config.budget_tokens,
                "budget_cost_usd": self._config.budget_cost_usd,
                "enabled": self._config.enabled,
                "task_timeout_seconds": self._config.task_timeout_seconds,
            },
            "budget": self.check_budget(),
        }


__all__ = ["TaskScheduler", "ScheduleConfig"]
