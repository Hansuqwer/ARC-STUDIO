"""Tests: ARC Studio chat-first CLI entry point (cli_studio.py shim).

The cli_studio.py module is now a thin shim that delegates to cli_repl.
These tests verify the shim still provides the expected CLI behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli_studio import app
from agent_runtime_cockpit.cli_repl.session import (
    ChatSession,
    MODE_PLAN,
    MODE_BUILD,
    MODE_AUTO,
    SESSION_SCHEMA_VERSION,
    _get_sessions_dir,
)

runner = CliRunner()


class TestBanner:
    def test_no_arg_shows_banner(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "ARC Studio" in result.stdout

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ARC Studio v" in result.stdout


class TestSessionPersistence:
    def test_session_roundtrip(self, tmp_path):
        """Verify ChatSession serialization roundtrip."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        s = ChatSession(mode=MODE_PLAN)
        s.add_message("user", "hello")
        s.add_message("assistant", "hi")

        # Write as canonical format (dir/session.json)
        sess_dir = session_dir / s.id
        sess_dir.mkdir(parents=True, exist_ok=True)
        path = sess_dir / "session.json"
        path.write_text(s.model_dump_json(indent=2), encoding="utf-8")

        loaded_data = json.loads(path.read_text())
        assert loaded_data["id"] == s.id
        assert loaded_data["mode"] == MODE_PLAN
        assert len(loaded_data["history"]) == 2
        assert loaded_data["history"][0]["role"] == "user"
        assert loaded_data["history"][0]["content"] == "hello"
        assert loaded_data["version"] == SESSION_SCHEMA_VERSION
        assert loaded_data["runtime_mode"] == "fake"
        assert loaded_data["profile_id"] == "default"
        assert loaded_data["isolation_id"] == "none"

    def test_v1_session_migrates_to_v2(self):
        loaded = ChatSession.model_validate({
            "version": 1,
            "id": "s-old",
            "mode": MODE_BUILD,
            "runtime_mode": "offline",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "history": [],
            "metadata": {},
        })
        assert loaded.version == SESSION_SCHEMA_VERSION
        assert loaded.runtime_mode == "fake"
        assert loaded.profile_id == "default"
        assert loaded.isolation_id == "none"
        assert loaded.tools_enabled is False
        assert loaded.max_tool_iterations == 10
        assert loaded.available_tools is None

    def test_v3_session_migrates_to_v4_tool_fields(self):
        loaded = ChatSession.model_validate({
            "version": 3,
            "id": "s-v3",
            "mode": MODE_BUILD,
            "runtime_mode": "provider_backed",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "history": [],
            "metadata": {},
        })
        assert loaded.version == SESSION_SCHEMA_VERSION
        assert loaded.runtime_mode == "provider_backed"
        assert loaded.allow_paid_calls is True
        assert loaded.tools_enabled is False
        assert loaded.max_tool_iterations == 10
        assert loaded.available_tools is None

    def test_v4_session_preserves_tool_allowlist(self):
        loaded = ChatSession.model_validate({
            "version": 4,
            "id": "s-v4",
            "mode": MODE_BUILD,
            "runtime_mode": "fake",
            "tools_enabled": True,
            "max_tool_iterations": 3,
            "available_tools": ["get_current_time"],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "history": [],
            "metadata": {},
        })
        assert loaded.version == SESSION_SCHEMA_VERSION
        assert loaded.tools_enabled is True
        assert loaded.max_tool_iterations == 3
        assert loaded.available_tools == ["get_current_time"]

    def test_session_save_and_load(self, tmp_path):
        """Verify ChatSession save/load with custom sessions dir."""
        from agent_runtime_cockpit.cli_repl.session import SESSION_SCHEMA_VERSION

        # Use a custom sessions dir via the env var
        custom_dir = tmp_path / "custom_sessions"
        import os
        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(custom_dir)

        try:
            s = ChatSession()
            s.add_message("user", "test")
            path = s.save()
            assert path.exists()
            assert path.parent.name == s.id

            loaded = ChatSession.load(s.id)
            assert loaded is not None
            assert loaded.id == s.id
            assert len(loaded.history) == 1
            assert loaded.history[0]["content"] == "test"
            assert loaded.version == SESSION_SCHEMA_VERSION
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_session_list(self, tmp_path):
        """Verify session listing with custom dir."""
        import os
        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "sessions_list")
        try:
            s1 = ChatSession()
            s1.save()
            s2 = ChatSession()
            s2.save()

            sessions = ChatSession.list_sessions()
            session_ids = [s.id for s in sessions]
            assert s1.id in session_ids
            assert s2.id in session_ids
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_load_nonexistent_returns_none(self):
        loaded = ChatSession.load("nonexistent-session-id")
        assert loaded is None

    def test_session_state_tracks_mode(self):
        session = ChatSession()
        assert session.mode == MODE_BUILD
        session.set_mode(MODE_PLAN)
        assert session.mode == MODE_PLAN
        session.set_mode(MODE_AUTO)
        assert session.mode == MODE_AUTO
        session.set_mode(MODE_BUILD)
        assert session.mode == MODE_BUILD

    def test_session_state_rejects_invalid_mode(self):
        session = ChatSession(mode=MODE_BUILD)
        session.set_mode("invalid")
        assert session.mode == MODE_BUILD


class TestLegacyReadCompat:
    def test_read_legacy_flat_session(self, tmp_path):
        """Verify legacy flat StudioSession JSON can be read."""
        from agent_runtime_cockpit.cli_repl.session import _read_legacy_session
        import os
        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "legacy_read")
        try:
            sid = "legacy-session-001"
            legacy_data = {
                "session_id": sid,
                "mode": "plan",
                "messages": [
                    {"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00"},
                    {"role": "assistant", "content": "hi", "timestamp": "2026-01-01T00:00:01"},
                ],
                "created": "2026-01-01T00:00:00",
                "updated": "2026-01-01T00:00:01",
            }
            legacy_dir = tmp_path / "legacy_read"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            (legacy_dir / f"{sid}.json").write_text(
                json.dumps(legacy_data), encoding="utf-8"
            )

            loaded = ChatSession.load(sid)
            assert loaded is not None
            assert loaded.id == sid
            assert loaded.mode == MODE_PLAN  # plan → canonical plan
            assert loaded.metadata["source_trust"] == "workspace"
            assert loaded.history[0]["source_trust"] == "workspace"
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)
