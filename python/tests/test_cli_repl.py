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
