"""Tests for Phase 54 — Task daemon HTTP routes."""

import json
from unittest.mock import patch

import pytest


_SSE_PATH = "agent_runtime_cockpit.web.routes._SSE_PUSH_EVENT_TYPES"


@pytest.mark.asyncio
async def test_tasks_list_untrusted(client, workspace):
    """GET /api/tasks untrusted returns 403."""
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        resp = await client.get("/api/tasks")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_tasks_create_and_list(client, workspace):
    """POST /api/tasks creates a task and GET /api/tasks lists it."""

    body = {"type": "run", "operation": "wf-test", "params": {}}
    resp = await client.post("/api/tasks", json=body)
    assert resp.status_code == 200
    data = json.loads(await resp.text())
    assert data["ok"] is True
    assert "task_id" in data["data"]

    # list tasks
    resp2 = await client.get("/api/tasks?limit=10")
    assert resp2.status_code == 200
    list_data = json.loads(await resp2.text())
    assert list_data["ok"] is True
    assert len(list_data["data"]) >= 1


@pytest.mark.asyncio
async def test_tasks_get_untrusted_returns_403(client, workspace):
    """GET /api/tasks/{id} untrusted returns 403 before existence check."""
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        resp = await client.get("/api/tasks/nonexistent")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_tasks_get_by_id(client, workspace):
    """GET /api/tasks/{id} returns task status."""

    body = {"type": "run", "operation": "wf-get-test", "params": {}}
    resp = await client.post("/api/tasks", json=body)
    data = json.loads(await resp.text())
    task_id = data["data"]["task_id"]

    resp2 = await client.get(f"/api/tasks/{task_id}")
    assert resp2.status_code == 200
    get_data = json.loads(await resp2.text())
    assert get_data["ok"] is True
    assert get_data["data"]["id"] == task_id


@pytest.mark.asyncio
async def test_tasks_cancel(client, workspace):
    """DELETE /api/tasks/{id} cancels a running task."""

    body = {"type": "run", "operation": "wf-cancel-test", "params": {}}
    resp = await client.post("/api/tasks", json=body)
    data = json.loads(await resp.text())
    task_id = data["data"]["task_id"]

    resp2 = await client.delete(f"/api/tasks/{task_id}")
    assert resp2.status_code == 200
    del_data = json.loads(await resp2.text())
    assert del_data["ok"] is True
    assert del_data["data"]["cancelled"] is True
