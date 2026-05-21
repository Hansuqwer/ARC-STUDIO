from __future__ import annotations

import time
from datetime import datetime, timezone

from ..config import ExecutionMode
from ..models import (
    SwarmTask,
    TaskStatus,
    WorkerResult,
)


def worker_execute(
    task: SwarmTask,
    mode: ExecutionMode = ExecutionMode.fake_offline,
    timeout: float = 30.0,
) -> WorkerResult:
    started = datetime.now(timezone.utc)
    t0 = time.time()

    if mode == ExecutionMode.fake_offline:
        output = f"Fake deterministic response for: {task.prompt[:80]}"
        elapsed = time.time() - t0
        if elapsed > timeout:
            return WorkerResult(
                worker_id=task.assigned_agent_id or "unknown",
                task_id=task.id,
                output="",
                error="timeout",
                duration_seconds=elapsed,
                started_at=started,
            )
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output=output,
            duration_seconds=elapsed,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )

    elapsed = time.time() - t0
    return WorkerResult(
        worker_id=task.assigned_agent_id or "unknown",
        task_id=task.id,
        output="",
        error=f"unsupported mode: {mode}",
        duration_seconds=elapsed,
        started_at=started,
    )


def process_worker_results(
    tasks: list[SwarmTask],
    results: list[WorkerResult],
) -> list[SwarmTask]:
    result_map = {r.task_id: r for r in results}
    for task in tasks:
        if task.id in result_map:
            task.result = result_map[task.id]
            if result_map[task.id].error:
                task.status = TaskStatus.failed
            else:
                task.status = TaskStatus.completed
            task.updated_at = datetime.now(timezone.utc)
    return tasks
