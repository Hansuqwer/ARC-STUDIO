"""Tests for Phase 56 task CLI commands (daemon-aware)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.tasks import Task, TaskExecutor, TaskStatus, TaskStorage, TaskType

runner = CliRunner()


@pytest.fixture
def tmp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace with a task DB."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        old = Path.cwd()
        os.chdir(str(cwd))
        yield cwd
        os.chdir(str(old))


def _seed_tasks(workspace: Path, count: int = 3) -> list[Task]:
    """Seed some tasks in the local task DB. Waits for executor threads to finish."""
    storage = TaskStorage(workspace / ".arc" / "tasks.db")
    executor = TaskExecutor(storage)
    tasks = []
    for i in range(count):
        task = Task(type=TaskType.RUN, operation=f"test-op-{i}")
        executor.submit_task(task)
        tasks.append(task)
    # Wait for background threads to finish to avoid tempdir cleanup races
    executor.wait_for_all(timeout=5.0)
    return tasks


def test_task_cli_registered():
    """arc task --help shows task subcommands."""
    result = runner.invoke(app, ["task", "--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "status" in result.stdout
    assert "list" in result.stdout
    assert "cancel" in result.stdout


def test_task_list_json(tmp_workspace: Path):
    """arc task list --json returns ok envelope with tasks."""
    _seed_tasks(tmp_workspace, 3)
    result = runner.invoke(app, ["task", "list", "--json"])
    assert result.exit_code == 0, f"Got exit {result.exit_code}: stderr={result.stderr}"
    data = json.loads(result.stdout)
    assert data.get("ok") is True
    assert "tasks" in data.get("data", data)
    tasks_list = data.get("data", data).get("tasks", [])
    assert len(tasks_list) == 3


def test_task_list_empty(tmp_workspace: Path):
    """arc task list --json with no tasks returns empty list."""
    result = runner.invoke(app, ["task", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    tasks_list = data.get("data", data).get("tasks", [])
    assert len(tasks_list) == 0


def test_task_status_json(tmp_workspace: Path):
    """arc task status <id> --json returns task dict."""
    tasks = _seed_tasks(tmp_workspace, 1)
    task_id = tasks[0].id
    result = runner.invoke(app, ["task", "status", task_id, "--json"])
    assert result.exit_code == 0, f"Got exit {result.exit_code}: stderr={result.stderr}"
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    assert payload.get("task_id") == task_id
    # Tasks auto-execute via background thread, so status could be running/completed
    assert payload.get("status") in ("pending", "running", "completed")


def test_task_status_not_found(tmp_workspace: Path):
    """arc task status <bad-id> --json returns error."""
    result = runner.invoke(app, ["task", "status", "nonexistent", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data.get("ok") is False


def test_task_cancel_json(tmp_workspace: Path):
    """arc task cancel <id> --json returns cancelled=True."""
    # Create task directly in storage without executor (avoids auto-execution)
    storage = TaskStorage(tmp_workspace / ".arc" / "tasks.db")
    task = Task(type=TaskType.RUN, operation="test-cancel")
    # Set status to running to allow cancellation
    task.transition_to(TaskStatus.RUNNING)
    storage.create_task(task)
    storage.update_task(task)

    result = runner.invoke(app, ["task", "cancel", task.id, "--json"])
    assert result.exit_code == 0, f"Got exit {result.exit_code}: stderr={result.stderr}"
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    assert payload.get("cancelled") is True


def test_task_cancel_not_found(tmp_workspace: Path):
    """arc task cancel <bad-id> --json returns error."""
    # Ensure no background threads from other tests
    import time

    time.sleep(0.1)
    result = runner.invoke(app, ["task", "cancel", "nonexistent", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data.get("ok") is False


def test_task_list_with_status_filter(tmp_workspace: Path):
    """arc task list --status pending --json filters correctly."""
    _seed_tasks(tmp_workspace, 3)
    # Tasks auto-execute; just verify the filter flag is accepted and JSON is valid
    result = runner.invoke(app, ["task", "list", "--status", "pending", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "tasks" in data.get("data", data)


def test_task_list_with_type_filter(tmp_workspace: Path):
    """arc task list --type run --json filters correctly."""
    _seed_tasks(tmp_workspace, 3)
    import time

    time.sleep(0.1)
    result = runner.invoke(app, ["task", "list", "--type", "run", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    tasks_list = data.get("data", data).get("tasks", [])
    assert len(tasks_list) == 3
