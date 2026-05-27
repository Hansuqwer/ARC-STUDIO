from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.events.bus import get_bus, reset_bus
from agent_runtime_cockpit.storage.advisory_lock import AdvisoryLockUnavailable
from agent_runtime_cockpit.web.keys import WORKSPACE_KEY
from agent_runtime_cockpit.web.routes import setup_routes

pytestmark = pytest.mark.asyncio

SESSIONS_DIR = "agent_runtime_cockpit.cli_repl.session._get_sessions_dir"
TRUST = "agent_runtime_cockpit.web.routes.enforce_workspace_trust"
SAVE = "agent_runtime_cockpit.cli_repl.session.ChatSession.save"
LOCK = "agent_runtime_cockpit.web.routes.advisory_lock"


async def _client(workspace: Path) -> TestClient:
    app = web.Application()
    app[WORKSPACE_KEY] = workspace
    setup_routes(app)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def _payload(session_id: str = "s-daemon") -> dict[str, Any]:
    s = ChatSession(id=session_id)
    s.add_message("user", "hello")
    return s.model_dump(mode="json")


async def test_sessions_write_valid_payload(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.post("/api/sessions/write", json=_payload("s-write"))
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 200
    assert body["ok"] is True
    assert (tmp_path / "s-write" / "session.json").exists()


async def test_sessions_write_invalid_json(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        resp = await client.post("/api/sessions/write", data="not-json")
        body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_write_secret_payload(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    payload = _payload("s-secret")
    payload["metadata"] = {"api_key": "sk-secret1234567890"}
    try:
        with patch(TRUST):
            resp = await client.post("/api/sessions/write", json=payload)
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_write_unsafe_id(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    payload = _payload("s-safe")
    payload["id"] = "../../evil"
    try:
        with patch(TRUST):
            resp = await client.post("/api/sessions/write", json=payload)
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_write_untrusted_workspace(tmp_path: Path) -> None:
    from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

    client = await _client(tmp_path)
    try:
        with patch(TRUST, side_effect=TrustEnforcementError("untrusted")):
            resp = await client.post("/api/sessions/write", json=_payload("s-untrusted"))
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    assert body["error"]["code"] == "PERMISSION_DENIED"


async def test_sessions_write_lock_timeout(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        with patch(TRUST), patch(SAVE, side_effect=AdvisoryLockUnavailable("lock timeout")):
            resp = await client.post("/api/sessions/write", json=_payload("s-lock"))
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 429
    assert body["error"]["code"] == "LOCK_CONTENTION"


async def test_sessions_write_payload_too_large(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        resp = await client.post(
            "/api/sessions/write",
            data=json.dumps({"id": "s-big", "blob": "x" * (513 * 1024)}),
            headers={"Content-Type": "application/json"},
        )
        body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_write_caps_history(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    payload = _payload("s-cap")
    payload["history"] = [{"role": "user", "content": str(i)} for i in range(250)]
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.post("/api/sessions/write", json=payload)
    finally:
        await client.close()
    assert resp.status == 200
    saved = json.loads((tmp_path / "s-cap" / "session.json").read_text())
    assert len(saved["history"]) == 200


async def test_sessions_delete_existing(tmp_path: Path) -> None:
    s = ChatSession(id="s-delete")
    with patch(SESSIONS_DIR, return_value=tmp_path):
        s.save()
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.delete("/api/sessions/s-delete")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 200
    assert body["ok"] is True
    assert not (tmp_path / "s-delete" / "session.json").exists()


async def test_sessions_delete_missing(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.delete("/api/sessions/s-missing")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 404
    assert body["error"]["code"] == "RUN_NOT_FOUND"


async def test_sessions_delete_unsafe_id(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        resp = await client.delete("/api/sessions/..%2Fevil")
        body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_delete_untrusted_workspace_checks_trust_before_existence(
    tmp_path: Path,
) -> None:
    from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

    client = await _client(tmp_path)
    try:
        with (
            patch(SESSIONS_DIR, return_value=tmp_path),
            patch(TRUST, side_effect=TrustEnforcementError("untrusted")),
        ):
            resp = await client.delete("/api/sessions/s-missing")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    assert body["error"]["code"] == "PERMISSION_DENIED"


async def test_sessions_delete_lock_timeout(tmp_path: Path) -> None:
    s = ChatSession(id="s-del-lock")
    with patch(SESSIONS_DIR, return_value=tmp_path):
        s.save()
    client = await _client(tmp_path)
    try:
        with (
            patch(SESSIONS_DIR, return_value=tmp_path),
            patch(TRUST),
            patch(LOCK, side_effect=AdvisoryLockUnavailable("lock timeout")),
        ):
            resp = await client.delete("/api/sessions/s-del-lock")
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 429
    assert body["error"]["code"] == "LOCK_CONTENTION"


async def test_sessions_update_valid_field(tmp_path: Path) -> None:
    s = ChatSession(id="s-update")
    with patch(SESSIONS_DIR, return_value=tmp_path):
        s.save()
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.patch(
                "/api/sessions/s-update", json={"field": "mode", "value": "plan"}
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 200
    assert body["ok"] is True


async def test_sessions_update_disallowed_field(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        resp = await client.patch("/api/sessions/s-any", json={"field": "history", "value": "[]"})
        body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_update_secret_value(tmp_path: Path) -> None:
    s = ChatSession(id="s-up-secret")
    with patch(SESSIONS_DIR, return_value=tmp_path):
        s.save()
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.patch(
                "/api/sessions/s-up-secret",
                json={"field": "profile_id", "value": "sk-secretABC123456"},
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 400
    assert body["error"]["code"] == "INVALID_INPUT"


async def test_sessions_update_missing(tmp_path: Path) -> None:
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            resp = await client.patch(
                "/api/sessions/s-nope", json={"field": "mode", "value": "plan"}
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 404
    assert body["error"]["code"] == "RUN_NOT_FOUND"


async def test_sessions_update_untrusted_workspace_checks_trust_before_load(
    tmp_path: Path,
) -> None:
    from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

    client = await _client(tmp_path)
    try:
        with (
            patch(SESSIONS_DIR, return_value=tmp_path),
            patch(TRUST, side_effect=TrustEnforcementError("untrusted")),
        ):
            resp = await client.patch(
                "/api/sessions/s-missing", json={"field": "mode", "value": "plan"}
            )
            body = await resp.json()
    finally:
        await client.close()
    assert resp.status == 403
    assert body["error"]["code"] == "PERMISSION_DENIED"


async def test_session_changed_emitted_on_success_and_not_error(tmp_path: Path) -> None:
    reset_bus()
    seen = []
    get_bus().subscribe_all(lambda event: seen.append(event))
    client = await _client(tmp_path)
    try:
        with patch(SESSIONS_DIR, return_value=tmp_path), patch(TRUST):
            ok_resp = await client.post("/api/sessions/write", json=_payload("s-event"))
            bad_resp = await client.post("/api/sessions/write", json={"id": "../../bad"})
    finally:
        await client.close()
    assert ok_resp.status == 200
    assert bad_resp.status == 400
    session_events = [event for event in seen if event.event_type == "session_changed"]
    assert len(session_events) == 1
    assert session_events[0].session_id == "s-event"
    assert session_events[0].operation == "write"
    assert session_events[0].payload["coverage_class"] == "session_lifecycle_ephemeral"
    assert session_events[0].payload["audit_persistence"] == "excluded"
    assert "not part of per-run audit chain" in session_events[0].payload["exclusion_reason"]
