"""Tests: Storage — JSONL trace store and SQLite index (ADR-003)."""

import datetime
import tempfile
from pathlib import Path

from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore, _compute_duration_ms
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
from agent_runtime_cockpit.storage.sqlite import SqliteStore


def make_run(run_id: str = "run-test-001", status: RunStatus = RunStatus.COMPLETED) -> RunRecord:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return RunRecord(
        id=run_id,
        workflow_id="wf-test",
        runtime="swarmgraph",
        status=status,
        started_at=now,
        ended_at=now if status != RunStatus.RUNNING else None,
        events=[
            RunEvent(type="RUN_STARTED", timestamp=now, run_id=run_id, sequence=0, data={}),
            RunEvent(type="RUN_COMPLETED", timestamp=now, run_id=run_id, sequence=1, data={}),
        ],
    )


# ─── JSONL tests ───────────────────────────────────────────────────────────────


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


# ─── SQLite index tests ────────────────────────────────────────────────────────


class TestSqliteStore:
    def test_init_and_insert(self):
        with tempfile.TemporaryDirectory() as td:
            db = SqliteStore(Path(td) / "arc.db")
            db.init_db()
            db.insert_run("run-001", "wf-1", "swarmgraph", "completed", "2026-01-01T00:00:00Z")
            run = db.get_run("run-001")
            assert run is not None
            assert run["id"] == "run-001"
            assert run["status"] == "completed"

    def test_update_run_status(self):
        with tempfile.TemporaryDirectory() as td:
            db = SqliteStore(Path(td) / "arc.db")
            db.init_db()
            db.insert_run("run-001", "wf-1", "swarmgraph", "running", "2026-01-01T00:00:00Z")
            db.update_run_status(
                "run-001",
                "completed",
                "2026-01-01T01:00:00Z",
                duration_ms=3600000,
            )
            run = db.get_run("run-001")
            assert run is not None
            assert run["status"] == "completed"
            assert run["duration_ms"] == 3600000

    def test_list_runs_with_filters(self):
        with tempfile.TemporaryDirectory() as td:
            db = SqliteStore(Path(td) / "arc.db")
            db.init_db()
            db.insert_run("r1", "wf-1", "swarmgraph", "completed", "2026-01-01T00:00:00Z")
            db.insert_run("r2", "wf-1", "langgraph", "failed", "2026-01-02T00:00:00Z")
            db.insert_run("r3", "wf-2", "swarmgraph", "completed", "2026-01-03T00:00:00Z")

            all_runs = db.list_runs()
            assert len(all_runs) == 3

            failed_runs = db.list_runs(status="failed")
            assert len(failed_runs) == 1
            assert failed_runs[0]["id"] == "r2"

            swarm_runs = db.list_runs(runtime="swarmgraph")
            assert len(swarm_runs) == 2

    def test_update_audit_path(self):
        with tempfile.TemporaryDirectory() as td:
            db = SqliteStore(Path(td) / "arc.db")
            db.init_db()
            db.insert_run("run-001", "wf-1", "swarmgraph", "completed", "2026-01-01T00:00:00Z")
            db.update_run_audit_path("run-001", "/path/to/audit.chain.jsonl")
            run = db.get_run("run-001")
            assert run is not None
            assert run["audit_path"] == "/path/to/audit.chain.jsonl"

    def test_run_exists(self):
        with tempfile.TemporaryDirectory() as td:
            db = SqliteStore(Path(td) / "arc.db")
            db.init_db()
            db.insert_run("run-001", "wf-1", "swarmgraph", "completed", "2026-01-01T00:00:00Z")
            assert db.run_exists("run-001") is True
            assert db.run_exists("nonexistent") is False

    def test_count_runs(self):
        with tempfile.TemporaryDirectory() as td:
            db = SqliteStore(Path(td) / "arc.db")
            db.init_db()
            assert db.count_runs() == 0
            db.insert_run("r1", "wf-1", "swarmgraph", "completed", "2026-01-01T00:00:00Z")
            assert db.count_runs() == 1
            db.insert_run("r2", "wf-1", "langgraph", "completed", "2026-01-02T00:00:00Z")
            assert db.count_runs() == 2


# ─── IndexedTraceStore tests (dual-write) ──────────────────────────────────────


class TestIndexedTraceStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            store = IndexedTraceStore(
                trace_dir=Path(td) / "traces",
                db_path=Path(td) / "arc.db",
            )
            store.init()
            run = make_run("run-001")
            store.save(run)
            loaded = store.load("run-001")
            assert loaded is not None
            assert loaded.id == "run-001"
            assert loaded.status == RunStatus.COMPLETED

    def test_save_updates_sqlite_index(self):
        with tempfile.TemporaryDirectory() as td:
            store = IndexedTraceStore(
                trace_dir=Path(td) / "traces",
                db_path=Path(td) / "arc.db",
            )
            store.init()
            run = make_run("run-001")
            store.save(run)
            # Verify SQLite has the index
            row = store.sqlite.get_run("run-001")
            assert row is not None
            assert row["status"] == "completed"
            assert row["runtime"] == "swarmgraph"

    def test_jsonl_is_canonical_when_sqlite_fails(self):
        """JSONL write succeeds even if SQLite is corrupted."""
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "bad.db"
            db_path.write_text("not a database")
            store = IndexedTraceStore(
                trace_dir=Path(td) / "traces",
                db_path=db_path,
            )
            run = make_run("resilient-run")
            # Should not raise; SQLite failure is logged, not propagated
            store.save(run)
            loaded = store.load("resilient-run")
            assert loaded is not None
            assert loaded.id == "resilient-run"

    def test_backfill_index(self):
        with tempfile.TemporaryDirectory() as td:
            store = IndexedTraceStore(
                trace_dir=Path(td) / "traces",
                db_path=Path(td) / "arc.db",
            )
            store.init()
            # Write runs directly to JSONL (as if old system created them)
            runs = [make_run(f"run-{i}") for i in range(5)]
            for r in runs:
                store.jsonl.save(r)
            # Backfill should index them into SQLite
            indexed, skipped, failed = store.backfill_index()
            assert indexed == 5
            assert skipped == 0
            assert failed == 0
            # Verify SQLite has them
            assert store.sqlite.count_runs() == 5

    def test_backfill_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            store = IndexedTraceStore(
                trace_dir=Path(td) / "traces",
                db_path=Path(td) / "arc.db",
            )
            store.init()
            runs = [make_run(f"run-{i}") for i in range(3)]
            for r in runs:
                store.jsonl.save(r)
            # First backfill
            indexed1, skipped1, failed1 = store.backfill_index()
            assert indexed1 == 3
            # Second backfill — should skip already-indexed runs
            indexed2, skipped2, failed2 = store.backfill_index()
            assert indexed2 == 0
            assert skipped2 == 3
            assert failed2 == 0

    def test_list_runs(self):
        with tempfile.TemporaryDirectory() as td:
            store = IndexedTraceStore(
                trace_dir=Path(td) / "traces",
                db_path=Path(td) / "arc.db",
            )
            store.init()
            store.save(make_run("run-a"))
            store.save(make_run("run-b"))
            run_ids = store.list_runs()
            assert "run-a" in run_ids
            assert "run-b" in run_ids


# ─── Utility tests ─────────────────────────────────────────────────────────────


class TestComputeDuration:
    def test_duration_ms(self):
        result = _compute_duration_ms("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z")
        assert result == 3600000  # 1 hour

    def test_duration_with_offset(self):
        result = _compute_duration_ms("2026-01-01T00:00:00+00:00", "2026-01-01T00:30:00+00:00")
        assert result == 1800000  # 30 minutes

    def test_duration_with_invalid_date(self):
        result = _compute_duration_ms("not-a-date", "2026-01-01T00:00:00Z")
        assert result is None


# ─── CR-006: run-ID path-traversal guard ────────────────────────────────────


class TestJsonlRunIdGuard:
    def test_trace_path_rejects_traversal(self):
        import pytest

        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            for bad in ("../secret", "../../etc/passwd", "a/b", "x\\y", ".."):
                with pytest.raises(ValueError):
                    store.trace_path(bad)

    def test_trace_path_allows_legit_ids(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            assert store.trace_path("run-001").name == "run-001.jsonl"
            assert store.trace_path("run_abc").name == "run_abc.jsonl"
            uuid_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            assert store.trace_path(uuid_id).name == f"{uuid_id}.jsonl"

    def test_load_returns_none_for_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonlTraceStore(Path(td))
            assert store.load("../secret") is None

    def test_save_does_not_write_outside_base_dir(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "traces"
            store = JsonlTraceStore(base)
            store.save(make_run("../../evil"))  # swallowed + logged, not written
            # Nothing escaped the base dir.
            assert not (Path(td) / "evil.jsonl").exists()
            assert list(Path(td).rglob("evil.jsonl")) == []
