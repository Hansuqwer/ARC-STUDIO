"""Phase 50 — Trust Enforcement Surface Audit tests.

Verifies that every workspace-sensitive route enforces workspace trust
*before* reading any workspace data (trust-before-existence pattern).

Surfaces covered:
  - POST/GET /api/runs/start   (start_run)
  - GET  /api/runs             (list_runs)
  - GET  /api/runs/{run_id}    (get_run)
  - GET  /api/context/pack     (context_pack)
  - GET  /api/runs/{run_id}/links  (run_links)
  - POST /api/telemetry/export/{run_id}  (export_trace)
  - GET  /api/runs/diff        (runs_diff)
  - POST /api/evals/run        (runs_eval)
  - POST /api/arena/chat       (arena_chat)
  - POST /api/arena/vote       (arena_vote)
  - POST /api/arena/adopt      (arena_adopt)

Each test:
  1. Patches enforce_workspace_trust to raise TrustEnforcementError.
  2. Calls the route with a non-existent resource ID (trust-before-existence).
  3. Asserts HTTP 403 and PERMISSION_DENIED code — not 404/500/silent pass.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from agent_runtime_cockpit.security.enforcement import TrustEnforcementError
from agent_runtime_cockpit.web.keys import WORKSPACE_KEY
from agent_runtime_cockpit.web.routes import setup_routes

pytestmark = pytest.mark.asyncio

TRUST = "agent_runtime_cockpit.web.routes.enforce_workspace_trust"
_UNTRUSTED = TrustEnforcementError("workspace untrusted (phase 50 test)")


async def _client(workspace: Path) -> TestClient:
    app = web.Application()
    app[WORKSPACE_KEY] = workspace
    setup_routes(app)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def _permission_denied(body: dict) -> None:
    assert body["error"]["code"] == "PERMISSION_DENIED", f"expected PERMISSION_DENIED, got {body}"


# ── start_run ─────────────────────────────────────────────────────────────────


async def test_start_run_post_untrusted_returns_403(tmp_path: Path) -> None:
    """POST /api/runs/start returns 403 PERMISSION_DENIED before any run logic."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.post("/api/runs/start", json={"runtime": "auto"})
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


async def test_start_run_get_untrusted_returns_403(tmp_path: Path) -> None:
    """GET /api/runs/start returns 403 PERMISSION_DENIED before any run logic."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.get("/api/runs/start?runtime=auto")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── list_runs ─────────────────────────────────────────────────────────────────


async def test_list_runs_untrusted_returns_403(tmp_path: Path) -> None:
    """GET /api/runs returns 403 before reading trace store."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.get("/api/runs")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── get_run ───────────────────────────────────────────────────────────────────


async def test_get_run_untrusted_returns_403_not_404(tmp_path: Path) -> None:
    """GET /api/runs/{run_id} returns 403 before checking existence (oracle-leak guard)."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.get("/api/runs/nonexistent-run-id")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── context_pack ──────────────────────────────────────────────────────────────


async def test_context_pack_untrusted_returns_403(tmp_path: Path) -> None:
    """GET /api/context/pack returns 403 before scanning workspace files."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.get("/api/context/pack")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── run_links ─────────────────────────────────────────────────────────────────


async def test_run_links_untrusted_returns_403_not_404(tmp_path: Path) -> None:
    """GET /api/runs/{run_id}/links returns 403 before checking run existence."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.get("/api/runs/nonexistent/links")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── export_trace ──────────────────────────────────────────────────────────────


async def test_export_trace_untrusted_returns_403_not_404(tmp_path: Path) -> None:
    """POST /api/telemetry/export/{run_id} returns 403 before loading run."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.post(
                "/api/telemetry/export/nonexistent-run",
                json={"endpoint": "http://localhost:4317"},
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── runs_diff ─────────────────────────────────────────────────────────────────


async def test_runs_diff_untrusted_returns_403(tmp_path: Path) -> None:
    """GET /api/runs/diff returns 403 before loading either run."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.get("/api/runs/diff?run_a=a1&run_b=b2")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── runs_eval ─────────────────────────────────────────────────────────────────


async def test_runs_eval_untrusted_returns_403_not_404(tmp_path: Path) -> None:
    """POST /api/evals/run returns 403 before loading the run."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.post(
                "/api/evals/run",
                json={"run_id": "nonexistent", "golden": {"run_id": "g", "events": []}},
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── arena_chat ────────────────────────────────────────────────────────────────


async def test_arena_chat_untrusted_returns_403(tmp_path: Path) -> None:
    """POST /api/arena/chat returns 403 before processing arena request."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.post(
                "/api/arena/chat",
                json={"prompt": "hello", "mode": "direct", "models": ["gpt-4o"]},
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── arena_vote ────────────────────────────────────────────────────────────────


async def test_arena_vote_untrusted_returns_403_not_404(tmp_path: Path) -> None:
    """POST /api/arena/vote returns 403 before checking run existence."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.post(
                "/api/arena/vote",
                json={
                    "run_id": "nonexistent",
                    "winner_candidate_id": "c1",
                    "loser_candidate_id": "c2",
                },
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── arena_adopt ───────────────────────────────────────────────────────────────


async def test_arena_adopt_untrusted_returns_403(tmp_path: Path) -> None:
    """POST /api/arena/adopt returns 403 before processing any workspace patch."""
    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=_UNTRUSTED):
            resp = await client.post(
                "/api/arena/adopt",
                json={"run_id": "nonexistent", "candidate_id": "c1"},
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    _permission_denied(body)


# ── Consistent error code check (CLI vs daemon parity) ────────────────────────


async def test_trust_enforcement_error_code_consistent_across_surfaces(
    tmp_path: Path,
) -> None:
    """All surfaces return the same PERMISSION_DENIED code and 403 HTTP status.

    This confirms CLI-daemon parity: the same TrustEnforcementError maps to the
    same error envelope regardless of which route raises it.
    """
    client = await _client(tmp_path)
    surfaces = [
        ("GET", "/api/runs", None),
        ("GET", "/api/runs/x", None),
        ("GET", "/api/context/pack", None),
        ("GET", "/api/runs/x/links", None),
        ("GET", "/api/runs/diff?run_a=a&run_b=b", None),
        ("POST", "/api/runs/start", {"runtime": "auto"}),
        ("POST", "/api/telemetry/export/x", {"endpoint": "http://localhost:4317"}),
        ("POST", "/api/evals/run", {"run_id": "x", "golden": {"run_id": "g", "events": []}}),
        ("POST", "/api/arena/chat", {"prompt": "hi", "mode": "direct", "models": []}),
        (
            "POST",
            "/api/arena/vote",
            {"run_id": "x", "winner_candidate_id": "c1", "loser_candidate_id": "c2"},
        ),
        ("POST", "/api/arena/adopt", {"run_id": "x", "candidate_id": "c1"}),
    ]
    try:
        for method, path, body in surfaces:
            with patch(TRUST, side_effect=_UNTRUSTED):
                if method == "GET":
                    resp = await client.get(path)
                else:
                    resp = await client.post(path, json=body)
                rjson = await resp.json()
            assert resp.status == 403, f"{method} {path} returned {resp.status}, expected 403"
            assert rjson["error"]["code"] == "PERMISSION_DENIED", (
                f"{method} {path} returned code={rjson['error']['code']}"
            )
    finally:
        await client.close()
