from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import SlashCommandHandler


class TestChatSession:
    def test_uses_session_dir_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        s = ChatSession()
        s.add_message("user", "isolated")
        path = s.save()
        assert tmp_path in path.parents
        assert ChatSession.load(s.id) is not None

    def test_create_session(self):
        s = ChatSession()
        assert s.id.startswith("s-")
        assert s.history == []

    def test_add_message(self):
        s = ChatSession()
        s.add_message("user", "hello")
        assert len(s.history) == 1
        assert s.history[0]["role"] == "user"
        assert s.history[0]["content"] == "hello"

    def test_save_and_load(self, tmp_path):
        s = ChatSession()
        s.add_message("user", "test")
        path = s.save()
        assert path.exists()
        loaded = ChatSession.load(s.id)
        assert loaded is not None
        assert loaded.id == s.id
        assert len(loaded.history) == 1

    def test_list_and_latest_use_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        assert ChatSession.list_sessions() == []
        assert ChatSession.latest() is None
        s = ChatSession()
        s.save()
        assert ChatSession.list_sessions()[0].id == s.id
        assert ChatSession.latest().id == s.id

    def test_load_nonexistent(self):
        loaded = ChatSession.load("nonexistent-id")
        assert loaded is None


class TestSlashCommands:
    def test_help(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/help", s)
        assert result is not None
        assert "/help" in result

    def test_clear(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        s.add_message("user", "hello")
        result = handler.handle("/clear", s)
        assert "cleared" in result
        assert len(s.history) == 0

    def test_summary_empty(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/summary", s)
        assert "0 messages" in result

    def test_summary_with_messages(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        s.add_message("user", "hi")
        result = handler.handle("/summary", s)
        assert "1 messages" in result

    def test_run(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/run hello world", s)
        assert result is not None
        assert "completed" in result

    def test_run_blocked_in_plan_mode(self):
        handler = SlashCommandHandler()
        s = ChatSession(mode="plan")
        result = handler.handle("/run hello world", s)
        assert result is not None
        assert "Blocked" in result

    def test_run_accepts_cancellation_token(self):
        class Cancelled:
            def is_cancelled(self) -> bool:
                return True

        handler = SlashCommandHandler()
        handler.cancellation_token = Cancelled()
        s = ChatSession()
        result = handler.handle("/run hello world", s)
        assert result is not None
        assert "cancelled" in result

    def test_run_no_arg(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/run", s)
        assert "Usage" in result

    def test_history_empty(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/history", s)
        assert "No messages" in result

    def test_history_with_messages(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        s.add_message("user", "msg1")
        s.add_message("assistant", "reply1")
        result = handler.handle("/history", s)
        assert "[user]" in result
        assert "[assistant]" in result

    def test_version(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/version", s)
        assert "ARC Studio" in result
        assert "SwarmGraph" in result

    def test_quit(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/quit", s)
        assert result == "__EXIT__"

    def test_exit(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/exit", s)
        assert result == "__EXIT__"

    def test_unknown_slash(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/foobar", s)
        assert "Unknown" in result

    def test_non_slash_returns_none(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("hello", s)
        assert result is None


class TestFormatResult:
    def test_format_completed(self):
        from agent_runtime_cockpit.cli_repl.chat_repl import _format_result
        result = {
            "status": "completed",
            "total_tasks": 3,
            "completed_tasks": 3,
            "total_cost_usd": 0.0,
            "results": [
                {"task_id": "t1", "output": "done", "status": "completed"}
            ],
        }
        formatted = _format_result(result)
        assert "completed" in formatted
        assert "3/3 tasks" in formatted
        assert "done" in formatted

    def test_format_no_results(self):
        from agent_runtime_cockpit.cli_repl.chat_repl import _format_result
        result = {
            "status": "completed",
            "total_tasks": 0,
            "completed_tasks": 0,
            "total_cost_usd": 0.0,
            "results": [],
        }
        formatted = _format_result(result)
        assert "0/0 tasks" in formatted


class TestMergedSlashCommands:
    """Tests for slash commands merged from cli_studio.py into cli_repl."""

    def test_plan_switches_mode(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/plan", s)
        assert result is not None
        assert "Plan" in result
        assert s.mode == "plan"

    def test_build_switches_mode(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/build", s)
        assert result is not None
        assert "Build" in result
        assert s.mode == "build"

    def test_auto_switches_mode(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/auto", s)
        assert result is not None
        assert "Auto" in result
        assert s.mode == "auto"

    def test_status_shows_info(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/status", s)
        assert result is not None
        assert "Workspace" in result
        assert "BUILD" in result

    def test_doctor_runs_checks(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/doctor", s)
        assert result is not None
        assert "✓" in result or "✗" in result

    def test_runs_with_no_traces(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/runs", s)
        assert result is not None
        assert "No runs" in result

    def test_status_after_mode_switch(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        handler.handle("/plan", s)
        result = handler.handle("/status", s)
        assert result is not None
        assert "PLAN" in result


class TestCommandRegistry:
    def test_register_and_lookup(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandRegistry, CommandDef

        registry = CommandRegistry()
        cmd = CommandDef(name="test", help_text="A test", category="meta", handler=lambda a, s: "ok")
        registry.register(cmd)
        assert registry.has("test")
        assert registry.get("test") is cmd

    def test_alias_resolution(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandRegistry, CommandDef

        registry = CommandRegistry()
        cmd = CommandDef(
            name="exit", help_text="Exit", category="meta",
            handler=lambda a, s: "__EXIT__", aliases=["quit"],
        )
        registry.register(cmd)
        assert registry.get("quit") is cmd
        assert registry.get("/quit") is cmd
        assert registry.get("EXIT") is cmd

    def test_duplicate_detection(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandRegistry, CommandDef

        registry = CommandRegistry()
        cmd = CommandDef(name="dup", help_text="First", category="meta", handler=lambda a, s: "1")
        registry.register(cmd)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(cmd)

    def test_duplicate_alias_detection(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandRegistry, CommandDef

        registry = CommandRegistry()
        registry.register(CommandDef(
            name="first", help_text="First", category="meta",
            handler=lambda a, s: "1", aliases=["shared"],
        ))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(CommandDef(
                name="second", help_text="Second", category="meta",
                handler=lambda a, s: "2", aliases=["shared"],
            ))

    def test_list_by_category(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandRegistry, CommandDef

        registry = CommandRegistry()
        registry.register(CommandDef(name="help", help_text="Help", category="meta", handler=lambda a, s: "h"))
        registry.register(CommandDef(name="run", help_text="Run", category="runtime", handler=lambda a, s: "r"))
        registry.register(CommandDef(name="status", help_text="Status", category="workspace", handler=lambda a, s: "s"))

        meta_cmds = registry.list_commands("meta")
        assert len(meta_cmds) == 1
        assert meta_cmds[0].name == "help"

        all_cmds = registry.list_commands()
        assert len(all_cmds) == 3

    def test_categories(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandRegistry, CommandDef

        registry = CommandRegistry()
        registry.register(CommandDef(name="a", help_text="A", category="meta", handler=lambda a, s: "a"))
        registry.register(CommandDef(name="b", help_text="B", category="runtime", handler=lambda a, s: "b"))
        cats = registry.categories()
        assert "meta" in cats
        assert "runtime" in cats

    def test_registered_commands_have_explicit_metadata(self):
        handler = SlashCommandHandler()
        for cmd in handler._registry.list_commands():
            assert cmd.category
            assert isinstance(cmd.gates_required, list)
            assert isinstance(cmd.mode_required, list)
            assert cmd.renders, cmd.name
            assert isinstance(cmd.requires_events, list)
            assert cmd.trust_required in {"system", "user", "workspace"}
            assert isinstance(cmd.privileged, bool)
            assert isinstance(cmd.visible_in_ide, bool)
            assert isinstance(cmd.popup_visible, bool)


class TestSessionMigration:
    def test_detect_legacy_sessions(self, tmp_path):
        import json
        import os
        from agent_runtime_cockpit.cli_repl.session import _detect_legacy_sessions

        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "migrate_detect")
        try:
            sess_dir = tmp_path / "migrate_detect"
            sess_dir.mkdir(parents=True, exist_ok=True)
            legacy = {
                "session_id": "legacy-001",
                "mode": "build",
                "messages": [{"role": "user", "content": "hi"}],
                "created": "2026-01-01T00:00:00",
                "updated": "2026-01-01T00:00:00",
            }
            (sess_dir / "legacy-001.json").write_text(json.dumps(legacy), encoding="utf-8")

            detected = _detect_legacy_sessions(sess_dir)
            assert len(detected) == 1
            assert detected[0]["session_id"] == "legacy-001"
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_detect_skips_latest_symlink(self, tmp_path):
        import json
        import os
        from agent_runtime_cockpit.cli_repl.session import _detect_legacy_sessions

        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "migrate_skip")
        try:
            sess_dir = tmp_path / "migrate_skip"
            sess_dir.mkdir(parents=True, exist_ok=True)
            legacy = {
                "session_id": "real-session",
                "mode": "build",
                "messages": [],
            }
            (sess_dir / "real-session.json").write_text(json.dumps(legacy), encoding="utf-8")
            # "latest" should be skipped
            (sess_dir / "latest").write_text("some-session.json", encoding="utf-8")

            detected = _detect_legacy_sessions(sess_dir)
            ids = [s["session_id"] for s in detected]
            assert "real-session" in ids
            assert "latest" not in ids
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_migrate_legacy_session(self, tmp_path):
        import json
        import os
        from agent_runtime_cockpit.cli_repl.session import migrate_legacy_session

        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "migrate_run")
        try:
            sess_dir = tmp_path / "migrate_run"
            sess_dir.mkdir(parents=True, exist_ok=True)
            legacy = {
                "session_id": "to-migrate",
                "mode": "plan",
                "messages": [
                    {"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00"},
                ],
                "created": "2026-01-01T00:00:00",
                "updated": "2026-01-01T00:00:01",
            }
            (sess_dir / "to-migrate.json").write_text(json.dumps(legacy), encoding="utf-8")

            migrated = migrate_legacy_session("to-migrate")
            assert migrated is not None
            assert migrated.id == "to-migrate"
            assert migrated.mode == "plan"
            assert len(migrated.history) == 1

            # Verify canonical format exists
            canonical_path = sess_dir / "to-migrate" / "session.json"
            assert canonical_path.exists()
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_migrate_all_legacy_sessions(self, tmp_path):
        import json
        import os
        from agent_runtime_cockpit.cli_repl.session import migrate_all_legacy_sessions

        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "migrate_all")
        try:
            sess_dir = tmp_path / "migrate_all"
            sess_dir.mkdir(parents=True, exist_ok=True)
            for i in range(2):
                legacy = {
                    "session_id": f"legacy-00{i}",
                    "mode": "build",
                    "messages": [{"role": "user", "content": f"msg-{i}"}],
                }
                (sess_dir / f"legacy-00{i}.json").write_text(json.dumps(legacy), encoding="utf-8")

            results = migrate_all_legacy_sessions()
            assert len(results) == 2
            for sid, success in results:
                assert success, f"Migration of {sid} failed"
            # Verify canonical
            assert (sess_dir / "legacy-000" / "session.json").exists()
            assert (sess_dir / "legacy-001" / "session.json").exists()
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_migrate_nonexistent_returns_none(self, tmp_path):
        import os
        from agent_runtime_cockpit.cli_repl.session import migrate_legacy_session

        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "migrate_none")
        try:
            result = migrate_legacy_session("does-not-exist")
            assert result is None
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)

    def test_list_legacy_session_ids(self, tmp_path):
        import json
        import os
        from agent_runtime_cockpit.cli_repl.session import _list_legacy_session_ids

        os.environ["ARC_STUDIO_SESSIONS_DIR"] = str(tmp_path / "migrate_ids")
        try:
            sess_dir = tmp_path / "migrate_ids"
            sess_dir.mkdir(parents=True, exist_ok=True)
            legacy = {"session_id": "id-001", "mode": "build", "messages": []}
            (sess_dir / "id-001.json").write_text(json.dumps(legacy), encoding="utf-8")

            ids = _list_legacy_session_ids(sess_dir)
            assert "id-001" in ids
        finally:
            os.environ.pop("ARC_STUDIO_SESSIONS_DIR", None)


class TestSessionsMigrate:
    def test_migrate_no_legacy(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "no_legacy"))
        result = CliRunner().invoke(app, ["studio", "sessions", "migrate", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["data"]["total_legacy"] == 0

    def test_migrate_with_legacy(self, monkeypatch, tmp_path):
        import json
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "with_legacy"))
        sess_dir = tmp_path / "with_legacy"
        sess_dir.mkdir(parents=True, exist_ok=True)
        legacy = {
            "session_id": "migrate-me",
            "mode": "build",
            "messages": [{"role": "user", "content": "hi"}],
            "created": "2026-01-01T00:00:00",
            "updated": "2026-01-01T00:00:00",
        }
        (sess_dir / "migrate-me.json").write_text(json.dumps(legacy), encoding="utf-8")

        result = CliRunner().invoke(app, ["studio", "sessions", "migrate", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["newly_migrated"] == 1
        assert "migrate-me" in payload["data"]["session_ids"]

    def test_migrate_twice_idempotent(self, monkeypatch, tmp_path):
        import json
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "idempotent"))
        sess_dir = tmp_path / "idempotent"
        sess_dir.mkdir(parents=True, exist_ok=True)
        legacy = {
            "session_id": "dup-test",
            "mode": "build",
            "messages": [],
        }
        (sess_dir / "dup-test.json").write_text(json.dumps(legacy), encoding="utf-8")

        # First migration
        result1 = CliRunner().invoke(app, ["studio", "sessions", "migrate", "--json"])
        assert result1.exit_code == 0

        # Second migration should report 0 new migrations
        result2 = CliRunner().invoke(app, ["studio", "sessions", "migrate", "--json"])
        assert result2.exit_code == 0
        payload2 = json.loads(result2.output)
        assert payload2["data"]["newly_migrated"] == 0

    def test_deprecated_sessions_migrate_alias_warns(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "alias"))
        result = CliRunner().invoke(app, ["studio", "sessions-migrate"])
        assert result.exit_code == 0, result.output
        assert "Deprecated" in result.output
        assert "arc studio sessions migrate" in result.output


class TestBareArc:
    def test_bare_arc_with_version_flag(self):
        result = CliRunner().invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ARC Studio" in result.stdout

    def test_bare_arc_shows_help_in_non_tty(self):
        """Without TTY, bare `arc` should show help text."""
        result = CliRunner().invoke(app, [])
        assert result.exit_code == 0
        # Should show available commands in help
        assert "version" in result.stdout or "Commands" in result.stdout

    def test_bare_arc_with_arc_no_tui_shows_help(self, monkeypatch):
        """ARC_NO_TUI=1 should show help even in TTY."""
        monkeypatch.setenv("ARC_NO_TUI", "1")
        result = CliRunner().invoke(app, [])
        assert result.exit_code == 0
        assert "Commands" in result.stdout or "ARC" in result.stdout

    def test_bare_arc_subcommand_still_works(self, monkeypatch, tmp_path):
        """Subcommands should still work normally."""
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sub_sessions"))
        result = CliRunner().invoke(app, ["studio", "sessions", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["ok"] is True


class TestStudioCli:
    def test_sessions_json(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        session = ChatSession()
        session.add_message("user", "hello")
        session.save()
        result = CliRunner().invoke(app, ["studio", "sessions", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["data"][0]["id"] == session.id
