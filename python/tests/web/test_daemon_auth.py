"""Tests for the optional ARC_DAEMON_TOKEN bearer-token auth.

These tests verify the middleware in python/src/agent_runtime_cockpit/web/server.py.
See docs/SECURITY_AUDIT_REPORT.md R-6 for design details.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.asyncio


async def test_no_token_set_allows_all(client):
    """When ARC_DAEMON_TOKEN is unset, all requests succeed."""
    r = await client.get("/api/runs")
    assert r.status_code == 200


async def test_health_allows_without_token(client):
    """/health always succeeds regardless of token setting."""
    r = await client.get("/health")
    assert r.status_code == 200


async def test_request_without_token_rejected(app):
    """When token is set, requests without auth header get 401."""
    import aiohttp.web as web
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
    import aiohttp.web as web
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
    import aiohttp.web as web
    from aiohttp.test_utils import TestClient, TestServer

    os.environ["ARC_DAEMON_TOKEN"] = "correct-token"
    try:
        async with TestServer(app) as server:
            async with TestClient(server) as c:
                r = await c.get("/api/runs", headers={"Authorization": "Bearer correct-token"})
                assert r.status == 200
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)


async def test_health_succeeds_even_with_token(app):
    """/health is exempt from auth when token is set."""
    import aiohttp.web as web
    from aiohttp.test_utils import TestClient, TestServer

    os.environ["ARC_DAEMON_TOKEN"] = "test-token-123"
    try:
        async with TestServer(app) as server:
            async with TestClient(server) as c:
                r = await c.get("/health")
                assert r.status == 200
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)
