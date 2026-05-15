"""Tests for storage management commands."""
from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner
from agent_runtime_cockpit.cli import app


def test_storage_vacuum_no_db(tmp_path: Path):
    """arc storage vacuum fails when no SQLite index exists."""
    result = CliRunner().invoke(app, [
        "storage", "vacuum",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_storage_vacuum_with_db(tmp_path: Path):
    """arc storage vacuum reclaims space after deletions."""
    from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    
    store = IndexedTraceStore(
        trace_dir=tmp_path / ".arc" / "traces",
        db_path=tmp_path / ".arc" / "arc.db",
    )
    store.init()
    for i in range(5):
        store.save(RunRecord(
            id=f"run-{i}",
            workflow_id="wf-test",
            runtime="stub",
            status=RunStatus.COMPLETED,
            started_at="2026-05-15T00:00:00Z",
        ))
    
    result = CliRunner().invoke(app, [
        "storage", "vacuum",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert "size_before" in data
    assert "size_after" in data
    assert "saved_bytes" in data


def test_storage_status_empty(tmp_path: Path):
    """arc storage status shows empty workspace."""
    result = CliRunner().invoke(app, [
        "storage", "status",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["traces"]["count"] == 0
    assert data["sqlite_index"]["exists"] is False
    assert data["goldens"]["count"] == 0
    assert data["hitl"]["pending"] == 0


def test_storage_status_with_data(tmp_path: Path):
    """arc storage status shows workspace with data."""
    from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    from agent_runtime_cockpit.evals.golden import GoldenTrace, save_golden
    
    store = IndexedTraceStore(
        trace_dir=tmp_path / ".arc" / "traces",
        db_path=tmp_path / ".arc" / "arc.db",
    )
    store.init()
    store.save(RunRecord(
        id="run-1",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
    ))
    
    save_golden(tmp_path, GoldenTrace(
        id="golden-1",
        workflow_id="wf-test",
        expected_status="completed",
    ))
    
    result = CliRunner().invoke(app, [
        "storage", "status",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["traces"]["count"] == 1
    assert data["sqlite_index"]["exists"] is True
    assert data["goldens"]["count"] == 1


def test_runs_prune_older_than(tmp_path: Path):
    """arc runs prune --older-than filters by age."""
    import time
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    
    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    old_run = RunRecord(
        id="old-run",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
    )
    store.save(old_run)
    
    old_path = tmp_path / ".arc" / "traces" / "old-run.jsonl"
    mtime = time.time() - (100 * 86400)
    old_path.touch()
    import os
    os.utime(old_path, (mtime, mtime))
    
    new_run = RunRecord(
        id="new-run",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
    )
    store.save(new_run)
    
    result = CliRunner().invoke(app, [
        "runs", "prune",
        "--older-than", "90",
        "--keep", "0",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["older_than_days"] == 90
    assert len(data["would_delete"]) == 1
    assert "old-run" in data["would_delete"][0]
