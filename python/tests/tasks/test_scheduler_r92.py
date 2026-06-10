"""Tests for ARC Daemon Tasks scheduler (R92, Phase 317)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.tasks import (
    ScheduleConfig,
    Task,
    TaskScheduler,
    TaskStorage,
    TaskType,
)


@pytest.fixture
def storage(tmp_path: Path) -> TaskStorage:
    db_path = tmp_path / "tasks.db"
    s = TaskStorage(db_path)
    s.init_db()
    return s


@pytest.fixture
def scheduler(storage: TaskStorage) -> TaskScheduler:
    config = ScheduleConfig(
        interval_seconds=60,
        max_concurrent=3,
        budget_tokens=10000,
        budget_cost_usd=5.0,
    )
    return TaskScheduler(storage, config)


@pytest.fixture
def sample_task() -> Task:
    return Task(
        type=TaskType.RUN,
        operation="test-workflow",
        params={"workspace": "/tmp/test"},
    )


class TestScheduleConfig:
    def test_default_config(self) -> None:
        config = ScheduleConfig()
        assert config.interval_seconds == 60
        assert config.max_concurrent == 5
        assert config.budget_tokens is None
        assert config.budget_cost_usd is None
        assert config.enabled is True

    def test_custom_config(self) -> None:
        config = ScheduleConfig(
            interval_seconds=300,
            max_concurrent=10,
            budget_tokens=50000,
            budget_cost_usd=10.0,
        )
        assert config.interval_seconds == 300
        assert config.budget_tokens == 50000


class TestTaskScheduler:
    def test_schedule_task(self, scheduler: TaskScheduler, sample_task: Task) -> None:
        task_id = scheduler.schedule(sample_task, interval_seconds=120)
        assert task_id == sample_task.id
        assert scheduler.scheduled_count == 1

    def test_unschedule_task(self, scheduler: TaskScheduler, sample_task: Task) -> None:
        scheduler.schedule(sample_task)
        assert scheduler.unschedule(sample_task.id) is True
        assert scheduler.scheduled_count == 0

    def test_unschedule_nonexistent(self, scheduler: TaskScheduler) -> None:
        assert scheduler.unschedule("nonexistent-id") is False

    def test_list_scheduled(self, scheduler: TaskScheduler, sample_task: Task) -> None:
        scheduler.schedule(sample_task, interval_seconds=60)
        scheduled = scheduler.list_scheduled()
        assert len(scheduled) == 1
        assert scheduled[0]["task_id"] == sample_task.id
        assert scheduled[0]["interval_seconds"] == 60
        assert scheduled[0]["type"] == "run"

    def test_check_budget_initial(self, scheduler: TaskScheduler) -> None:
        budget = scheduler.check_budget()
        assert budget["tokens_used"] == 0
        assert budget["tokens_limit"] == 10000
        assert budget["tokens_exhausted"] is False
        assert budget["cost_used"] == 0.0
        assert budget["cost_exhausted"] is False

    def test_record_usage(self, scheduler: TaskScheduler) -> None:
        scheduler.record_usage(tokens=500, cost=0.25)
        assert scheduler.tokens_used == 500
        assert scheduler.cost_used == 0.25

    def test_budget_exhaustion_tokens(self, scheduler: TaskScheduler) -> None:
        scheduler.record_usage(tokens=10000, cost=0.0)
        budget = scheduler.check_budget()
        assert budget["tokens_exhausted"] is True

    def test_budget_exhaustion_cost(self, scheduler: TaskScheduler) -> None:
        scheduler.record_usage(tokens=0, cost=5.0)
        budget = scheduler.check_budget()
        assert budget["cost_exhausted"] is True

    def test_reset_budget(self, scheduler: TaskScheduler) -> None:
        scheduler.record_usage(tokens=1000, cost=1.0)
        scheduler.reset_budget()
        assert scheduler.tokens_used == 0
        assert scheduler.cost_used == 0.0

    def test_get_stats(self, scheduler: TaskScheduler, sample_task: Task) -> None:
        scheduler.schedule(sample_task)
        stats = scheduler.get_stats()
        assert stats["running"] is False
        assert stats["scheduled_count"] == 1
        assert stats["config"]["interval_seconds"] == 60
        assert "budget" in stats

    @pytest.mark.asyncio
    async def test_run_once_empty(self, scheduler: TaskScheduler) -> None:
        executed = await scheduler.run_once()
        assert executed == []

    @pytest.mark.asyncio
    async def test_run_once_with_scheduled_task(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        scheduler.schedule(sample_task, interval_seconds=3600)
        import time

        scheduler._scheduled_tasks[sample_task.id]["next_run"] = time.time() - 1
        executed = await scheduler.run_once()
        assert sample_task.id in executed

    @pytest.mark.asyncio
    async def test_run_once_budget_exhausted(self, storage: TaskStorage, sample_task: Task) -> None:
        config = ScheduleConfig(budget_tokens=100)
        scheduler = TaskScheduler(storage, config)
        scheduler.record_usage(tokens=100)
        scheduler.schedule(sample_task, interval_seconds=3600)
        import time

        scheduler._scheduled_tasks[sample_task.id]["next_run"] = time.time() - 1
        executed = await scheduler.run_once()
        assert executed == []

    @pytest.mark.asyncio
    async def test_run_once_disabled(self, storage: TaskStorage, sample_task: Task) -> None:
        config = ScheduleConfig(enabled=False)
        scheduler = TaskScheduler(storage, config)
        scheduler.schedule(sample_task, interval_seconds=0)
        executed = await scheduler.run_once()
        assert executed == []


class TestTaskSchedulerCLI:
    def test_schedule_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["task", "schedule", "--help"])
        assert result.exit_code == 0
        assert "schedule" in result.output.lower()

    def test_schedule_task(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "task",
                "schedule",
                "test-op",
                "--type",
                "run",
                "--interval",
                "60",
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["scheduled"] is True
        assert data["data"]["interval_seconds"] == 60

    def test_scheduled_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["task", "scheduled", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "count" in data["data"]

    def test_scheduler_stats(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["task", "scheduler-stats", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "scheduled_count" in data["data"]
        assert "budget" in data["data"]

    def test_unschedule_task(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app
        from agent_runtime_cockpit.tasks import Task, TaskScheduler, TaskStorage, TaskType

        # Create a task directly in storage using the same path as CLI
        db_path = tmp_path / ".arc" / "tasks.db"
        storage = TaskStorage(db_path)
        scheduler = TaskScheduler(storage)
        task = Task(type=TaskType.RUN, operation="test-op", params={})
        task_id = scheduler.schedule(task, interval_seconds=60)

        runner = CliRunner()
        # Now unschedule with --yes flag
        result = runner.invoke(app, ["task", "unschedule", task_id, "--yes", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["unscheduled"] is True
