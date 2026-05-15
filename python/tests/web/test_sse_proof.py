"""
Tests: Manual SSE proof endpoint (PR 18).

Verifies that the manual ``aiohttp.web.StreamResponse`` SSE
implementation delivers events + heartbeats without the
aiohttp-sse package.
"""
from __future__ import annotations

import json
import pytest


pytestmark = pytest.mark.asyncio


async def test_sse_proof_returns_event_stream(workspace, client):
    """GET /api/sse/proof returns text/event-stream with events."""
    resp = await client.get("/api/sse/proof")
    assert resp.status_code == 200
    body = await resp.text()
    assert "RUN_STARTED" in body
    assert "STEP_STARTED" in body
    assert "RUN_COMPLETED" in body
    assert "STREAM_END" in body
    assert "HEARTBEAT" in body


async def test_sse_proof_events_have_required_fields(workspace, client):
    """Each SSE data line is valid JSON with type field."""
    resp = await client.get("/api/sse/proof")
    body = await resp.text()
    for line in body.strip().split("\n"):
        if not line.startswith("data: "):
            continue
        payload = json.loads(line.removeprefix("data: "))
        assert "type" in payload
        assert isinstance(payload["type"], str)


async def test_sse_proof_ends_with_stream_end(workspace, client):
    """SSE stream ends with STREAM_END event."""
    resp = await client.get("/api/sse/proof")
    body = await resp.text()
    assert '"type": "STREAM_END"' in body
