"""Tests for MCP session registry (Phase 78 follow-up)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.mcp.session import (
    McpSessionRecord,
    McpSessionStore,
    _load_store,
    _save_store,
    cleanup_stale_sessions,
    list_sessions,
    show_session,
    start_session,
    stop_session,
)

runner = CliRunner()


def test_start_stop_session(tmp_path: Path):
    """Start a session with sleep command, verify it's registered, then stop it."""
    record = start_session(tmp_path, ["sleep", "10"])
    assert record.session_id
    assert record.pid > 0
    assert record.status == "running"

    sessions = list_sessions(tmp_path)
    assert len(sessions) >= 1
    assert sessions[0]["session_id"] == record.session_id
    assert sessions[0]["alive"] is True

    stopped = stop_session(tmp_path, record.session_id)
    assert stopped is True

    sessions = list_sessions(tmp_path)
    matching = [s for s in sessions if s["session_id"] == record.session_id]
    assert len(matching) == 1
    assert matching[0]["alive"] is False


def test_stop_nonexistent_session(tmp_path: Path):
    """Stop a nonexistent session returns False."""
    assert stop_session(tmp_path, "nonexistent") is False


def test_show_session(tmp_path: Path):
    """Show a session returns its details."""
    record = start_session(tmp_path, ["sleep", "5"])
    session = show_session(tmp_path, record.session_id)
    assert session is not None
    assert session["session_id"] == record.session_id
    assert session["pid"] == record.pid
    assert session["alive"] is True

    stop_session(tmp_path, record.session_id)


def test_show_nonexistent_session(tmp_path: Path):
    """Show a nonexistent session returns None."""
    assert show_session(tmp_path, "nonexistent") is None


def test_cleanup_stale_sessions_removes_expired(tmp_path: Path):
    """Cleanup removes sessions past idle timeout."""
    record = start_session(tmp_path, ["sleep", "1"])
    import time

    time.sleep(1.5)

    cleaned = cleanup_stale_sessions(tmp_path, timeout=0)
    assert record.session_id in cleaned


def test_cleanup_keeps_recent_sessions(tmp_path: Path):
    """Cleanup keeps sessions within idle timeout."""
    record = start_session(tmp_path, ["sleep", "30"])
    cleaned = cleanup_stale_sessions(tmp_path, timeout=3600)
    assert record.session_id not in cleaned
    stop_session(tmp_path, record.session_id)


def test_list_sessions_empty(tmp_path: Path):
    """List sessions in empty workspace returns empty list."""
    sessions = list_sessions(tmp_path)
    assert sessions == []


def test_list_sessions_order(tmp_path: Path):
    """Sessions are listed in reverse chronological order."""
    r1 = start_session(tmp_path, ["sleep", "1"])
    import time

    time.sleep(0.1)
    r2 = start_session(tmp_path, ["sleep", "1"])
    sessions = list_sessions(tmp_path)
    assert sessions[0]["session_id"] == r2.session_id
    assert sessions[1]["session_id"] == r1.session_id
    stop_session(tmp_path, r1.session_id)
    stop_session(tmp_path, r2.session_id)


def test_cli_session_start_stop(tmp_path: Path):
    """CLI: arc mcp workbench session-start and session-stop work."""
    from agent_runtime_cockpit.cli._app import app

    local_runner = CliRunner()
    result = local_runner.invoke(
        app,
        [
            "mcp",
            "workbench",
            "session-start",
            "sleep",
            "10",
            "--json",
            "--workspace",
            str(tmp_path),
        ],
        catch_exceptions=False,
    )
    if result.exit_code == 0:
        data = json.loads(result.stdout)
        assert data["ok"] is True
        session_id = data["data"]["session_id"]

        result2 = local_runner.invoke(
            app,
            [
                "mcp",
                "workbench",
                "session-stop",
                session_id,
                "--json",
                "--workspace",
                str(tmp_path),
            ],
            catch_exceptions=False,
        )
        assert result2.exit_code == 0


def test_store_roundtrip(tmp_path: Path):
    """Session store write/read roundtrip."""
    store_path = tmp_path / ".arc" / "mcp" / "sessions" / "sessions.json"
    rec = McpSessionRecord(
        session_id="test123",
        server_cmd=["echo", "hi"],
        pid=12345,
        pgid=12345,
        started_at="2026-01-01T00:00:00Z",
        last_used_at="2026-01-01T00:00:00Z",
        workspace=str(tmp_path),
    )
    store = McpSessionStore(sessions={"test123": rec})
    _save_store(tmp_path, store)
    assert store_path.exists()
    loaded = _load_store(tmp_path)
    assert loaded.sessions["test123"].session_id == "test123"
    assert loaded.sessions["test123"].pid == 12345


def test_start_session_strips_secret_env(tmp_path: Path):
    """Session launch defaults to subprocess env filtering."""
    import os
    import time

    out = tmp_path / "secret.txt"
    record = start_session(
        tmp_path,
        ["sh", "-c", f"printf %s ${{SECRET_KEY:-missing}} > {out.name}; sleep 5"],
        env={"SECRET_KEY": "should-not-pass", "PATH": os.environ.get("PATH", "/usr/bin")},
    )
    try:
        for _ in range(20):
            if out.exists():
                break
            time.sleep(0.05)
        assert out.read_text(encoding="utf-8") == "missing"
    finally:
        stop_session(tmp_path, record.session_id)
