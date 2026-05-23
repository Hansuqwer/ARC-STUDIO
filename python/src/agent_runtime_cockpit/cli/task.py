"""Task commands: create, status, list, cancel (Phase 27)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import task_app


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
    import json as json_mod

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
    """Get status of a task."""
    _setup_logging(debug)

    from ..tasks import TaskExecutor, TaskStorage

    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    executor = TaskExecutor(storage)
    task = executor.get_task_status(task_id)

    if not task:
        _out(
            err(ArcErrorCode.RUN_NOT_FOUND, f"Task not found: {task_id}"),
            json_output,
        )
        raise typer.Exit(1)

    payload = {
        "task_id": task.id,
        "type": task.type.value,
        "operation": task.operation,
        "status": task.status.value,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "ended_at": task.ended_at,
        "expires_at": task.expires_at,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "result": task.result,
        "error": task.error,
    }
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        status_color = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
        }.get(task.status.value, "white")

        console.print(f"Task: [bold]{task.id}[/bold]")
        console.print(f"Type: {task.type.value}, Operation: {task.operation}")
        console.print(
            f"Status: [bold {status_color}]{task.status.value.upper()}[/bold {status_color}]"
        )
        console.print(f"Created: {task.created_at}")
        if task.started_at:
            console.print(f"Started: {task.started_at}")
        if task.ended_at:
            console.print(f"Ended: {task.ended_at}")
        if task.retry_count > 0:
            console.print(f"Retries: {task.retry_count}/{task.max_retries}")
        if task.result:
            console.print(f"Result: {task.result}")
        if task.error:
            console.print(f"[red]Error: {task.error}[/red]")


@task_app.command("list")
def task_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of tasks to list"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List tasks with optional filters."""
    _setup_logging(debug)

    from ..tasks import TaskExecutor, TaskStatus, TaskStorage, TaskType

    # Validate filters
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Invalid status: {status}. Must be pending, running, completed, failed, or cancelled.",
                ),
                json_output,
            )
            raise typer.Exit(1)

    type_enum = None
    if task_type:
        try:
            type_enum = TaskType(task_type)
        except ValueError:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Invalid type: {task_type}. Must be run, trace, or audit.",
                ),
                json_output,
            )
            raise typer.Exit(1)

    # List tasks
    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    executor = TaskExecutor(storage)
    tasks = executor.list_tasks(status=status_enum, task_type=type_enum, limit=limit)

    payload = {
        "count": len(tasks),
        "filters": {"status": status, "type": task_type, "limit": limit},
        "tasks": [
            {
                "task_id": t.id,
                "type": t.type.value,
                "operation": t.operation,
                "status": t.status.value,
                "created_at": t.created_at,
                "started_at": t.started_at,
                "ended_at": t.ended_at,
                "retry_count": t.retry_count,
            }
            for t in tasks
        ],
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

        console.print(f"Tasks{filter_str}: {len(tasks)} found")
        for t in tasks:
            status_color = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
                "cancelled": "gray",
            }.get(t.status.value, "white")
            console.print(
                f"  [{status_color}]{t.status.value:10}[/{status_color}] "
                f"{t.id[:8]}... {t.type.value:5} {t.operation:20} "
                f"(created: {t.created_at})"
            )


@task_app.command("cancel")
def task_cancel(
    task_id: str = typer.Argument(..., help="Task ID to cancel"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Cancel a running or pending task."""
    _setup_logging(debug)

    from ..tasks import TaskExecutor, TaskStorage

    storage = TaskStorage(Path.cwd() / ".arc" / "tasks.db")
    executor = TaskExecutor(storage)
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
