"""Tests for ARC_DAEMON_TOKEN bearer-token auth.

These tests verify the middleware in python/src/agent_runtime_cockpit/web/server.py.
See docs/SECURITY_AUDIT_REPORT.md R-6 for design details.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

_TRUST = "agent_runtime_cockpit.web.routes.enforce_workspace_trust"

pytestmark = pytest.mark.asyncio


async def test_no_token_set_rejected_by_default(app, monkeypatch):
    """When ARC_DAEMON_TOKEN is unset, non-health requests fail closed."""
    from aiohttp.test_utils import TestClient, TestServer

    monkeypatch.delenv("ARC_DAEMON_TOKEN", raising=False)
    monkeypatch.delenv("ARC_DAEMON_ALLOW_UNAUTHENTICATED", raising=False)
    async with TestServer(app) as server:
        async with TestClient(server) as c:
            r = await c.get("/api/runs")
            assert r.status == 401
            body = await r.json()
            assert "ARC_DAEMON_TOKEN required" in body["error"]


async def test_no_token_test_bypass_allows_routes(client):
    """ARC_DAEMON_ALLOW_UNAUTHENTICATED=1 is test/local bypass only."""
    r = await client.get("/api/runs")
    assert r.status_code == 200


async def test_health_allows_without_token(client):
    """/health always succeeds regardless of token setting."""
    r = await client.get("/health")
    assert r.status_code == 200


async def test_request_without_token_rejected(app):
    """When token is set, requests without auth header get 401."""
    from aiohttp.test_utils import TestClient, TestServer

    os.environ["ARC_DAEMON_TOKEN"] = "test-token-123"
    try:
        async with TestServer(app) as server:
            async with TestClient(server) as c:
                r = await c.get("/api/runs")
                assert r.status == 401
                body = await r.json()
                assert "error" in body
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)


async def test_request_with_wrong_token_rejected(app):
    """Wrong bearer token returns 401."""
    from aiohttp.test_utils import TestClient, TestServer

    os.environ["ARC_DAEMON_TOKEN"] = "correct-token"
    try:
        async with TestServer(app) as server:
            async with TestClient(server) as c:
                r = await c.get("/api/runs", headers={"Authorization": "Bearer wrong-token"})
                assert r.status == 401
                body = await r.json()
                assert "error" in body
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)


async def test_request_with_correct_token_succeeds(app):
    """Correct bearer token succeeds."""
    from aiohttp.test_utils import TestClient, TestServer

    os.environ["ARC_DAEMON_TOKEN"] = "correct-token"
    try:
        with patch(_TRUST):
            async with TestServer(app) as server:
                async with TestClient(server) as c:
                    r = await c.get("/api/runs", headers={"Authorization": "Bearer correct-token"})
                    assert r.status == 200
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)


async def test_health_succeeds_even_with_token(app):
    """/health is exempt from auth when token is set."""
    from aiohttp.test_utils import TestClient, TestServer

    os.environ["ARC_DAEMON_TOKEN"] = "test-token-123"
    try:
        async with TestServer(app) as server:
            async with TestClient(server) as c:
                r = await c.get("/health")
                assert r.status == 200
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)


async def test_mutating_request_rejects_untrusted_origin(client):
    r = await client.post(
        "/api/runs/start",
        json={"runtime": "auto"},
        headers={"Origin": "http://evil.example"},
    )
    assert r.status_code == 403


async def test_legacy_get_start_rejects_untrusted_origin(client):
    r = await client.get(
        "/api/runs/start?runtime=auto",
        headers={"Origin": "http://evil.example"},
    )
    assert r.status_code == 403


async def test_payload_limit_applies_globally(client):
    r = await client.post(
        "/api/providers/proxy/chat",
        data="x" * (513 * 1024),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413


async def test_invalid_workspace_header_returns_400(client):
    r = await client.get("/api/runs", headers={"X-ARC-Workspace": "/definitely/not/arc"})
    assert r.status_code == 400
    body = await r.json()
    assert body["error"]["code"] == "INVALID_INPUT"
