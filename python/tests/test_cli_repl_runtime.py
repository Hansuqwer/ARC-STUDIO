"""Tests for runtime-agnostic shell workstreams: /runtime, /model, streaming, diff→apply."""

from __future__ import annotations

import builtins
from unittest.mock import patch


from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import SlashCommandHandler
from agent_runtime_cockpit.runtime.mode import RuntimeMode


# ── /runtime (engine selector) ──────────────────────────────────────────────


class TestRuntimeCommand:
    def test_list_shows_active_engine(self):
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/runtime", s)
        assert result is not None
        assert result.state == "present"
        assert "Active engine" in result.output
        assert "swarmgraph" in result.output  # default

    def test_list_shows_detected_can_run_paid(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/runtime list", s)
        assert result.state == "present"
        assert "detected" in result.output
        assert "can_run" in result.output

    def test_use_known_engine_sets_metadata(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/runtime use lmarena", s)
        assert result.state in ("present", "degraded")  # lmarena may or may not be runnable
        assert s.metadata.get("runtime_adapter") == "lmarena"

    def test_use_unknown_engine_blocked(self):
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/runtime use totally_unknown_engine_xyz", s)
        assert result.state == "blocked"
        assert "unknown" in result.output.lower() or "Unknown" in result.output

    def test_use_does_not_change_runtime_mode(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        h = SlashCommandHandler()
        s = ChatSession(runtime_mode=RuntimeMode.FAKE)
        h.handle("/runtime use lmarena", s)
        assert s.runtime_mode is RuntimeMode.FAKE  # execution mode unchanged

    def test_use_does_not_enable_paid_calls(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        h = SlashCommandHandler()
        s = ChatSession(allow_paid_calls=False)
        h.handle("/runtime use crewai", s)
        assert s.allow_paid_calls is False

    def test_use_missing_id_blocked(self):
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/runtime use", s)
        assert result.state == "blocked"


# ── _run_with_adapter dispatch ────────────────────────────────────────────────


class _StubRunner:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, prompt: str) -> dict:
        return {
            "status": "completed",
            "total_tasks": 1,
            "completed_tasks": 1,
            "total_cost_usd": 0.0,
            "results": [{"output": f"stub: {prompt}"}],
        }


class TestAdapterDispatch:
    def test_swarmgraph_engine_uses_swarmgraph_runner(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl import chat_repl
        from agent_runtime_cockpit.cli_repl.rendering import Renderer
        from rich.console import Console

        s = ChatSession()
        s.metadata["runtime_adapter"] = "swarmgraph"
        renderer = Renderer(Console(record=True, width=80), ascii_only=True)

        with patch("agent_runtime_cockpit.swarmgraph.SwarmGraphRunner", _StubRunner):
            reply = chat_repl._run_with_adapter("hello", s, renderer)
        assert "stub: hello" in reply

    def test_non_swarmgraph_engine_without_can_run_returns_degraded(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl import chat_repl
        from agent_runtime_cockpit.cli_repl.rendering import Renderer
        from rich.console import Console

        s = ChatSession()
        s.metadata["runtime_adapter"] = "llamaindex"  # can_run=False by default
        renderer = Renderer(Console(record=True, width=80), ascii_only=True)

        reply = chat_repl._run_with_adapter("hello", s, renderer)
        assert "degraded" in reply

    def test_swarmgraph_not_called_when_different_engine_selected(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl import chat_repl
        from agent_runtime_cockpit.cli_repl.rendering import Renderer
        from rich.console import Console

        s = ChatSession()
        s.metadata["runtime_adapter"] = "langgraph"  # not swarmgraph
        renderer = Renderer(Console(record=True, width=80), ascii_only=True)

        called = []

        def fail_runner(*a, **kw):
            called.append(True)
            raise AssertionError(
                "SwarmGraphRunner must NOT be used when a different engine is selected"
            )

        with patch("agent_runtime_cockpit.swarmgraph.SwarmGraphRunner", fail_runner):
            reply = chat_repl._run_with_adapter("hello", s, renderer)
        # LangGraph has can_run=False → degraded, and SwarmGraphRunner was never called
        assert not called
        assert "degraded" in reply


# ── /model (real switching, gated) ──────────────────────────────────────────


class TestModelCommand:
    def test_list_shows_providers(self):
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/model list", s)
        assert result.state == "present"
        assert "Provider" in result.output or "provider" in result.output.lower()

    def test_use_without_key_returns_degraded(self, monkeypatch):
        monkeypatch.delenv("NINEROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ARC_9ROUTER_API_KEY", raising=False)
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/model use 9router", s)
        assert result.state == "degraded"
        assert result.reason == "no_key"
        assert s.allow_paid_calls is False

    def test_use_with_key_switches_provider(self, monkeypatch):
        monkeypatch.setenv("NINEROUTER_API_KEY", "test-key")
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/model use 9router:some-model", s)
        assert result.state == "present"
        assert s.metadata.get("provider") == "9router"
        assert s.metadata.get("provider_model") == "some-model"

    def test_use_never_enables_paid_calls(self, monkeypatch):
        monkeypatch.setenv("NINEROUTER_API_KEY", "test-key")
        h = SlashCommandHandler()
        s = ChatSession(allow_paid_calls=False)
        h.handle("/model use 9router", s)
        assert s.allow_paid_calls is False

    def test_use_missing_spec_blocked(self):
        h = SlashCommandHandler()
        s = ChatSession()
        result = h.handle("/model use", s)
        assert result.state == "blocked"


# ── Live streaming (provider-backed, injectable stream_fn) ──────────────────


class TestProviderStreaming:
    def test_stream_fn_accumulates_tokens(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl import chat_repl
        from agent_runtime_cockpit.cli_repl.rendering import Renderer
        from rich.console import Console

        tokens = ["Hello", " world", "!"]

        def fake_stream(prompt: str):
            return iter(tokens)

        s = ChatSession(runtime_mode=RuntimeMode.PROVIDER_BACKED, allow_paid_calls=True)
        console = Console(record=True, width=80)
        renderer = Renderer(console, ascii_only=True)
        renderer.stream_fn = fake_stream

        reply = chat_repl._run_provider_streaming("hi", s, renderer)
        assert reply == "Hello world!"

    def test_fake_offline_does_not_stream(self, monkeypatch):
        """In fake/offline mode, _run_with_adapter uses SwarmGraphRunner, not streaming."""
        from agent_runtime_cockpit.cli_repl import chat_repl
        from agent_runtime_cockpit.cli_repl.rendering import Renderer
        from rich.console import Console

        s = ChatSession(runtime_mode=RuntimeMode.FAKE, allow_paid_calls=False)
        s.metadata["runtime_adapter"] = "swarmgraph"
        renderer = Renderer(Console(record=True, width=80), ascii_only=True)
        renderer.stream_fn = None  # no stream_fn

        with patch("agent_runtime_cockpit.swarmgraph.SwarmGraphRunner", _StubRunner):
            reply = chat_repl._run_with_adapter("test", s, renderer)
        # Deterministic offline response, not streaming output
        assert "stub: test" in reply


# ── Diff → approve → apply ──────────────────────────────────────────────────


class TestApplyDiff:
    def test_plan_mode_denied(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        # Stub trust so plan-mode check runs first (trust is gated after plan-mode check)
        h = SlashCommandHandler()
        s = ChatSession(mode="plan")
        result = h.handle("/apply-diff myfile.py", s)
        assert hasattr(result, "state"), f"Expected CommandResult, got {type(result)}: {result!r}"
        assert result.state == "denied"
        assert "plan mode" in result.output.lower() or result.reason == "plan_mode"

    def test_approve_calls_apply_path(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl import slash_commands
        from agent_runtime_cockpit.cli_repl.adapters import SlashAdapterResult

        approved_prompts: list[str] = []

        def approve(prompt: str) -> bool:
            approved_prompts.append(prompt)
            return True

        monkeypatch.setattr(
            slash_commands,
            "render_apply",
            lambda arg: SlashAdapterResult(state="present", text="applied"),
        )
        # Stub trust to trusted
        import agent_runtime_cockpit.security.trust as trust_mod

        monkeypatch.setattr(
            trust_mod,
            "resolve_trust",
            lambda ws: type("T", (), {"level": type("L", (), {"value": "trusted"})()})(),
        )

        h = SlashCommandHandler()
        h.confirm_fn = approve
        s = ChatSession(mode="build")
        result = h.handle("/apply-diff myfile.py some diff", s)
        assert result.state == "present"
        assert approved_prompts

    def test_decline_prevents_apply(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl import slash_commands
        from agent_runtime_cockpit.cli_repl.adapters import SlashAdapterResult

        apply_calls: list[str] = []
        monkeypatch.setattr(
            slash_commands,
            "render_apply",
            lambda arg: (
                apply_calls.append(arg) or SlashAdapterResult(state="present", text="applied")
            ),
        )

        import agent_runtime_cockpit.security.trust as trust_mod

        monkeypatch.setattr(
            trust_mod,
            "resolve_trust",
            lambda ws: type("T", (), {"level": type("L", (), {"value": "trusted"})()})(),
        )

        h = SlashCommandHandler()
        h.confirm_fn = lambda prompt: False
        s = ChatSession(mode="build")
        result = h.handle("/apply-diff myfile.py some diff", s)
        assert result.state == "denied"
        assert not apply_calls

    def test_non_interactive_no_confirm_fn_denied(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        import agent_runtime_cockpit.security.trust as trust_mod

        monkeypatch.setattr(
            trust_mod,
            "resolve_trust",
            lambda ws: type("T", (), {"level": type("L", (), {"value": "trusted"})()})(),
        )
        h = SlashCommandHandler()
        h.confirm_fn = None
        s = ChatSession(mode="build")
        result = h.handle("/apply-diff myfile.py diff", s)
        assert result.state in ("denied", "blocked")

    def test_diff_preview_shown_in_approval_prompt(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from agent_runtime_cockpit.cli_repl.adapters import SlashAdapterResult
        from agent_runtime_cockpit.cli_repl import slash_commands

        import agent_runtime_cockpit.security.trust as trust_mod

        monkeypatch.setattr(
            trust_mod,
            "resolve_trust",
            lambda ws: type("T", (), {"level": type("L", (), {"value": "trusted"})()})(),
        )
        monkeypatch.setattr(
            slash_commands,
            "render_apply",
            lambda arg: SlashAdapterResult(state="present", text="applied"),
        )

        prompts: list[str] = []
        h = SlashCommandHandler()
        h.confirm_fn = lambda p: prompts.append(p) or False
        s = ChatSession(mode="build")
        h.handle("/apply-diff myfile.py + new line", s)
        assert prompts
        assert "myfile.py" in prompts[0]


# ── ARC_TUI=1 stub ──────────────────────────────────────────────────────────


class TestTUIStub:
    def test_arc_tui_shows_blocker_message(self, monkeypatch, tmp_path, capsys):
        import builtins

        monkeypatch.setenv("ARC_TUI", "1")
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        import agent_runtime_cockpit.cli_repl.chat_repl as chat_repl

        monkeypatch.setattr(chat_repl, "HISTORY_FILE", tmp_path / "history.txt")
        monkeypatch.setattr(builtins, "input", lambda *_: (_ for _ in ()).throw(EOFError()))

        chat_repl.run_chat_repl()
        out = capsys.readouterr().out
        assert "ARC_TUI" in out or "full-screen" in out.lower() or "Falling back" in out


# ── Safe defaults preserved ─────────────────────────────────────────────────


class TestSafeDefaultsPreserved:
    def test_default_engine_is_swarmgraph(self):
        s = ChatSession()
        engine = (s.metadata or {}).get("runtime_adapter") or "swarmgraph"
        assert engine == "swarmgraph"

    def test_offline_default_no_paid_calls_after_runtime_use(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        h = SlashCommandHandler()
        s = ChatSession(allow_paid_calls=False)
        h.handle("/runtime use lmarena", s)
        h.handle(
            "/model use 9router", s
        )  # key not set → degraded, but allow_paid_calls still False
        assert s.allow_paid_calls is False

    def test_plain_repl_still_works(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ARC_PLAIN_REPL", "1")
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        import agent_runtime_cockpit.cli_repl.chat_repl as chat_repl

        monkeypatch.setattr(chat_repl, "HISTORY_FILE", tmp_path / "history.txt")
        monkeypatch.setattr(builtins, "input", lambda *_: (_ for _ in ()).throw(EOFError()))
        chat_repl.run_chat_repl()
        out = capsys.readouterr().out
        assert "ARC Studio v" in out
        assert "state: mode=build runtime=fake" in out
