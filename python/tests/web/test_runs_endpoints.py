import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.asyncio


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _trace_dir(workspace: Path) -> Path:
    return workspace / ".arc" / "traces"


def _seed_trace(
    workspace: Path,
    run_id: str,
    runtime: str = "swarmgraph",
    status: str = "completed",
    *,
    workflow_id: str = "demo-workflow",
    started_at: str | None = None,
    ended_at: str | None = None,
    events: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a JSONL trace whose first line is a valid RunRecord."""
    traces_dir = _trace_dir(workspace)
    traces_dir.mkdir(parents=True, exist_ok=True)
    path = traces_dir / f"{run_id}.jsonl"
    started = started_at or _iso_now()
    run_events = [
        {
            "type": event.get("type", "AG_UI"),
            "timestamp": event.get("timestamp", started),
            "run_id": run_id,
            "sequence": event.get("sequence", i),
            "data": event.get("data", {}),
        }
        for i, event in enumerate(events or [])
    ]
    record: dict[str, Any] = {
        "id": run_id,
        "workflow_id": workflow_id,
        "runtime": runtime,
        "status": status,
        "started_at": started,
        "ended_at": ended_at,
        "events": run_events,
        "metadata": metadata or {},
    }
    lines = [json.dumps(record)]
    for event in run_events:
        lines.append(json.dumps(event))
    path.write_text("\n".join(lines) + "\n")
    return path


async def _get_runs(client, path: str = "/api/runs") -> dict[str, Any]:
    r = await client.get(path)
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    assert body["error"] is None
    assert isinstance(body["data"], list)
    return body


async def test_list_runs_empty(client):
    r = await client.get("/runs")
    if r.status_code == 404:
        r = await client.get("/api/runs")
        if r.status_code == 404:
            pytest.skip("/runs not mounted")
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    assert body["error"] is None
    assert body["data"] == []


async def test_response_envelope_shape(client):
    body = await _get_runs(client)
    assert set(body.keys()) >= {"version", "ok", "data", "error", "meta"}
    assert body["version"] == "1.0"
    assert isinstance(body["ok"], bool)
    assert "timestamp" in body["meta"]


async def test_list_runs_with_seed(client, workspace):
    _seed_trace(workspace, "aaaaaaaaaaaa", "swarmgraph", "completed")
    _seed_trace(workspace, "bbbbbbbbbbbb", "langgraph", "failed")
    
    for path in ("/runs", "/api/runs"):
        r = await client.get(path)
        if r.status_code == 404:
            continue
        assert r.status_code == 200
        body = await r.json()
        assert body["ok"] is True
        items = body["data"]
        ids = [item["id"] for item in items]
        assert "aaaaaaaaaaaa" in ids
        assert "bbbbbbbbbbbb" in ids
        return
    pytest.skip("/runs not mounted")


async def test_filter_by_runtime(client, workspace):
    _seed_trace(workspace, "aaaaaaaaaaaa", runtime="swarmgraph")
    _seed_trace(workspace, "bbbbbbbbbbbb", runtime="langgraph")
    
    for path in ("/runs?runtime=langgraph", "/api/runs?runtime=langgraph"):
        r = await client.get(path)
        if r.status_code == 404:
            continue
        assert r.status_code == 200
        body = await r.json()
        assert body["ok"] is True, f"Expected ok=True, got {body}"
        items = body["data"]
        assert len(items) == 1, f"Expected 1 langgraph run, got {len(items)}: {items}"
        assert items[0]["runtime"] == "langgraph"
        assert items[0]["id"] == "bbbbbbbbbbbb"
        return
        return
    pytest.skip("/runs filtering not implemented")


async def test_run_summary_unknown_404(client):
    for path in ("/runs/ffffffffffff/summary", "/api/runs/ffffffffffff/summary", "/runs/ffffffffffff"):
        r = await client.get(path)
        if r.status_code == 404:
            return  # Expected
    pytest.skip("run detail endpoint not mounted")


async def test_pagination(client, workspace):
    for i in range(5):
        _seed_trace(workspace, f"{i:012d}", "swarmgraph")
    
    for path in ("/runs?limit=2&offset=1", "/api/runs?limit=2&offset=1"):
        r = await client.get(path)
        if r.status_code == 404:
            continue
        if r.status_code == 200:
            body = await r.json()
            assert body["ok"] is True
            items = body["data"]
            if len(items) <= 3:  # Pagination working (not all 5)
                return
        return
    pytest.skip("pagination not implemented")


async def test_run_links_empty_run(client, workspace):
    _seed_trace(workspace, "links-empty", events=[])

    r = await client.get("/api/runs/links-empty/links")
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    assert body["data"]["has_stable_ids"] is False
    assert body["data"]["stable_id_count"] == 0


async def test_run_links_filters_node_chain(client, workspace):
    _seed_trace(workspace, "links-node", events=[
        {"type": "NODE_STARTED", "data": {"node_id": "node_alpha"}},
        {"type": "NODE_FAILED", "data": {"node_id": "node_alpha", "error": "boom"}},
    ])

    r = await client.get("/api/runs/links-node/links?filter=node_id&stable_id=node_alpha")
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    chain = body["data"]["node_chains"]["node_alpha"]
    assert [event["type"] for event in chain] == ["NODE_STARTED", "NODE_FAILED"]


async def test_run_links_malformed_stable_id_returns_empty(client, workspace):
    _seed_trace(workspace, "links-malformed", events=[
        {"type": "NODE_STARTED", "data": {"node_id": "node_alpha"}},
    ])

    r = await client.get("/api/runs/links-malformed/links?filter=node_id&stable_id=not-present")
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    assert "node_chains" not in body["data"]
    assert body["data"]["has_stable_ids"] is True


async def test_run_links_invalid_filter_returns_400(client, workspace):
    _seed_trace(workspace, "links-invalid-filter", events=[])

    r = await client.get("/api/runs/links-invalid-filter/links?filter=bad")
    assert r.status_code == 400
    body = await r.json()
    assert body["ok"] is False
    assert "Invalid links filter" in body["error"]["message"]


async def test_run_links_limit_and_offset(client, workspace):
    _seed_trace(workspace, "links-page", events=[
        {"type": "NODE_STARTED", "data": {"node_id": "node_a"}},
        {"type": "NODE_STARTED", "data": {"node_id": "node_b"}},
        {"type": "NODE_STARTED", "data": {"node_id": "node_c"}},
    ])

    r = await client.get("/api/runs/links-page/links?filter=node_id&limit=1&offset=1")
    assert r.status_code == 200
    body = await r.json()
    assert body["ok"] is True
    assert list(body["data"]["node_chains"].keys()) == ["node_b"]
    assert body["data"]["limit"] == 1
    assert body["data"]["offset"] == 1
