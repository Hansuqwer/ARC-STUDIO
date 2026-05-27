"""Phase 46 — IDE write bridge / advisory lock integration for session writes.

Tests for:
- arc studio sessions write (stdin JSON import)
- arc studio sessions delete
- arc studio sessions update
- Advisory lock contention simulation
- Secret rejection, ID regex enforcement, workspace trust
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.cli_repl.session import SESSION_ID_RE, ChatSession
from agent_runtime_cockpit.storage.advisory_lock import AdvisoryLockUnavailable


# ── helpers ───────────────────────────────────────────────────────────────────

# Patch targets: lazy imports inside command functions resolve through these paths
_SESSIONS_DIR_PATH = "agent_runtime_cockpit.cli_repl.session._get_sessions_dir"
# enforce_workspace_trust is imported at the call site inside each command function body,
# so we patch it at the canonical module where it lives.
_ENFORCE_TRUST_PATH = "agent_runtime_cockpit.security.enforcement.enforce_workspace_trust"
_SAVE_PATH = "agent_runtime_cockpit.cli_repl.session.ChatSession.save"
# advisory_lock is also imported inside the delete command body; patch at its source
_LOCK_PATH = "agent_runtime_cockpit.storage.advisory_lock.advisory_lock"


def _make_session(sessions_dir: Path, suffix: str = "") -> ChatSession:
    """Create and persist a minimal ChatSession for tests."""
    s = ChatSession(id=f"s-test{suffix}")
    s.add_message("user", "hello")
    with patch(_SESSIONS_DIR_PATH, return_value=sessions_dir):
        s.save()
    return s


def _session_payload(session: ChatSession) -> dict[str, Any]:
    return session.model_dump(mode="json")


runner = CliRunner()


def _run_write(payload: dict[str, Any], sessions_dir: Path, trusted: bool = True) -> Any:
    """Invoke `arc studio sessions write --json` with payload on stdin."""
    stdin = json.dumps(payload)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=sessions_dir),
        _patched_trust(trusted=trusted),
    ):
        return runner.invoke(app, ["studio", "sessions", "write", "--json"], input=stdin)


def _patched_trust(trusted: bool = True) -> Any:
    """Context manager that patches enforce_workspace_trust.

    trusted=True  → no-op (let the action proceed)
    trusted=False → raises TrustEnforcementError (simulates untrusted workspace)
    """
    from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

    if trusted:
        return patch(_ENFORCE_TRUST_PATH, return_value=None)
    else:
        return patch(
            _ENFORCE_TRUST_PATH,
            side_effect=TrustEnforcementError("untrusted workspace"),
        )


# ── SESSION_ID_RE tests ────────────────────────────────────────────────────────


def test_session_id_re_allows_valid() -> None:
    assert SESSION_ID_RE.match("s-abc123")
    assert SESSION_ID_RE.match("session-1")
    assert SESSION_ID_RE.match("A" * 80)


def test_session_id_re_rejects_slash() -> None:
    assert not SESSION_ID_RE.match("../../etc/passwd")
    assert not SESSION_ID_RE.match("a/b")


def test_session_id_re_rejects_empty() -> None:
    assert not SESSION_ID_RE.match("")


def test_session_id_re_rejects_too_long() -> None:
    assert not SESSION_ID_RE.match("a" * 81)


# ── write command: valid import ────────────────────────────────────────────────


def test_write_valid_payload_imports_session(tmp_path: Path) -> None:
    s = ChatSession(id="s-validimport")
    s.add_message("user", "hello")
    payload = _session_payload(s)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code == 0, result.output
    out = json.loads(result.output.strip())
    assert out["ok"] is True
    assert out["data"]["session_id"] == s.id


def test_write_creates_session_file(tmp_path: Path) -> None:
    s = ChatSession(id="s-newimport")
    s.add_message("user", "hi from IDE")
    payload = _session_payload(s)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code == 0
    saved_path = tmp_path / s.id / "session.json"
    assert saved_path.exists()
    data = json.loads(saved_path.read_text())
    assert data["id"] == s.id


def test_write_roundtrip_via_load(tmp_path: Path) -> None:
    s = ChatSession(id="s-roundtrip")
    s.add_message("user", "round trip")
    payload = _session_payload(s)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
        assert result.exit_code == 0
        loaded = ChatSession.load(s.id)
    assert loaded is not None
    assert loaded.id == s.id


# ── write command: invalid inputs ─────────────────────────────────────────────


def test_write_rejects_invalid_json(tmp_path: Path) -> None:
    with _patched_trust(trusted=True):
        result = runner.invoke(app, ["studio", "sessions", "write", "--json"], input="NOT JSON")
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"


def test_write_rejects_secret_in_payload(tmp_path: Path) -> None:
    s = ChatSession(id="s-secrettest")
    payload = _session_payload(s)
    payload["metadata"] = {"api_key": "sk-secret1234567890"}
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"
    assert "secret" in out["error"]["message"].lower()


def test_write_rejects_unsafe_session_id(tmp_path: Path) -> None:
    s = ChatSession(id="s-valid")
    payload = _session_payload(s)
    payload["id"] = "../../etc/passwd"
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"


def test_write_caps_history_at_200(tmp_path: Path) -> None:
    s = ChatSession(id="s-histcap")
    for i in range(250):
        s.add_message("user", f"msg {i}")
    payload = _session_payload(s)
    assert len(payload["history"]) == 250
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code == 0
    saved_path = tmp_path / s.id / "session.json"
    data = json.loads(saved_path.read_text())
    assert len(data["history"]) <= 200


def test_write_denied_for_untrusted_workspace(tmp_path: Path) -> None:
    s = ChatSession(id="s-trusttest")
    payload = _session_payload(s)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=False),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "PERMISSION_DENIED"


def test_write_lock_contention_returns_lock_error(tmp_path: Path) -> None:
    s = ChatSession(id="s-locktest")
    payload = _session_payload(s)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
        patch(_SAVE_PATH, side_effect=AdvisoryLockUnavailable("lock timeout")),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "LOCK_CONTENTION"


# ── delete command ─────────────────────────────────────────────────────────────


def test_delete_existing_session(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-del")
    session_file = tmp_path / s.id / "session.json"
    assert session_file.exists()
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(app, ["studio", "sessions", "delete", s.id, "--json"])
    assert result.exit_code == 0
    out = json.loads(result.output.strip())
    assert out["ok"] is True
    assert not session_file.exists()


def test_delete_missing_session_returns_not_found(tmp_path: Path) -> None:
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(app, ["studio", "sessions", "delete", "s-nonexistent", "--json"])
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "RUN_NOT_FOUND"


def test_delete_rejects_unsafe_id(tmp_path: Path) -> None:
    result = runner.invoke(app, ["studio", "sessions", "delete", "../../evil", "--json"])
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"


def test_delete_denied_for_untrusted_workspace(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-deltrust")
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=False),
    ):
        result = runner.invoke(app, ["studio", "sessions", "delete", s.id, "--json"])
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "PERMISSION_DENIED"


def test_delete_lock_contention(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-dellck")
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
        patch(_LOCK_PATH, side_effect=AdvisoryLockUnavailable("lock timeout on delete")),
    ):
        result = runner.invoke(app, ["studio", "sessions", "delete", s.id, "--json"])
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "LOCK_CONTENTION"


# ── update command ─────────────────────────────────────────────────────────────


def test_update_allowed_field_mode(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-upd")
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app,
            ["studio", "sessions", "update", s.id, "--field", "mode", "--value", "plan", "--json"],
        )
    assert result.exit_code == 0
    out = json.loads(result.output.strip())
    assert out["ok"] is True
    assert out["data"]["field"] == "mode"


def test_update_rejects_history_field(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["studio", "sessions", "update", "s-any", "--field", "history", "--value", "[]", "--json"],
    )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"


def test_update_rejects_secret_field(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "studio",
            "sessions",
            "update",
            "s-any",
            "--field",
            "api_key",
            "--value",
            "sk-secret",
            "--json",
        ],
    )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"


def test_update_rejects_secret_in_value(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-updv")
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app,
            [
                "studio",
                "sessions",
                "update",
                s.id,
                "--field",
                "profile_id",
                "--value",
                "sk-secretABC123456",
                "--json",
            ],
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_INPUT"


def test_update_missing_session(tmp_path: Path) -> None:
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
    ):
        result = runner.invoke(
            app,
            [
                "studio",
                "sessions",
                "update",
                "s-ghost",
                "--field",
                "mode",
                "--value",
                "plan",
                "--json",
            ],
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "RUN_NOT_FOUND"


def test_update_denied_for_untrusted_workspace(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-updtrust")
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=False),
    ):
        result = runner.invoke(
            app,
            ["studio", "sessions", "update", s.id, "--field", "mode", "--value", "plan", "--json"],
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "PERMISSION_DENIED"


def test_update_lock_contention(tmp_path: Path) -> None:
    s = _make_session(tmp_path, suffix="-updlck")
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
        patch(_SAVE_PATH, side_effect=AdvisoryLockUnavailable("lock timeout on update")),
    ):
        result = runner.invoke(
            app,
            ["studio", "sessions", "update", s.id, "--field", "mode", "--value", "plan", "--json"],
        )
    assert result.exit_code != 0
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "LOCK_CONTENTION"


# ── concurrent lock simulation ────────────────────────────────────────────────


def test_concurrent_write_simulation_no_corruption(tmp_path: Path) -> None:
    """Two concurrent writes to the same session file.

    Both should complete without corrupting the JSON. The advisory lock ensures
    the second write waits for the first. We verify the final file is valid JSON.
    """
    session_id = "s-concurrent"
    results: list[tuple[bool, str]] = []

    def _do_write(suffix: str) -> None:
        s = ChatSession(id=session_id)
        s.add_message("user", f"message-{suffix}")
        with patch(_SESSIONS_DIR_PATH, return_value=tmp_path):
            s.save()
            results.append((True, suffix))

    t1 = threading.Thread(target=_do_write, args=("A",))
    t2 = threading.Thread(target=_do_write, args=("B",))
    t1.start()
    time.sleep(0.01)
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert len(results) == 2, f"Expected 2 writes, got {len(results)}"
    session_file = tmp_path / session_id / "session.json"
    assert session_file.exists()
    data = json.loads(session_file.read_text())
    assert data["id"] == session_id


def test_advisory_lock_unavailable_propagated(tmp_path: Path) -> None:
    """AdvisoryLockUnavailable is propagated as LOCK_CONTENTION in write command."""
    s = ChatSession(id="s-lockprop")
    payload = _session_payload(s)
    with (
        patch(_SESSIONS_DIR_PATH, return_value=tmp_path),
        _patched_trust(trusted=True),
        patch(_SAVE_PATH, side_effect=AdvisoryLockUnavailable("simulated timeout")),
    ):
        result = runner.invoke(
            app, ["studio", "sessions", "write", "--json"], input=json.dumps(payload)
        )
    out = json.loads(result.output.strip())
    assert out["ok"] is False
    assert out["error"]["code"] == "LOCK_CONTENTION"
    assert "timeout" in out["error"]["message"].lower() or "lock" in out["error"]["message"].lower()
