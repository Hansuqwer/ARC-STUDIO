"""Integration tests for the /api/evals/run endpoint."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.asyncio


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _seed_trace(
    workspace: Path,
    run_id: str,
    runtime: str = "swarmgraph",
    status: str = "completed",
    *,
    workflow_id: str = "demo-workflow",
    started_at: str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> Path:
    traces_dir = workspace / ".arc" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    path = traces_dir / f"{run_id}.jsonl"
    started = started_at or _iso_now()
    record: dict[str, Any] = {
        "id": run_id,
        "workflow_id": workflow_id,
        "runtime": runtime,
        "status": status,
        "started_at": started,
        "ended_at": started,
        "events": events or [],
        "metadata": {},
    }
    # Write the record as first JSON line, then events as subsequent lines
    # Store events with proper RunEvent fields
    event_records = []
    for i, event in enumerate(events or []):
        event_records.append({
            "type": event.get("type", "AG_UI"),
            "timestamp": event.get("timestamp", started),
            "run_id": run_id,
            "sequence": event.get("sequence", i),
            "data": event.get("data", {}),
        })
    record["events"] = event_records
    path.write_text(json.dumps(record) + "\n")
    return path


async def test_eval_run_status_match(client, workspace):
    run_id = "test-run-eval-001"
    started = _iso_now()
    _seed_trace(workspace, run_id, status="completed", started_at=started, events=[
        {"type": "RUN_STARTED", "timestamp": started, "data": {}},
        {"type": "RUN_COMPLETED", "timestamp": started, "data": {"final_output": "hello world"}},
    ])
    r = await client.post("/api/evals/run", json={
        "run_id": run_id,
        "golden": {
            "id": "golden-001",
            "workflow_id": "demo-workflow",
            "expected_status": "completed",
            "expected_event_types": ["RUN_STARTED", "RUN_COMPLETED"],
            "expected_final_output_contains": "hello",
            "description": "test golden",
        },
    })
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["run_id"] == run_id
    assert data["passed"] is True
    assert data["status_match"] is True


async def test_eval_run_status_mismatch(client, workspace):
    run_id = "test-run-eval-002"
    started = _iso_now()
    _seed_trace(workspace, run_id, status="failed", started_at=started, events=[
        {"type": "RUN_STARTED", "timestamp": started, "data": {}},
    ])
    r = await client.post("/api/evals/run", json={
        "run_id": run_id,
        "golden": {
            "id": "golden-002",
            "workflow_id": "demo-workflow",
            "expected_status": "completed",
            "expected_event_types": [],
            "expected_final_output_contains": "",
            "description": "should fail status",
        },
    })
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["passed"] is False
    assert data["status_match"] is False


async def test_eval_run_not_found(client):
    r = await client.post("/api/evals/run", json={
        "run_id": "nonexistent-run",
        "golden": {
            "id": "golden-003",
            "workflow_id": "demo-workflow",
            "expected_status": "completed",
            "expected_event_types": [],
            "expected_final_output_contains": "",
            "description": "",
        },
    })
    assert r.status_code == 404
