"""Tests for the Rich-based interactive ARC shell (rendering + REPL wiring).

Rendering is captured deterministically via ``Console(record=True)`` +
``export_text()`` at a fixed width with the ASCII box fallback, so assertions
target stable text structure rather than colors/escape codes.
"""

from __future__ import annotations

import builtins

import pytest
from rich.console import Console

import agent_runtime_cockpit.cli_repl.chat_repl as chat_repl
from agent_runtime_cockpit.cli_repl.rendering import Renderer
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import CommandResult, SlashCommandHandler
from agent_runtime_cockpit.runtime.mode import RuntimeMode


def make_renderer(width: int = 100) -> Renderer:
    return Renderer(Console(record=True, width=width), ascii_only=True)


class _StubRunner:
    """Deterministic offline runner — no provider/network call."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def run(self, prompt: str) -> dict:
        return {
            "status": "completed",
            "total_tasks": 1,
            "completed_tasks": 1,
            "total_cost_usd": 0.0,
            "results": [{"output": f"Fake deterministic response for: {prompt}"}],
        }


# ── startup panel (1-6) ─────────────────────────────────────────────────────
class TestStartupPanel:
    def _render(self, session, workspace):
        r = make_renderer()
        r.print(r.startup_panel(session, workspace))
        return r.console.export_text()

    def test_contains_arc_studio_title(self, tmp_path):  # 1
        assert "ARC Studio" in self._render(ChatSession(), tmp_path)

    def test_includes_workspace_path(self, tmp_path):  # 2
        # Render wide so a long tmp path fits on one line for a clean substring check.
        r = Renderer(Console(record=True, width=200), ascii_only=True)
        r.print(r.startup_panel(ChatSession(), tmp_path))
        assert str(tmp_path) in r.console.export_text()

    def test_includes_trust_state(self, tmp_path):  # 3
        out = self._render(ChatSession(), tmp_path)
        assert "trust" in out
        # default untrusted workspace must be visibly labeled
        assert "untrusted" in out

    def test_includes_runtime_mode(self, tmp_path):  # 4
        out = self._render(ChatSession(), tmp_path)
        assert "runtime" in out
        assert "fake/offline" in out

    def test_includes_provider_and_model(self, tmp_path):  # 5
        out = self._render(ChatSession(), tmp_path)
        assert "provider" in out and "none" in out
        assert "model" in out and "unknown" in out

    def test_includes_sandbox_state(self, tmp_path):  # 6
        out = self._render(ChatSession(), tmp_path)
        assert "sandbox" in out and "subprocess" in out

    def test_provider_backed_not_enabled_by_default(self, tmp_path):
        # No fake provider/model status; offline/fake default holds.
        session = ChatSession()
        assert session.runtime_mode is RuntimeMode.FAKE
        assert session.allow_paid_calls is False
        rows = dict(make_renderer()._state_rows(session, tmp_path))
        assert rows["runtime"] == "fake/offline"
        assert rows["provider"] == "none"
        assert rows["model"] == "unknown"


# ── message blocks (7-9) ────────────────────────────────────────────────────
class TestMessageBlocks:
    def test_user_block_distinct(self):  # 7
        r = make_renderer()
        r.print(r.user_block("hello"))
        out = r.console.export_text()
        assert "User" in out and "hello" in out

    def test_assistant_block_distinct(self):  # 8
        r = make_renderer()
        r.print(r.assistant_block("Fake deterministic response for: hello"))
        out = r.console.export_text()
        assert "Assistant" in out and "Fake deterministic response" in out

    def test_tool_block_distinct(self):  # 9a
        r = make_renderer()
        r.print(r.tool_block("read_file", summary="read a.txt"))
        out = r.console.export_text()
        assert "Tool: read_file" in out and "read a.txt" in out

    def test_progress_line_distinct(self):  # 9b
        r = make_renderer()
        r.print(r.progress_line("tool.executed", {"tool": "bash", "trust": "untrusted"}))
        out = r.console.export_text()
        assert "[tool] bash" in out


# ── result states (10-12) ───────────────────────────────────────────────────
class TestResultStates:
    def test_denied_styling(self):  # 10
        r = make_renderer()
        r.print(r.result_block(CommandResult(state="denied", output="Sandbox denied: rm -rf .")))
        out = r.console.export_text()
        assert "denied" in out and "rm -rf ." in out

    def test_degraded_styling(self):  # 11
        r = make_renderer()
        r.print(r.result_block(CommandResult(state="degraded", reason="cancelled")))
        out = r.console.export_text()
        assert "degraded" in out

    def test_error_styling(self):  # 12
        r = make_renderer()
        r.print(r.result_block(CommandResult(state="error", output="boom")))
        out = r.console.export_text()
        assert "error" in out and "boom" in out

    def test_present_is_plain_text(self):
        r = make_renderer()
        r.print(r.result_block(CommandResult(state="present", output="all good")))
        assert "all good" in r.console.export_text()


# ── slash command framing (13-14) ───────────────────────────────────────────
class TestCommandFraming:
    def test_help_is_grouped(self):  # 13
        r = make_renderer()
        s = ChatSession()
        result = SlashCommandHandler().handle("/help", s)
        r.print(r.command_result("/help", result))
        out = r.console.export_text().lower()
        assert "help" in out
        for group in ["session", "run", "sandbox", "providers"]:
            assert group in out

    def test_status_panel_includes_core_state(self):  # 14
        r = make_renderer()
        s = ChatSession()
        result = SlashCommandHandler().handle("/status", s)
        r.print(r.command_result("/status", result))
        out = r.console.export_text()
        assert "Status" in out
        assert "Trust" in out and "Sandbox" in out and "Provider" in out

    def test_model_renders_degraded_panel(self):
        r = make_renderer()
        s = ChatSession()
        result = SlashCommandHandler().handle("/model", s)
        r.print(r.command_result("/model", result))
        out = r.console.export_text()
        assert "Model" in out
        # /model list now shows provider catalog with "Configured" column
        assert "Provider" in out or "provider" in out.lower()

    def test_session_renders_panel(self):
        r = make_renderer()
        s = ChatSession()
        result = SlashCommandHandler().handle("/session", s)
        r.print(r.command_result("/session", result))
        out = r.console.export_text()
        assert "Session" in out and s.id in out


# ── REPL lifecycle (15-18) ──────────────────────────────────────────────────
class TestReplLifecycle:
    def test_plain_mode_preserves_legacy_startup(self, monkeypatch, tmp_path, capsys):  # 15
        monkeypatch.setenv("ARC_PLAIN_REPL", "1")
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        monkeypatch.setattr(chat_repl, "HISTORY_FILE", tmp_path / "history.txt")

        def _eof(_prompt=""):
            raise EOFError

        monkeypatch.setattr(builtins, "input", _eof)
        chat_repl.run_chat_repl()
        out = capsys.readouterr().out
        assert "ARC Studio v" in out
        # plain-only banner marker (the rich shell never prints this line)
        assert "state: mode=build runtime=fake" in out
        assert "Session saved:" in out

    def test_ctrl_c_saves_session_cleanly(self, monkeypatch, tmp_path, capsys):  # 16
        sessions = tmp_path / "sessions"
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(sessions))
        monkeypatch.setattr(chat_repl, "HISTORY_FILE", tmp_path / "history.txt")

        def _interrupt(_prompt=""):
            raise KeyboardInterrupt

        monkeypatch.setattr(builtins, "input", _interrupt)
        # default (rich) path; must not raise
        chat_repl.run_chat_repl()
        out = capsys.readouterr().out
        assert "ARC Studio" in out  # rich startup panel rendered
        assert "Session saved:" in out
        saved = list(sessions.glob("s-*/session.json"))
        assert saved, "session was not persisted on Ctrl+C"

    def test_non_interactive_initial_prompt(self, monkeypatch, tmp_path, capsys):  # 17
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        monkeypatch.setattr(chat_repl, "HISTORY_FILE", tmp_path / "history.txt")
        result = chat_repl.run_chat_repl(initial_prompt="/help", non_interactive=True)
        out = capsys.readouterr().out
        assert result is None
        assert "slash command palette" in out

    def test_offline_default_no_provider_call(self, monkeypatch):  # 18
        monkeypatch.setattr(
            "agent_runtime_cockpit.swarmgraph.SwarmGraphRunner", _StubRunner, raising=False
        )
        r = make_renderer()
        handler = SlashCommandHandler()
        session = ChatSession()
        chat_repl._handle_input_rich("hello", session, handler, r)
        # offline/fake stays the default after a turn
        assert session.runtime_mode is RuntimeMode.FAKE
        assert session.allow_paid_calls is False
        assert session.history[-1]["role"] == "assistant"
        assert "Assistant" in r.console.export_text()


# ── approval UX (acceptance: not silent) ────────────────────────────────────
class TestApproval:
    def test_approval_panel_defaults_deny(self, monkeypatch):
        r = make_renderer()
        monkeypatch.setattr(builtins, "input", lambda *_a, **_k: "n")
        approved = r.confirm_approval(
            "Sandbox approval required\nCommand: curl https://example.com"
        )
        out = r.console.export_text()
        assert approved is False
        assert "Approval Required" in out
        assert "curl https://example.com" in out

    def test_approval_panel_accepts_yes(self, monkeypatch):
        r = make_renderer()
        monkeypatch.setattr(builtins, "input", lambda *_a, **_k: "y")
        assert r.confirm_approval("approve me") is True

    def test_handler_confirm_fn_routed_to_sandbox(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        prompts: list[str] = []
        handler = SlashCommandHandler()
        handler.confirm_fn = lambda prompt: prompts.append(prompt) or False
        result = handler.handle("/sandbox run -- curl https://example.com", ChatSession())
        assert result.state == "denied"
        assert prompts and "Sandbox approval required" in prompts[0]


# ── golden + robustness (19-20) ─────────────────────────────────────────────
class TestGoldenAndRobustness:
    def test_startup_plus_turn_structure(self, tmp_path):  # 19
        r = make_renderer(width=80)
        session = ChatSession()
        r.print(r.startup_panel(session, tmp_path))
        r.print(r.user_block("hello"))
        r.print(r.assistant_block("[SwarmGraph] Run completed - 1/1 tasks, $0.0000"))
        out = r.console.export_text()
        # deterministic ordered structure: title -> User -> Assistant
        i_title = out.find("ARC Studio")
        i_user = out.find("User")
        i_assistant = out.find("Assistant")
        assert -1 < i_title < i_user < i_assistant
        assert "$0.0000" in out

    def test_narrow_terminal_does_not_break(self, tmp_path):  # 20
        r = make_renderer(width=20)
        r.print(r.startup_panel(ChatSession(), tmp_path))
        r.print(r.user_block("hello world this is a long line"))
        out = r.console.export_text()
        assert "ARC Studio" in out  # still renders, just wrapped

    def test_no_secret_values_in_startup(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-should-not-print")
        r = make_renderer()
        r.print(r.startup_panel(ChatSession(), tmp_path))
        assert "sk-secret-should-not-print" not in r.console.export_text()


@pytest.mark.parametrize("use_ascii", [True, False])
def test_renderer_box_modes_render(tmp_path, use_ascii):
    r = Renderer(Console(record=True, width=80), ascii_only=use_ascii)
    r.print(r.startup_panel(ChatSession(), tmp_path))
    assert "ARC Studio" in r.console.export_text()
