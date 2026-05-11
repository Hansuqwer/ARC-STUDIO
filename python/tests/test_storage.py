"""Tests: Storage — JSONL trace store."""
import tempfile
from pathlib import Path
import datetime

from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
from agent_runtime_cockpit.protocol.schemas import RunRecord, RunEvent, RunStatus


def make_run(run_id: str = "run-test-001") -> RunRecord:
    now = datetime.datetime.utcnow().isoformat() + "Z"
    return RunRecord(
        id=run_id,
        workflow_id="wf-test",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        events=[
            RunEvent(type="RUN_STARTED", timestamp=now, run_id=run_id, sequence=0, data={}),
            RunEvent(type="RUN_COMPLETED", timestamp=now, run_id=run_id, sequence=1, data={}),
        ],
    )


class TestJsonlTraceStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            run = make_run("run-001")
            store.save(run)
            loaded = store.load("run-001")
            assert loaded is not None
            assert loaded.id == "run-001"
            assert loaded.status == RunStatus.COMPLETED

    def test_load_nonexistent_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            assert store.load("nonexistent-run") is None

    def test_list_runs(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            store.save(make_run("run-a"))
            store.save(make_run("run-b"))
            ids = store.list_runs()
            assert "run-a" in ids
            assert "run-b" in ids

    def test_events_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            run = make_run("run-events")
            store.save(run)
            loaded = store.load("run-events")
            assert loaded is not None
            assert len(loaded.events) == 2
            assert loaded.events[0].type == "RUN_STARTED"
            assert loaded.events[1].type == "RUN_COMPLETED"

    def test_overwrite_run(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            run1 = make_run("run-overwrite")
            store.save(run1)
            # Overwrite with updated status
            run2 = make_run("run-overwrite")
            run2.status = RunStatus.FAILED
            store.save(run2)
            loaded = store.load("run-overwrite")
            assert loaded.status == RunStatus.FAILED
