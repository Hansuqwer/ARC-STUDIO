"""Tests: ARC Studio chat-first CLI entry point (cli_studio.py)."""
from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli_studio import app, StudioSession, SESSION_DIR, MODE_PLAN, MODE_BUILD, MODE_AUTO

runner = CliRunner()


class TestBanner:
    def test_no_arg_shows_banner(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "ARC Studio" in result.stdout
        assert "/help" in result.stdout

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ARC Studio v" in result.stdout


class TestSlashCommands:
    def test_help_lists_commands(self):
        result = runner.invoke(app, ["/help"])
        assert result.exit_code == 0
        assert "/help" in result.stdout
        assert "/status" in result.stdout
        assert "/doctor" in result.stdout
        assert "/runs" in result.stdout
        assert "/plan" in result.stdout
        assert "/build" in result.stdout
        assert "/auto" in result.stdout
        assert "/exit" in result.stdout

    def test_unknown_slash_command(self):
        result = runner.invoke(app, ["/nonexistent"])
        assert result.exit_code == 0
        assert "Unknown command" in result.stdout

    def test_status_shows_info(self):
        result = runner.invoke(app, ["/status"])
        assert result.exit_code == 0
        assert "Workspace" in result.stdout
        assert "Mode" in result.stdout
        assert "BUILD" in result.stdout

    def test_doctor_runs_checks(self):
        result = runner.invoke(app, ["/doctor"])
        assert result.exit_code == 0
        assert "✓" in result.stdout or "✗" in result.stdout

    def test_runs_with_no_traces(self):
        result = runner.invoke(app, ["/runs"])
        assert result.exit_code == 0


class TestModeSwitching:
    def test_plan_switches_mode(self):
        result = runner.invoke(app, ["/plan"])
        assert result.exit_code == 0
        assert "Plan" in result.stdout

    def test_build_switches_mode(self):
        result = runner.invoke(app, ["/build"])
        assert result.exit_code == 0
        assert "Build" in result.stdout

    def test_auto_switches_mode(self):
        result = runner.invoke(app, ["/auto"])
        assert result.exit_code == 0
        assert "Auto" in result.stdout

    def test_session_state_tracks_mode(self):
        session = StudioSession("test-session")
        assert session.mode == MODE_BUILD
        session.set_mode(MODE_PLAN)
        assert session.mode == MODE_PLAN
        session.set_mode(MODE_AUTO)
        assert session.mode == MODE_AUTO
        session.set_mode(MODE_BUILD)
        assert session.mode == MODE_BUILD

    def test_session_state_rejects_invalid_mode(self):
        session = StudioSession("test-session", mode=MODE_BUILD)
        session.set_mode("invalid")
        assert session.mode == MODE_BUILD


class TestOneShot:
    def test_oneshot_exits_zero(self):
        result = runner.invoke(app, ["hello world"])
        assert result.exit_code == 0

    def test_oneshot_echoes_message(self):
        result = runner.invoke(app, ["hello world"])
        assert result.exit_code == 0
        assert "hello world" in result.stdout or "You said" in result.stdout

    def test_oneshot_help(self):
        result = runner.invoke(app, ["/help"])
        assert result.exit_code == 0
        assert "/status" in result.stdout

    def test_oneshot_unknown_command(self):
        result = runner.invoke(app, ["/bogus"])
        assert result.exit_code == 0
        assert "Unknown command" in result.stdout

    def test_oneshot_mode_switch(self):
        result = runner.invoke(app, ["/plan"])
        assert result.exit_code == 0
        assert "Plan" in result.stdout

    def test_oneshot_exit(self):
        result = runner.invoke(app, ["/exit"])
        assert result.exit_code == 0
        assert "Session saved" in result.stdout


class TestSessionPersistence:
    def test_session_roundtrip(self, tmp_path):
        sid = "test-roundtrip-001"
        session = StudioSession(sid, mode=MODE_PLAN)
        session.add_message("user", "hello")
        session.add_message("assistant", "hi")

        (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
        path = tmp_path / "sessions" / f"{sid}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")

        loaded_data = json.loads(path.read_text())
        assert loaded_data["session_id"] == sid
        assert loaded_data["mode"] == MODE_PLAN
        assert len(loaded_data["messages"]) == 2
        assert loaded_data["messages"][0]["role"] == "user"
        assert loaded_data["messages"][0]["content"] == "hello"

    def test_session_save_and_load(self, tmp_path):
        sid = "test-save-load-001"
        session_dir = tmp_path / "sessions"
        session = StudioSession(sid)
        session.add_message("user", "test")
        session.save(session_dir=session_dir)

        loaded = StudioSession.load(sid, session_dir=session_dir)
        assert loaded is not None
        assert loaded.session_id == sid
        assert len(loaded.messages) == 1
        assert loaded.messages[0]["content"] == "test"

    def test_session_list(self, tmp_path):
        sid1, sid2 = "list-ses-001", "list-ses-002"
        session_dir = tmp_path / "sessions"
        s1 = StudioSession(sid1)
        s1.save(session_dir=session_dir)
        s2 = StudioSession(sid2)
        s2.save(session_dir=session_dir)

        sessions = StudioSession.list_sessions(session_dir=session_dir)
        assert sid1 in sessions
        assert sid2 in sessions

    def test_load_nonexistent_returns_none(self):
        loaded = StudioSession.load("nonexistent-session-id")
        assert loaded is None

    def test_oneshot_does_not_write_real_session_dir(self, tmp_path):
        before = set(SESSION_DIR.glob("*.json")) if SESSION_DIR.exists() else set()
        result = runner.invoke(app, ["hello isolated world"])
        after = set(SESSION_DIR.glob("*.json")) if SESSION_DIR.exists() else set()
        assert result.exit_code == 0
        assert after == before
