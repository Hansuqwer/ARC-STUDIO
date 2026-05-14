"""Protocol contract tests: verify Python endpoints match the TS ArcEnvelope contract.

See theia-extensions/arc-core/src/common/arc-protocol.ts for the TypeScript side.
"""
from __future__ import annotations

import pytest

from agent_runtime_cockpit.protocol.schemas import RunRecord

pytestmark = pytest.mark.asyncio

ENVELOPE_KEYS = {"version", "ok", "data", "error", "meta"}


async def test_list_runs_envelope_shape(client):
    """/api/runs returns ArcEnvelope with data as list of RunRecords."""
    r = await client.get("/api/runs")
    assert r.status_code == 200
    body = await r.json()
    assert set(body.keys()) >= ENVELOPE_KEYS, f"Missing envelope keys: {ENVELOPE_KEYS - set(body.keys())}"
    assert body["version"] == "1.0"
    assert body["ok"] is True
    assert body["error"] is None
    assert "timestamp" in body["meta"]


async def test_list_runs_data_are_valid_run_records(client, workspace):
    """Every item in data validates as RunRecord."""
    from tests.web.test_runs_endpoints import _seed_trace

    _seed_trace(workspace, "run-sg-aaa111", "swarmgraph", "completed")
    _seed_trace(workspace, "run-sg-bbb222", "langgraph", "failed")

    r = await client.get("/api/runs")
    assert r.status_code == 200
    body = await r.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2

    for item in body["data"]:
        record = RunRecord.model_validate(item)
        assert record.id in ("run-sg-aaa111", "run-sg-bbb222")


async def test_health_returns_status_object(client):
    """/health returns a status dict, not an ArcEnvelope."""
    r = await client.get("/health")
    assert r.status_code == 200
    body = await r.json()
    assert "status" in body
    assert "version" in body


async def test_envelope_error_shape(client):
    """Invalid requests return ArcEnvelope with error populated."""
    r = await client.get("/api/runs/does-not-exist")
    assert r.status_code == 404
    body = await r.json()
    assert set(body.keys()) >= ENVELOPE_KEYS
    assert body["ok"] is False
    assert body["data"] is None
    assert body["error"] is not None
    assert "code" in body["error"]
    assert "message" in body["error"]
