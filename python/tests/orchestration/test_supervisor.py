"""
Tests: JobSupervisor — run lifecycle, cancel, and orphan recovery (PR 20).

Uses fake executor functions to simulate successful, failing,
cancelling, and orphaned runs.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agent_runtime_cockpit.orchestration.supervisor import (
    JobSupervisor,
    RunRequest,
    ActiveRun,
)
from agent_runtime_cockpit.orchestration.event_broker import EventBroker
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
from agent_runtime_cockpit.protocol.schemas import RunStatus


@pytest.fixture
def supervisor(tmp_path: Path) -> JobSupervisor:
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    broker = EventBroker(store=store)
    return JobSupervisor(store=store, broker=broker)


def _make_request(workflow_id: str = "wf-test", runtime: str = "swarmgraph") -> RunRequest:
    return RunRequest(workflow_id=workflow_id, runtime=runtime)


class TestStartRun:
    """Starting a run creates a PENDING record and launches execution."""

    @pytest.mark.asyncio
    async def test_start_run_returns_pending_record(self, supervisor: JobSupervisor):
        run = await supervisor.start_run(
            _make_request(),
            lambda run_id, req, emit: asyncio.sleep(0.01),
        )
        assert run.id.startswith("run-")
        assert run.status == RunStatus.PENDING
        assert run.workflow_id == "wf-test"

    @pytest.mark.asyncio
    async def test_run_completes_successfully(self, supervisor: JobSupervisor):
        async def fake_executor(run_id, req, emit_event):
            emit_event(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "fake"})
            await asyncio.sleep(0.01)

        run = await supervisor.start_run(_make_request(), fake_executor)
        run_id = run.id

        # Wait for completion
        await asyncio.sleep(0.2)

        loaded = supervisor.store.load(run_id)
        assert loaded is not None
        assert loaded.status == RunStatus.COMPLETED
        assert loaded.ended_at is not None
        assert [event.type for event in loaded.events] == [
            "RUN_STARTED", "STEP_STARTED", "RUN_COMPLETED",
        ]


class TestCancelRun:
    """Cancelling a run marks it as CANCELLED."""

    @pytest.mark.asyncio
    async def test_cancel_active_run(self, supervisor: JobSupervisor):
        async def slow_executor(run_id, req, emit_event):
            emit_event(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "slow"})
            await asyncio.sleep(10)  # will be cancelled

        run = await supervisor.start_run(_make_request(), slow_executor)
        run_id = run.id
        await asyncio.sleep(0.05)  # let it start

        cancelled = await supervisor.cancel_run(run_id)
        assert cancelled is True, (
            f"cancel_run returned False. Active runs: {list(supervisor._active_runs.keys())}"
        )

        loaded = supervisor.store.load(run_id)
        assert loaded is not None
        assert loaded.status == RunStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self, supervisor: JobSupervisor):
        cancelled = await supervisor.cancel_run("nonexistent")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_cancel_completed_run_is_noop(self, supervisor: JobSupervisor):
        async def fast_executor(run_id, req, emit_event):
            await asyncio.sleep(0.01)

        run = await supervisor.start_run(_make_request(), fast_executor)
        run_id = run.id
        await asyncio.sleep(0.1)  # let it finish

        cancelled = await supervisor.cancel_run(run_id)
        assert cancelled is False  # already completed

        loaded = supervisor.store.load(run_id)
        assert loaded.status == RunStatus.COMPLETED


class TestOrphanRecovery:
    """Recover orphans marks stale RUNNING runs as FAILED."""

    @pytest.mark.asyncio
    async def test_recover_orphans(self, supervisor: JobSupervisor, tmp_path: Path):
        # Manually create a RUNNING run in the store (simulating orphan)
        from agent_runtime_cockpit.protocol.schemas import RunRecord
        from datetime import datetime, timezone

        orphan = RunRecord(
            id="orphan-001",
            workflow_id="wf",
            runtime="swarmgraph",
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        supervisor.store.save(orphan)

        recovered = await supervisor.recover_orphans()
        assert recovered == 1

        loaded = supervisor.store.load("orphan-001")
        assert loaded is not None
        assert loaded.status == RunStatus.FAILED
        assert loaded.metadata.get("failure_reason") == "supervisor_orphan"

    @pytest.mark.asyncio
    async def test_recover_orphans_skips_completed(self, supervisor: JobSupervisor, tmp_path: Path):
        from agent_runtime_cockpit.protocol.schemas import RunRecord
        from datetime import datetime, timezone

        completed = RunRecord(
            id="completed-001",
            workflow_id="wf",
            runtime="swarmgraph",
            status=RunStatus.COMPLETED,
            started_at=datetime.now(timezone.utc).isoformat(),
            ended_at=datetime.now(timezone.utc).isoformat(),
        )
        supervisor.store.save(completed)

        recovered = await supervisor.recover_orphans()
        assert recovered == 0

    @pytest.mark.asyncio
    async def test_recover_orphans_empty_store(self, supervisor: JobSupervisor):
        recovered = await supervisor.recover_orphans()
        assert recovered == 0


class TestBrokerIntegration:
    """Supervisor publishes events through the EventBroker."""

    @pytest.mark.asyncio
    async def test_broker_receives_run_events(self, supervisor: JobSupervisor):
        broker = supervisor.broker

        async def fake_executor(run_id, req, emit_event):
            emit_event(run_id, "STEP_STARTED", {"step_id": "s1", "step_name": "fake"})
            await asyncio.sleep(0.01)

        run = await supervisor.start_run(_make_request(), fake_executor)
        run_id = run.id

        # Subscribe to broker events BEFORE execution completes
        queue = broker.subscribe(run_id)
        await asyncio.sleep(0.2)

        # Collect published events
        collected = []
        while not queue.empty():
            ev = queue.get_nowait()
            if ev is not None:
                collected.append(ev)

        # Should have RUN_STARTED, STEP_STARTED, RUN_COMPLETED
        types = {e["type"] for e in collected}
        assert "RUN_STARTED" in types, f"Got types: {types}"
        assert "STEP_STARTED" in types, f"Got types: {types}"
        assert "RUN_COMPLETED" in types, f"Got types: {types}"
