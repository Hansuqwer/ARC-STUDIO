"""Tests for Phase 55 — Provider workspace isolation trust enforcement."""

import json
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_providers_routing_put_untrusted(client, workspace):
    """PUT /api/providers/routing untrusted returns 403."""
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        body = {"provider_id": "openai", "policy": "round_robin"}
        resp = await client.put("/api/providers/routing", json=body)
    assert resp.status_code == 403
    data = json.loads(await resp.text())
    assert data["ok"] is False
    assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_providers_routing_get_still_works(client, workspace):
    """GET /api/providers/routing is read-only and does not require trust."""
    resp = await client.get("/api/providers/routing")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_providers_accounts_post_untrusted(client, workspace):
    """POST /api/providers/accounts untrusted returns 403."""
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        body = {"provider": "openai", "label": "test", "api_key_env": "OPENAI_API_KEY"}
        resp = await client.post("/api/providers/accounts", json=body)
    assert resp.status_code == 403
    data = json.loads(await resp.text())
    assert data["ok"] is False
    assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_providers_account_patch_untrusted(client, workspace):
    """PATCH /api/providers/accounts/{id} untrusted returns 403."""
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        resp = await client.patch("/api/providers/accounts/nonexistent", json={"enabled": True})
    assert resp.status_code == 403
    data = json.loads(await resp.text())
    assert data["ok"] is False
    assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_providers_account_delete_untrusted(client, workspace):
    """DELETE /api/providers/accounts/{id} untrusted returns 403."""
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        resp = await client.delete("/api/providers/accounts/nonexistent")
    assert resp.status_code == 403
    data = json.loads(await resp.text())
    assert data["ok"] is False
    assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_providers_accounts_get_still_works(client, workspace):
    """GET /api/providers/accounts is read-only and does not require trust."""
    resp = await client.get("/api/providers/accounts")
    assert resp.status_code == 200
