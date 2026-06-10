"""Task commands: create, status, list, cancel (Phase 27 / Phase 56)."""

from __future__ import annotations

import json as json_mod
import os
from pathlib import Path
from typing import Any, Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import task_app


def _daemon_base_url() -> Optional[str]:
    """Get daemon base URL from env, or None."""
    return os.environ.get("ARC_PYTHON_DAEMON_URL") or None


def _try_daemon_get(path: str) -> Optional[dict[str, Any]]:
    """Try to GET from daemon. Returns parsed JSON or None on failure."""
    base = _daemon_base_url()
    if not base:
        return None
    try:
        import httpx

        resp = httpx.get(f"{base.rstrip('/')}{path}", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and data.get("ok"):
                return data.get("data") or data
        return None
    except Exception:
        return None


def _try_daemon_delete(path: str) -> Optional[dict[str, Any]]:
    """Try to DELETE from daemon. Returns parsed JSON or None on failure."""
    base = _daemon_base_url()
    if not base:
        return None
    try:
        import httpx

        resp = httpx.delete(f"{base.rstrip('/')}{path}", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and data.get("ok"):
                return data.get("data") or data
        return None
    except Exception:
        return None


def _get_local_executor() -> Any:
    """Get local TaskExecutor."""
    from ..tasks import TaskExecutor, TaskStorage

    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    return TaskExecutor(storage)


def _task_to_payload(task: Any) -> dict[str, Any]:
    """Convert a Task to a dict payload."""
    return {
        "task_id": task["id"] if isinstance(task, dict) else task.id,
        "type": task["type"] if isinstance(task, dict) else task.type.value,
        "operation": task["operation"] if isinstance(task, dict) else task.operation,
        "status": task["status"] if isinstance(task, dict) else task.status.value,
        "created_at": task["created_at"] if isinstance(task, dict) else task.created_at,
        "started_at": task.get("started_at") if isinstance(task, dict) else task.started_at,
        "ended_at": task.get("ended_at") if isinstance(task, dict) else task.ended_at,
        "expires_at": task["expires_at"] if isinstance(task, dict) else task.expires_at,
        "retry_count": task.get("retry_count", 0) if isinstance(task, dict) else task.retry_count,
        "max_retries": task.get("max_retries", 3) if isinstance(task, dict) else task.max_retries,
        "result": task.get("result") if isinstance(task, dict) else task.result,
        "error": task.get("error") if isinstance(task, dict) else task.error,
    }


@task_app.command("create")
def task_create(
    operation: str = typer.Argument(
        ..., help="Operation to execute (e.g., 'run', 'trace', 'audit')"
    ),
    task_type: str = typer.Option("run", "--type", "-t", help="Task type: run, trace, or audit"),
    params: str = typer.Option("{}", "--params", "-p", help="JSON parameters for the operation"),
    max_retries: int = typer.Option(3, "--max-retries", help="Maximum retry attempts"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Create a new async task for execution."""
    _setup_logging(debug)

    from ..tasks import Task, TaskExecutor, TaskStorage, TaskType

    # Validate task type
    try:
        task_type_enum = TaskType(task_type)
    except ValueError:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid task type: {task_type}. Must be run, trace, or audit.",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Parse params
    try:
        params_dict = json_mod.loads(params)
    except json_mod.JSONDecodeError as e:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Invalid JSON params: {e}"),
            json_output,
        )
        raise typer.Exit(1)

    # Create task
    task = Task(
        type=task_type_enum,
        operation=operation,
        params=params_dict,
        max_retries=max_retries,
    )

    # Submit task
    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    executor = TaskExecutor(storage)
    task_id = executor.submit_task(task)

    payload = {
        "task_id": task_id,
        "type": task.type.value,
        "operation": task.operation,
        "status": task.status.value,
        "created_at": task.created_at,
        "expires_at": task.expires_at,
    }
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        console.print(f"Task created: [bold]{task_id}[/bold]")
        console.print(f"Type: {task.type.value}, Operation: {task.operation}")
        console.print(f"Status: [yellow]{task.status.value}[/yellow]")


@task_app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="Task ID to check status for"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Get status of a task.

    Tries daemon HTTP API first; falls back to local TaskStorage.
    """
    _setup_logging(debug)

    # Try daemon first
    daemon_result = _try_daemon_get(f"/api/tasks/{task_id}")
    if daemon_result is not None:
        task_data = daemon_result.get("data") or daemon_result
        payload = _task_to_payload(task_data)
        _out(ok(payload), json_output)
        if not json_output:
            from ._app import console

            status_color = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
                "cancelled": "gray",
            }.get(payload["status"], "white")
            console.print(f"Task: [bold]{payload['task_id']}[/bold]")
            console.print(f"Type: {payload['type']}, Operation: {payload['operation']}")
            console.print(
                f"Status: [bold {status_color}]{payload['status'].upper()}[/bold {status_color}]"
            )
            console.print(f"Created: {payload['created_at']}")
            if payload.get("started_at"):
                console.print(f"Started: {payload['started_at']}")
            if payload.get("ended_at"):
                console.print(f"Ended: {payload['ended_at']}")
            if payload.get("retry_count", 0) > 0:
                console.print(f"Retries: {payload['retry_count']}/{payload['max_retries']}")
            if payload.get("result"):
                console.print(f"Result: {payload['result']}")
            if payload.get("error"):
                console.print(f"[red]Error: {payload['error']}[/red]")
        return

    # Fallback: local storage
    executor = _get_local_executor()
    task = executor.get_task_status(task_id)

    if not task:
        _out(
            err(ArcErrorCode.RUN_NOT_FOUND, f"Task not found: {task_id}"),
            json_output,
        )
        raise typer.Exit(1)

    payload = _task_to_payload(task)
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        status_color = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
        }.get(payload["status"], "white")

        console.print(f"Task: [bold]{payload['task_id']}[/bold]")
        console.print(f"Type: {payload['type']}, Operation: {payload['operation']}")
        console.print(
            f"Status: [bold {status_color}]{payload['status'].upper()}[/bold {status_color}]"
        )
        console.print(f"Created: {payload['created_at']}")
        if payload.get("started_at"):
            console.print(f"Started: {payload['started_at']}")
        if payload.get("ended_at"):
            console.print(f"Ended: {payload['ended_at']}")
        if payload.get("retry_count", 0) > 0:
            console.print(f"Retries: {payload['retry_count']}/{payload['max_retries']}")
        if payload.get("result"):
            console.print(f"Result: {payload['result']}")
        if payload.get("error"):
            console.print(f"[red]Error: {payload['error']}[/red]")


@task_app.command("list")
def task_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of tasks to list"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List tasks with optional filters.

    Tries daemon HTTP API first; falls back to local TaskStorage.
    """
    _setup_logging(debug)

    from ..tasks import TaskStatus, TaskType

    # Validate filters
    status_val = None
    type_val = None
    if status:
        try:
            status_val = TaskStatus(status).value
        except ValueError:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Invalid status: {status}. Must be pending, running, completed, failed, or cancelled.",
                ),
                json_output,
            )
            raise typer.Exit(1)

    if task_type:
        try:
            type_val = TaskType(task_type).value
        except ValueError:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Invalid type: {task_type}. Must be run, trace, or audit.",
                ),
                json_output,
            )
            raise typer.Exit(1)

    # Try daemon first
    params = []
    if status_val:
        params.append(f"status={status_val}")
    if type_val:
        params.append(f"type={type_val}")
    params.append(f"limit={limit}")
    qs = "&".join(params)
    daemon_result = _try_daemon_get(f"/api/tasks?{qs}")

    if daemon_result is not None:
        raw_tasks = daemon_result.get("data") or daemon_result
        if isinstance(raw_tasks, list):
            tasks_data = raw_tasks
        elif isinstance(raw_tasks, dict) and "tasks" in raw_tasks:
            tasks_data = raw_tasks["tasks"]
        elif isinstance(raw_tasks, dict):
            tasks_data = [raw_tasks]
        else:
            tasks_data = []
    else:
        # Fallback: local storage
        executor = _get_local_executor()
        status_enum = TaskStatus(status_val) if status_val else None
        type_enum = TaskType(type_val) if type_val else None
        tasks_data = executor.list_tasks(status=status_enum, task_type=type_enum, limit=limit)

    payload = {
        "count": len(tasks_data),
        "filters": {"status": status, "type": task_type, "limit": limit},
        "tasks": [_task_to_payload(t) if not isinstance(t, dict) else t for t in tasks_data],
    }
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        filter_desc = []
        if status:
            filter_desc.append(f"status={status}")
        if task_type:
            filter_desc.append(f"type={task_type}")
        filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""

        console.print(f"Tasks{filter_str}: {len(tasks_data)} found")
        for t in tasks_data:
            tinfo = t if isinstance(t, dict) else _task_to_payload(t)
            status_color = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
                "cancelled": "gray",
            }.get(tinfo["status"], "white")
            console.print(
                f"  [{status_color}]{tinfo['status']:10}[/{status_color}] "
                f"{tinfo['task_id'][:8]}... {tinfo['type']:5} {tinfo['operation']:20} "
                f"(created: {tinfo['created_at']})"
            )


@task_app.command("cancel")
def task_cancel(
    task_id: str = typer.Argument(..., help="Task ID to cancel"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Cancel a running or pending task.

    Tries daemon HTTP API first; falls back to local TaskStorage.
    """
    _setup_logging(debug)

    # Try daemon first
    daemon_result = _try_daemon_delete(f"/api/tasks/{task_id}")
    if daemon_result is not None:
        cancelled = daemon_result.get("cancelled", True)
        if cancelled:
            payload = {"task_id": task_id, "cancelled": True}
            _out(ok(payload), json_output)
            if not json_output:
                from ._app import console

                console.print(f"Task cancelled: [bold]{task_id}[/bold]")
            return

    # Fallback: local storage
    executor = _get_local_executor()
    cancelled = executor.cancel_task(task_id)

    if not cancelled:
        task = executor.get_task_status(task_id)
        if not task:
            _out(
                err(ArcErrorCode.RUN_NOT_FOUND, f"Task not found: {task_id}"),
                json_output,
            )
        else:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Task cannot be cancelled (status: {task.status.value})",
                ),
                json_output,
            )
        raise typer.Exit(1)

    payload = {"task_id": task_id, "cancelled": True}
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        console.print(f"Task cancelled: [bold]{task_id}[/bold]")


