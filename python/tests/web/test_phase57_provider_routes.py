"""Tests for Phase 57 provider account HTTP routes.

Uses the same patterns as test_phase50_trust_surface_audit.py
and test_phase55_provider_trust.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, AsyncIterator
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from agent_runtime_cockpit.security.enforcement import TrustEnforcementError
from agent_runtime_cockpit.web.keys import WORKSPACE_KEY
from agent_runtime_cockpit.web.routes import setup_routes

pytestmark = pytest.mark.asyncio

TRUST = "agent_runtime_cockpit.web.routes.enforce_workspace_trust"
_UNTRUSTED = TrustEnforcementError("workspace untrusted (phase 57 test)")


def _ok(envelope: dict) -> bool:
    return envelope.get("ok", False)


def _permission_denied(body: dict) -> None:
    assert body["error"]["code"] == "PERMISSION_DENIED", f"expected PERMISSION_DENIED, got {body}"


async def _client(workspace: Path) -> AsyncIterator[TestClient]:
    app = web.Application()
    app[WORKSPACE_KEY] = workspace
    setup_routes(app)
    client = TestClient(TestServer(app))
    await client.start_server()
    yield client
    await client.close()


def _provider_config_path(workspace: Path) -> Path:
    d = workspace / ".arc"
    d.mkdir(parents=True, exist_ok=True)
    return d / "providers.json"


def _seed_account(config_path: Path, account: dict[str, Any]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "accounts": [account]}
    config_path.write_text(json.dumps(payload, indent=2))


# ── GET /api/providers/accounts/{id} ──────────────────────────────────────────


async def test_providers_get_account_exists(tmp_path: Path) -> None:
    """GET single provider account returns the account."""
    config = _provider_config_path(tmp_path)
    account = {
        "id": "p1",
        "provider": "openai",
        "label": "My OpenAI",
        "enabled": True,
        "key_env_var": "OPENAI_API_KEY",
        "key_fingerprint": None,
        "masked_key": "env:OPENAI_API_KEY",
        "base_url": None,
        "default_model": "gpt-4",
        "created_at": "2026-01-01T00:00:00",
    }
    _seed_account(config, account)

    with patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}):
        async for c in _client(tmp_path):
            resp = await c.get("/api/providers/accounts/p1")
            assert resp.status == 200
            body = await resp.json()
            assert _ok(body)
            assert body["data"]["id"] == "p1"
            assert body["data"]["label"] == "My OpenAI"


async def test_providers_get_account_not_found(tmp_path: Path) -> None:
    """GET nonexistent account returns 404."""
    config = _provider_config_path(tmp_path)
    config.write_text(json.dumps({"version": 1, "accounts": []}))
    with patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}):
        async for c in _client(tmp_path):
            resp = await c.get("/api/providers/accounts/nonexistent")
            assert resp.status == 404


# ── PUT /api/providers/accounts/{id} ──────────────────────────────────────────


async def test_providers_put_updates_label(tmp_path: Path) -> None:
    """PUT updates account label."""
    config = _provider_config_path(tmp_path)
    account = {
        "id": "p2",
        "provider": "anthropic",
        "label": "Old Label",
        "enabled": True,
        "key_env_var": "ANTHROPIC_API_KEY",
        "key_fingerprint": None,
        "masked_key": "env:ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-sonnet",
    }
    _seed_account(config, account)
    with (
        patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}),
        patch(TRUST),
    ):
        async for c in _client(tmp_path):
            resp = await c.put(
                "/api/providers/accounts/p2",
                json={"label": "New Label"},
            )
            assert resp.status == 200
            body = await resp.json()
            assert _ok(body)
            assert body["data"]["label"] == "New Label"


async def test_providers_put_updates_default_model(tmp_path: Path) -> None:
    """PUT updates account default_model."""
    config = _provider_config_path(tmp_path)
    account = {
        "id": "p3",
        "provider": "openai",
        "label": "Test",
        "enabled": True,
        "key_env_var": "OPENAI_API_KEY",
        "default_model": "gpt-4",
    }
    _seed_account(config, account)
    with (
        patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}),
        patch(TRUST),
    ):
        async for c in _client(tmp_path):
            resp = await c.put(
                "/api/providers/accounts/p3",
                json={"default_model": "gpt-4-turbo"},
            )
            assert resp.status == 200
            body = await resp.json()
            assert _ok(body)
            assert body["data"]["default_model"] == "gpt-4-turbo"


async def test_providers_put_untrusted_returns_403(tmp_path: Path) -> None:
    """PUT on untrusted workspace returns 403."""
    config = _provider_config_path(tmp_path)
    account = {"id": "p4", "provider": "openai", "label": "Test"}
    _seed_account(config, account)
    with (
        patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}),
        patch(TRUST, side_effect=_UNTRUSTED),
    ):
        async for c in _client(tmp_path):
            resp = await c.put(
                "/api/providers/accounts/p4",
                json={"label": "Should Fail"},
            )
            assert resp.status == 403
            body = await resp.json()
            _permission_denied(body)


# ── POST /api/providers/accounts/{id}/test ────────────────────────────────────


async def test_providers_test_configured(tmp_path: Path) -> None:
    """POST test returns configured when env var present."""
    config = _provider_config_path(tmp_path)
    account = {
        "id": "p5",
        "provider": "openai",
        "label": "Test",
        "key_env_var": "OPENAI_API_KEY",
    }
    _seed_account(config, account)
    with (
        patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config), "OPENAI_API_KEY": "sk-test"}),
        patch(TRUST),
    ):
        async for c in _client(tmp_path):
            resp = await c.post("/api/providers/accounts/p5/test")
            assert resp.status == 200
            body = await resp.json()
            assert _ok(body)
            assert body["data"]["status"] == "configured"


async def test_providers_test_not_found(tmp_path: Path) -> None:
    """POST test on nonexistent account returns 404."""
    config = _provider_config_path(tmp_path)
    config.write_text(json.dumps({"version": 1, "accounts": []}))
    with (
        patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}),
        patch(TRUST),
    ):
        async for c in _client(tmp_path):
            resp = await c.post("/api/providers/accounts/nonexistent/test")
            assert resp.status == 404


async def test_providers_test_untrusted_returns_403(tmp_path: Path) -> None:
    """POST test on untrusted workspace returns 403."""
    config = _provider_config_path(tmp_path)
    account = {"id": "p6", "provider": "openai", "label": "Test"}
    _seed_account(config, account)
    with (
        patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config)}),
        patch(TRUST, side_effect=_UNTRUSTED),
    ):
        async for c in _client(tmp_path):
            resp = await c.post("/api/providers/accounts/p6/test")
            assert resp.status == 403
            body = await resp.json()
            _permission_denied(body)
