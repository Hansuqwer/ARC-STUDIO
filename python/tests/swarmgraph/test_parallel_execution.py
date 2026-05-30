from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import pytest

from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.models import WorkerResult
from agent_runtime_cockpit.swarmgraph import runner as runner_module
from agent_runtime_cockpit.swarmgraph.runner import SwarmGraphRunner


class _CancellationToken:
    def __init__(self) -> None:
        self.is_cancelled = False

    def cancel(self) -> None:
        self.is_cancelled = True


@pytest.mark.asyncio
async def test_run_async_returns_result() -> None:
    runner = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1))
    result = await runner.run_async("Explain consensus")

    assert result["status"] == "completed"
    assert result["total_tasks"] == 1


@pytest.mark.asyncio
async def test_parallel_execution_respects_max_parallel_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = 0
    max_active = 0

    async def fake_worker(task, mode, timeout, cancellation_token=None):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="ok"
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)
    cfg = SwarmGraphConfig(num_workers=3, max_rounds=1, max_parallel_workers=2, fan_out_threshold=0)
    runner = SwarmGraphRunner(config=cfg)

    result = await runner.run_async("Implement A. Test B. Document C.")

    assert result["completed_tasks"] == 3
    assert max_active == 2


@pytest.mark.asyncio
async def test_failed_worker_does_not_cancel_other_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_worker(task, mode, timeout, cancellation_token=None):
        if task.assigned_agent_id == "worker-2":
            return WorkerResult(
                worker_id=task.assigned_agent_id,
                task_id=task.id,
                output="",
                error="boom",
            )
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="ok"
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)
    cfg = SwarmGraphConfig(num_workers=3, max_rounds=1, max_parallel_workers=3, fan_out_threshold=0)
    runner = SwarmGraphRunner(config=cfg)

    result = await runner.run_async("Implement A. Test B. Document C.")

    assert result["completed_tasks"] == 2
    assert result["failed_tasks"] == 1
    assert len([event for event in result["events"] if event["kind"] == "worker"]) == 3


@pytest.mark.asyncio
async def test_cancellation_token_cancels_in_flight_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def slow_worker(task, mode, timeout, cancellation_token=None):
        await asyncio.sleep(5)
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="late"
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", slow_worker)
    token = _CancellationToken()
    cfg = SwarmGraphConfig(num_workers=3, max_rounds=1, max_parallel_workers=3, fan_out_threshold=0)
    runner = SwarmGraphRunner(config=cfg)

    async def cancel_soon() -> None:
        await asyncio.sleep(0.05)
        token.cancel()

    start = time.monotonic()
    cancel_task = asyncio.create_task(cancel_soon())
    result = await runner.run_async("Implement A. Test B. Document C.", cancellation_token=token)
    await cancel_task

    assert time.monotonic() - start < 1
    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_worker_events_emit_in_completion_order(monkeypatch: pytest.MonkeyPatch) -> None:
    async def delayed_worker(task, mode, timeout, cancellation_token=None):
        delay = {"worker-1": 0.03, "worker-2": 0.01, "worker-3": 0.02}[task.assigned_agent_id]
        await asyncio.sleep(delay)
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="ok",
            started_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", delayed_worker)
    cfg = SwarmGraphConfig(num_workers=3, max_rounds=1, max_parallel_workers=3, fan_out_threshold=0)
    runner = SwarmGraphRunner(config=cfg)

    result = await runner.run_async("Implement A. Test B. Document C.")

    worker_ids = [
        event["data"]["worker_id"] for event in result["events"] if event["kind"] == "worker"
    ]
    assert worker_ids == ["worker-2", "worker-3", "worker-1"]


@pytest.mark.asyncio
async def test_budget_failure_after_completed_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    async def cost_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="ok",
            cost_usd=0.6,
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", cost_worker)
    cfg = SwarmGraphConfig(
        num_workers=3,
        max_rounds=1,
        max_parallel_workers=1,
        fan_out_threshold=0,
        enable_budget=True,
        budget_limit_usd=1.0,
    )
    runner = SwarmGraphRunner(config=cfg)

    result = await runner.run_async("Implement A. Test B. Document C.")

    assert result["status"] == "failed"
    assert result["error"] == "budget exhausted"
    assert result["total_cost_usd"] == pytest.approx(1.2)
    assert len([event for event in result["events"] if event["kind"] == "budget"]) == 2


@pytest.mark.asyncio
async def test_budget_exhausted_before_dispatch_skips_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unexpected_worker(task, mode, timeout, cancellation_token=None):
        raise AssertionError("worker should not run when budget is already exhausted")

    monkeypatch.setattr(runner_module, "worker_execute_async", unexpected_worker)
    cfg = SwarmGraphConfig(
        num_workers=3,
        max_rounds=1,
        max_parallel_workers=3,
        fan_out_threshold=0,
        enable_budget=True,
        budget_limit_usd=0.0,
    )
    runner = SwarmGraphRunner(config=cfg)

    result = await runner.run_async("Implement A. Test B. Document C.")

    assert result["status"] == "failed"
    assert result["error"] == "budget exhausted"
    assert result["completed_tasks"] == 0
    assert result["total_cost_usd"] == 0.0
    assert not [event for event in result["events"] if event["kind"] == "worker"]
    budget_events = [event for event in result["events"] if event["kind"] == "budget"]
    assert budget_events == [
        {
            "id": budget_events[0]["id"],
            "kind": "budget",
            "swarm_id": result["swarm_id"],
            "timestamp": budget_events[0]["timestamp"],
            "data": {
                "cost_usd": 0.0,
                "limit_usd": 0.0,
                "accumulated": 0.0,
                "exhausted": True,
            },
            "round": 0,
        }
    ]