@task_app.command("schedule")
def task_schedule(
    operation: str = typer.Argument(..., help="Operation to schedule (e.g., 'run', 'trace')"),
    task_type: str = typer.Option("run", "--type", "-t", help="Task type: run, trace, or audit"),
    params: str = typer.Option("{}", "--params", "-p", help="JSON parameters"),
    interval: int = typer.Option(3600, "--interval", "-i", help="Interval in seconds"),
    budget_tokens: Optional[int] = typer.Option(None, "--budget-tokens", help="Token budget limit"),
    budget_cost: Optional[float] = typer.Option(
        None, "--budget-cost", help="Cost budget limit (USD)"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Schedule a task for recurring background execution (R92).

    Tasks run in the local daemon with budget caps. No cloud execution.
    """
    _setup_logging(debug)

    from ..tasks import ScheduleConfig, Task, TaskScheduler, TaskStorage, TaskType

    try:
        task_type_enum = TaskType(task_type)
    except ValueError:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid task type: {task_type}. Must be run, trace, or audit.",
            ),
            json_output,
        )
        raise typer.Exit(1)

    try:
        params_dict = json_mod.loads(params)
    except json_mod.JSONDecodeError as e:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid JSON params: {e}"), json_output)
        raise typer.Exit(1)

    task = Task(type=task_type_enum, operation=operation, params=params_dict)
    config = ScheduleConfig(
        interval_seconds=interval,
        budget_tokens=budget_tokens,
        budget_cost_usd=budget_cost,
    )
    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    scheduler = TaskScheduler(storage, config)
    task_id = scheduler.schedule(task, interval_seconds=interval)

    payload = {
        "task_id": task_id,
        "type": task.type.value,
        "operation": task.operation,
        "interval_seconds": interval,
        "budget_tokens": budget_tokens,
        "budget_cost_usd": budget_cost,
        "scheduled": True,
    }
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        console.print(f"Task scheduled: [bold]{task_id}[/bold]")
        console.print(f"Interval: {interval}s, Type: {task.type.value}, Operation: {operation}")


@task_app.command("unschedule")
def task_unschedule(
    task_id: str = typer.Argument(..., help="Task ID to unschedule"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Remove a task from the recurring schedule (R92).

    This is a destructive action that requires confirmation unless --yes is provided.
    """
    _setup_logging(debug)

    from ..tasks import TaskScheduler, TaskStorage

    if not yes and not json_output:
        from ._app import console

        console.print(
            f"[yellow]Warning:[/yellow] This will remove task '{task_id}' from the schedule."
        )
        if not typer.confirm("Are you sure?"):
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)

    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    scheduler = TaskScheduler(storage)
    removed = scheduler.unschedule(task_id)

    if not removed:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Scheduled task not found: {task_id}"), json_output)
        raise typer.Exit(1)

    payload = {"task_id": task_id, "unscheduled": True}
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        console.print(f"Task unscheduled: [bold]{task_id}[/bold]")


@task_app.command("scheduled")
def task_list_scheduled(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List all scheduled recurring tasks (R92)."""
    _setup_logging(debug)

    from ..tasks import TaskScheduler, TaskStorage

    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    scheduler = TaskScheduler(storage)
    scheduled = scheduler.list_scheduled()

    payload = {"count": len(scheduled), "scheduled": scheduled}
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        console.print(f"Scheduled tasks: {len(scheduled)}")
        for s in scheduled:
            console.print(
                f"  {s['task_id'][:8]}... {s['type']:5} {s['operation']:20} "
                f"(interval={s['interval_seconds']}s, next={s['next_run']})"
            )


@task_app.command("scheduler-stats")
def task_scheduler_stats(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show scheduler statistics and budget usage (R92)."""
    _setup_logging(debug)

    from ..tasks import TaskScheduler, TaskStorage

    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    scheduler = TaskScheduler(storage)
    stats = scheduler.get_stats()

    _out(ok(stats), json_output)

    if not json_output:
        from ._app import console

        console.print("Scheduler Statistics:")
        console.print(f"  Running: {stats['running']}")
        console.print(f"  Scheduled: {stats['scheduled_count']}")
        budget = stats["budget"]
        console.print(f"  Tokens used: {budget['tokens_used']} / {budget['tokens_limit']}")
        console.print(f"  Cost used: ${budget['cost_used']:.4f} / ${budget['cost_limit']}")
