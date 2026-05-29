from __future__ import annotations

import json
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, Optional
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import agent_runtime_cockpit.cli_repl.slash_commands as slash_commands
from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import SlashCommandHandler, _build_registry
from agent_runtime_cockpit.providers import ProviderResponse, UsageRecord


@dataclass
class _StubRunResult:
    text: str

    def render(self) -> str:
        return self.text

    def summary(self) -> dict[str, Any]:
        return {"chars": len(self.text)}


class _StubRunner:
    def __init__(
        self,
        *,
        config: Any = None,
        cancellation_token: Optional[CancellationToken] = None,
        mode: str = "instant",
    ) -> None:
        self.config = config
        self.cancellation_token = cancellation_token
        self.mode = mode

    def run(
        self,
        prompt: str,
        cancellation_token: Optional[CancellationToken] = None,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> _StubRunResult:
        token = cancellation_token or self.cancellation_token
        if self.mode == "instant":
            return _StubRunResult(text=f"ok: {prompt}")
        if self.mode == "progress":
            if on_progress is not None:
                on_progress({"stage": "plan"})
                on_progress({"stage": "execute"})
            return _StubRunResult(text=f"ok: {prompt}")
        if self.mode == "cancellable":
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if token is not None:
                    token.raise_if_cancelled()
                if on_progress is not None:
                    on_progress({"stage": "execute"})
                time.sleep(0.01)
            raise AssertionError("Cancellable runner ran to completion")
        raise AssertionError(f"Unknown stub runner mode: {self.mode}")


@dataclass
class _StubRunnerFactory:
    mode: str = "instant"
    instances: list[_StubRunner] = field(default_factory=list)

    def __call__(self, *args, **kwargs) -> _StubRunner:
        if args and "config" not in kwargs:
            kwargs["config"] = args[0]
        stub = _StubRunner(mode=self.mode, **kwargs)
        self.instances.append(stub)
        return stub


class _StubProviderClient:
    def __init__(self) -> None:
        self.complete_requests = []

    def capabilities(self):
        return slash_commands.AnthropicClient().capabilities()

    async def complete(self, request, *, cancellation_token):
        self.complete_requests.append(request)
        cancellation_token.raise_if_cancelled()
        return ProviderResponse(
            call_id="c1",
            model=request.model,
            content="provider ok",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=1, output_tokens=1),
        )

    async def stream(self, request, *, cancellation_token):
        return
        yield

    async def cancel(self, call_id: str) -> None:
        return None


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

    def test_save_rejects_invalid_session_ids(self):
        for session_id in (".", "latest", "bad id", "../x", ""):
            s = ChatSession(id=session_id)
            with pytest.raises(ValueError, match="unsafe session id"):
                s.save()

    def test_load_rejects_invalid_session_ids(self):
        for session_id in (".", "latest", "bad id", "../x", ""):
            assert ChatSession.load(session_id) is None


class TestSlashCommands:
    def test_help(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/help", s)
        assert result is not None
        assert "/help" in result
        assert "/sandbox" in result
        assert "/policy" in result
        # Groups now appear as uppercase headers in the palette
        result_lower = str(result).lower()
        for group in [
            "session",
            "run",
            "sandbox",
            "policy",
            "workspace",
            "providers",
            "audit",
            "tasks",
            "mcp",
        ]:
            assert group in result_lower, f"Group missing from /help output: {group}"
        assert "Recommended entrypoint: arch-studio-cli" in result
        assert "Workflow: /status" in result

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

    def test_repl_run_blocked_when_gate_closed(self, monkeypatch):
        monkeypatch.delenv("ARC_ALLOW_RUN", raising=False)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/run hello world", s)
        assert result is not None
        assert result.state == "blocked"
        assert result.reason == "gate_closed"

    def test_repl_run_succeeds_when_gate_open_via_env(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        factory = _StubRunnerFactory(mode="instant")
        handler = SlashCommandHandler()
        s = ChatSession()
        with patch("agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", factory):
            result = handler.handle("/run hello world", s)
        assert result is not None
        assert result.state == "present"
        assert "ok: hello world" in result.output
        assert any(
            name == "run.started" and payload["prompt_chars"] == 11
            for name, payload in handler.events
        )
        assert any(name == "run.completed" for name, _payload in handler.events)
        started = [payload for name, payload in handler.events if name == "run.started"][0]
        assert started["runtime_mode"] == "fake"

    def test_repl_run_progress_events_are_renderable(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        progress: list[tuple[str, dict[str, Any]]] = []
        factory = _StubRunnerFactory(mode="progress")
        handler = SlashCommandHandler(
            progress_sink=lambda name, payload: progress.append((name, payload))
        )
        s = ChatSession()
        with patch("agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", factory):
            result = handler.handle("/run hello progress", s)

        assert result is not None
        assert result.state == "present"
        assert result.metadata["progress_event_count"] == 2
        assert result.metadata["progress_stages"] == ["plan", "execute"]
        assert [name for name, _payload in progress] == [
            "run.started",
            "run.progress.plan",
            "run.progress.execute",
            "run.completed",
        ]

    def test_repl_run_succeeds_when_gate_open_via_session(self, monkeypatch):
        monkeypatch.delenv("ARC_ALLOW_RUN", raising=False)
        factory = _StubRunnerFactory(mode="instant")
        handler = SlashCommandHandler()
        s = SimpleNamespace(mode="build", allow_run=True, add_message=lambda *_args: None)
        with patch("agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", factory):
            result = handler.handle("/run hello", s)
        assert result is not None
        assert result.state == "present"

    @pytest.mark.skipif(os.name == "nt", reason="SIGINT unreliable on Windows")
    def test_repl_run_honors_cancellation_via_sigint(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        factory = _StubRunnerFactory(mode="cancellable")
        handler = SlashCommandHandler()
        s = ChatSession()

        def _send_sigint_soon():
            time.sleep(0.05)
            os.kill(os.getpid(), signal.SIGINT)

        sender = threading.Thread(target=_send_sigint_soon)
        sender.start()
        try:
            with patch("agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", factory):
                result = handler.handle("/run loop", s)
        finally:
            sender.join(timeout=2.0)

        assert result is not None
        assert result.state == "degraded"
        assert result.reason == "cancelled"
        assert result.metadata["progress_event_count"] >= 1
        assert "execute" in result.metadata["progress_stages"]
        cancelled = [payload for name, payload in handler.events if name == "run.cancelled"]
        assert len(cancelled) == 1
        assert cancelled[0]["reason"] == "user"

    def test_repl_run_and_registry_run_share_contract(self, monkeypatch, make_repl_context):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        factory = _StubRunnerFactory(mode="instant")
        handler = SlashCommandHandler()
        s = ChatSession()
        ctx = make_repl_context()
        ctx.session.allow_run = True
        registry = _build_registry()
        run_entry = registry.get("/run")

        with patch("agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", factory):
            repl_result = handler.handle("/run shared prompt", s)
            registry_result = run_entry.handler(["shared", "prompt"], ctx)

        assert repl_result.state == registry_result.state == "present"
        assert [name for name, _payload in handler.events if name.startswith("run.")] == [
            "run.started",
            "run.completed",
        ]
        assert [event.name for event in ctx.events if event.name.startswith("run.")] == [
            "run.started",
            "run.completed",
        ]

    def test_run_blocked_in_plan_mode(self):
        handler = SlashCommandHandler()
        s = ChatSession(mode="plan")
        result = handler.handle("/run hello world", s)
        assert result is not None
        assert "Blocked" in result

    def test_runtime_command_shows_current_runtime(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/runtime", s)
        assert result is not None
        assert "Runtime: fake" in result

    def test_tools_list_shows_builtin_tools(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/tools list", s)
        assert result is not None
        assert "Tools enabled: False" in result
        assert "read_file (enabled, read, trust=untrusted)" in result
        assert "list_directory (enabled, read, trust=untrusted)" in result
        assert "get_current_time (enabled, read, trust=trusted)" in result
        assert "bash (enabled, shell, trust=untrusted)" in result

    def test_tools_enable_all(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/tools enable", s)
        assert result == "Tools enabled."
        assert s.tools_enabled is True
        assert s.available_tools is None

    def test_tools_enable_allowlist(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/tools enable get_current_time", s)
        assert result == "Tools enabled."
        assert s.tools_enabled is True
        assert s.available_tools == ["get_current_time"]

    def test_tools_enable_unknown_blocks(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/tools enable unknown_tool", s)
        assert result == "Blocked: unknown tools: unknown_tool"
        assert s.tools_enabled is False

    def test_tools_disable_all(self):
        handler = SlashCommandHandler()
        s = ChatSession(tools_enabled=True)
        result = handler.handle("/tools disable", s)
        assert result == "Tools disabled."
        assert s.tools_enabled is False

    def test_mode_alias_sets_runtime_mode(self):
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/mode gated", s)
        assert result == "Runtime mode: gated_local"
        assert s.runtime_mode == "gated_local"

    def test_provider_backed_run_requires_paid_calls(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        handler = SlashCommandHandler()
        s = ChatSession(runtime_mode="provider_backed", allow_paid_calls=False)
        result = handler.handle("/run hello", s)
        assert result is not None
        assert result.state == "blocked"
        assert result.reason == "paid_calls_disabled"

    def test_provider_backed_run_invokes_budget_preflight(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        calls: list[dict[str, Any]] = []

        def fake_preflight(*args: Any, **kwargs: Any) -> None:
            calls.append(kwargs)

        monkeypatch.setattr(slash_commands, "preflight_with_estimator", fake_preflight)
        provider = _StubProviderClient()
        handler = SlashCommandHandler(runner=provider)
        s = ChatSession(runtime_mode="provider_backed", allow_paid_calls=True)
        result = handler.handle("/run hello", s)
        assert result is not None
        assert result.state == "present"
        assert result.output == "provider ok"
        assert calls
        assert calls[0]["provider_id"] == "anthropic"
        assert calls[0]["request_messages"] == [{"role": "user", "content": "hello"}]
        assert provider.complete_requests
        assert s.metadata["last_context"]["source"] == "provider_usage"
        assert s.metadata["last_context"]["used_tokens"] == 1

    def test_provider_backed_run_uses_turn_manager_not_swarmgraph(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        monkeypatch.setattr(
            slash_commands, "preflight_with_estimator", lambda *args, **kwargs: None
        )

        def fail_runner(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("SwarmGraphRunner should not execute provider-backed /run")

        monkeypatch.setattr(slash_commands, "SwarmGraphRunner", fail_runner)
        provider = _StubProviderClient()
        handler = SlashCommandHandler(runner=provider)
        s = ChatSession(runtime_mode="provider_backed", allow_paid_calls=True)
        result = handler.handle("/run hello", s)
        assert result is not None
        assert result.state == "present"
        assert provider.complete_requests

    def test_provider_backed_run_passes_tool_registry_when_tools_enabled(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        monkeypatch.setattr(
            slash_commands, "preflight_with_estimator", lambda *args, **kwargs: None
        )
        seen: dict[str, Any] = {}
        original = slash_commands.TurnManager

        class RecordingTurnManager(original):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                seen["tool_registry"] = kwargs.get("tool_registry")
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(slash_commands, "TurnManager", RecordingTurnManager)
        handler = SlashCommandHandler(runner=_StubProviderClient())
        s = ChatSession(runtime_mode="provider_backed", allow_paid_calls=True, tools_enabled=True)
        result = handler.handle("/run hello", s)
        assert result is not None
        assert result.state == "present"
        assert seen["tool_registry"] is not None

    @pytest.mark.asyncio
    async def test_provider_backed_run_works_in_async_context(self, monkeypatch):
        """Verify provider-backed /run works when called from async context (event loop running)."""
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        monkeypatch.setattr(
            slash_commands, "preflight_with_estimator", lambda *args, **kwargs: None
        )
        provider = _StubProviderClient()
        handler = SlashCommandHandler(runner=provider)
        s = ChatSession(runtime_mode="provider_backed", allow_paid_calls=True)

        # Call from within async context (event loop is running)
        # The _run_coro_sync wrapper should detect this and use thread pool
        result = handler.handle("/run hello", s)

        assert result is not None
        assert result.state == "present"
        assert result.output == "provider ok"
        assert provider.complete_requests

    def test_fake_run_skips_budget_preflight(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")

        def fail_preflight(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("provider preflight should not run for fake mode")

        monkeypatch.setattr(slash_commands, "preflight_with_estimator", fail_preflight)
        monkeypatch.setattr(slash_commands, "SwarmGraphRunner", _StubRunner)
        handler = SlashCommandHandler()
        s = ChatSession(runtime_mode="fake", allow_paid_calls=False)
        result = handler.handle("/run hello", s)
        assert result is not None
        assert result.state == "present"

    def test_provider_backed_budget_failure_blocks_runner(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")

        def fail_runner(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("runner should not execute after budget block")

        monkeypatch.setattr(slash_commands, "SwarmGraphRunner", fail_runner)
        handler = SlashCommandHandler()
        s = ChatSession(
            runtime_mode="provider_backed",
            allow_paid_calls=True,
            metadata={
                "provider_budget": {
                    "first_launch_confirmed": True,
                    "caps": [{"scope": "session", "amount_usd": "0.00000001"}],
                }
            },
        )
        result = handler.handle("/run " + ("hello " * 200), s)
        assert result is not None
        assert result.state == "blocked"
        assert result.reason == "budget_preflight_failed"

    def test_run_accepts_pre_cancelled_token(self, monkeypatch):
        monkeypatch.setenv("ARC_ALLOW_RUN", "1")
        token = CancellationToken()
        token.cancel(reason=CancellationReason.USER, detail="pre-cancelled")
        handler = SlashCommandHandler()
        handler.cancellation_token = token
        s = ChatSession()
        result = handler.handle("/run hello world", s)
        assert result is not None
        assert result.state == "degraded"
        assert result.reason == "cancelled"

    def test_run_no_arg(self):
        os.environ["ARC_ALLOW_RUN"] = "1"
        handler = SlashCommandHandler()
        s = ChatSession()
        try:
            result = handler.handle("/run", s)
            assert result.reason == "missing_prompt"
            assert "Usage" in result.remediation
        finally:
            os.environ.pop("ARC_ALLOW_RUN", None)

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
            "results": [{"task_id": "t1", "output": "done", "status": "completed"}],
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
        assert "Trust:" in result
        assert "BUILD" in result
        assert "Provider: none" in result
        assert "Sandbox: subprocess (microvm preflight-only)" in result
        assert "Context: unknown" in result

    def test_startup_banner_and_prompt_show_state(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.chat_repl import _format_prompt, _format_startup_banner

        s = ChatSession(tools_enabled=True, metadata={"provider": "anthropic"})
        banner = "\n".join(_format_startup_banner(s, workspace=tmp_path))
        assert "ARC Studio v" in banner
        assert "workspace:" in banner
        assert "provider=anthropic" in banner
        assert "sandbox=subprocess" in banner
        assert "/agent <task>" in banner

        prompt = _format_prompt(s)
        assert prompt.startswith("arc[")
        assert "build|fake|anthropic|tools:on|ctx:?" in prompt

    def test_prompt_and_status_show_real_context_metadata(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.chat_repl import _format_prompt
        from agent_runtime_cockpit.cli_repl.adapters import render_status

        s = ChatSession(
            metadata={
                "last_context": {
                    "available": True,
                    "used_tokens": 100,
                    "max_context_tokens": 1000,
                    "usage_pct": 10.0,
                    "source": "provider_usage",
                }
            }
        )
        assert "ctx:10.0%" in _format_prompt(s)
        status = render_status(s, tmp_path)
        assert "Context: 10.0% (100/1000 tokens, source=provider_usage)" in status.text

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

    def test_sandbox_doctor_reports_providers(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/sandbox doctor", s)
        assert result is not None
        assert result.state == "present"
        assert "Sandbox providers" in result.output
        assert "subprocess" in result.output
        assert "microvm" in result.output

    def test_sandbox_run_read_only_allowed_and_audited(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/sandbox run -- pwd", s)
        assert result is not None
        assert result.state == "present"
        assert "Classification: read_only" in result.output
        assert result.metadata["decision"]["allowed"] is True
        assert result.metadata["audit_event"]["type"] == "SANDBOX_COMMAND"
        assert any(name == "sandbox.command" for name, _payload in handler.events)

    def test_sandbox_run_network_denied_and_audited(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/sandbox run -- curl https://example.com", s)
        assert result is not None
        assert result.state == "denied"
        assert "Classification: network" in result.output
        assert result.metadata["decision"]["allowed"] is False
        assert result.metadata["audit_event"]["type"] == "SANDBOX_DENIED"
        assert any(name == "sandbox.denied" for name, _payload in handler.events)

    def test_sandbox_run_destructive_denied(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/sandbox run -- rm -rf .", s)
        assert result is not None
        assert result.state == "denied"
        assert result.metadata["classification"] == "destructive"

    def test_sandbox_run_microvm_blocked(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/sandbox run --provider microvm -- pwd", s)
        assert result is not None
        assert result.state == "blocked"
        assert "microVM execution not yet available" in result.output

    def test_policy_explain_read_only_allowed(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/policy explain -- ls -la", s)
        assert result is not None
        assert result.state == "present"
        assert "Classification: read_only" in result.output
        assert "Decision: allow" in result.output

    def test_policy_explain_network_denied(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        result = handler.handle("/policy explain -- curl https://example.com", s)
        assert result is not None
        assert result.state == "denied"
        assert "Classification: network" in result.output
        assert "Decision: deny" in result.output

    def test_policy_list_and_show(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        policy_list = handler.handle("/policy list", s)
        policy_show = handler.handle("/policy show local-safe", s)
        assert policy_list is not None
        assert policy_show is not None
        assert "local-safe" in policy_list.output
        assert "Allow network: no" in policy_show.output

    def test_runs_show_and_status(self, monkeypatch, tmp_path):
        traces = tmp_path / ".arc" / "traces"
        traces.mkdir(parents=True)
        (traces / "run-1.jsonl").write_text(
            '{"type":"RUN_STARTED"}\n{"type":"RUN_COMPLETED"}\n', encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        s = ChatSession()
        shown = handler.handle("/runs show run-1", s)
        status = handler.handle("/runs status run-1", s)
        assert shown is not None
        assert status is not None
        assert shown.state == "present"
        assert "Events: 2" in shown.output
        assert "Status: RUN_COMPLETED" in status.output

    def test_read_workspace_file(self, monkeypatch, tmp_path):
        (tmp_path / "hello.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        result = handler.handle("/read --offset 2 --limit 1 hello.txt", ChatSession())
        assert result is not None
        assert result.state == "present"
        assert result.output == "2: two"
        assert result.metadata["lines_returned"] == 1

    def test_read_missing_file_is_absent(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        result = handler.handle("/read missing.txt", ChatSession())
        assert result is not None
        assert result.state == "absent"

    def test_read_path_escape_blocked(self, monkeypatch, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.chdir(workspace)
        handler = SlashCommandHandler()
        result = handler.handle("/read ../outside.txt", ChatSession())
        assert result is not None
        assert result.state == "blocked"
        assert "escapes workspace" in result.output

    def test_read_symlink_escape_blocked(self, monkeypatch, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "link.txt").symlink_to(outside)
        monkeypatch.chdir(workspace)
        handler = SlashCommandHandler()
        result = handler.handle("/read link.txt", ChatSession())
        assert result is not None
        assert result.state == "blocked"

    def test_read_binary_file_blocked(self, monkeypatch, tmp_path):
        (tmp_path / "data.bin").write_bytes(b"abc\x00def")
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        result = handler.handle("/read data.bin", ChatSession())
        assert result is not None
        assert result.state == "blocked"
        assert "binary" in result.output

    def test_search_workspace_text(self, monkeypatch, tmp_path):
        (tmp_path / "a.txt").write_text("hello\nbye\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("print('hello')\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        result = handler.handle('/search hello --include "*.py"', ChatSession())
        assert result is not None
        assert result.state == "present"
        assert "b.py:1" in result.output
        assert "a.txt" not in result.output
        assert result.metadata["matches"][0]["path"] == "b.py"

    def test_search_path_scope_and_absent(self, monkeypatch, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "a.txt").write_text("needle\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("needle\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        result = handler.handle("/search needle --path subdir", ChatSession())
        assert result is not None
        assert result.state == "present"
        assert "subdir/a.txt:1" in result.output
        assert "b.txt" not in result.output
        no_match = handler.handle("/search absent --path subdir", ChatSession())
        assert no_match is not None
        assert no_match.state == "absent"

    def test_search_path_escape_blocked(self, monkeypatch, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.chdir(workspace)
        handler = SlashCommandHandler()
        result = handler.handle("/search secret --path ../outside", ChatSession())
        assert result is not None
        assert result.state == "blocked"

    def test_search_caps_matches(self, monkeypatch, tmp_path):
        (tmp_path / "many.txt").write_text("\n".join("hit" for _ in range(80)), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        result = handler.handle("/search hit", ChatSession())
        assert result is not None
        assert result.state == "degraded"
        assert result.metadata["truncated"] is True
        assert len(result.metadata["matches"]) == 50

    def test_help_includes_read_and_search(self):
        handler = SlashCommandHandler()
        result = handler.handle("/help", ChatSession())
        assert result is not None
        assert "/read" in result
        assert "/search" in result

    def test_slash_command_exception_boundary(self, monkeypatch):
        handler = SlashCommandHandler()
        s = ChatSession()

        def boom(_arg, _session):
            raise RuntimeError("boom")

        monkeypatch.setattr(slash_commands, "cmd_status", boom)
        handler._registry.get("status").handler = boom
        result = handler.handle("/status", s)
        assert result is not None
        assert result.state == "error"
        assert "boom" in result.output
        assert result.metadata["command"] == "status"
        assert result.metadata["error_type"] == "RuntimeError"

    def test_chat_repl_formats_progress_events(self):
        from agent_runtime_cockpit.cli_repl.chat_repl import _format_progress_event

        assert _format_progress_event("run.started", {}) == "[progress] run started"
        assert (
            _format_progress_event("run.progress.execute", {"stage": "execute"})
            == "[progress] execute"
        )
        assert (
            _format_progress_event("run.completed", {"elapsed_ms": 7})
            == "[progress] run completed in 7ms"
        )
        assert (
            _format_progress_event("run.cancelled", {"reason": "user"})
            == "[progress] run cancelled: user"
        )
        assert (
            _format_progress_event("turn.started", {"prompt_chars": 5})
            == "[agent] turn started (5 chars)"
        )
        assert (
            _format_progress_event(
                "tool.requested", {"tool": "bash", "args_preview": "{'command': 'ls'}"}
            )
            == "[tool] bash args={'command': 'ls'}"
        )
        rendered = _format_progress_event(
            "tool.executed",
            {
                "tool": "edit_file",
                "trust": "untrusted",
                "summary": "edited a.txt",
                "diff": "--- a\n+++ b",
            },
        )
        assert "[tool] edit_file ok trust=untrusted" in rendered
        assert "[diff]" in rendered
        assert "--- a" in rendered
        assert (
            _format_progress_event(
                "tool.result.blocked", {"tool": "bash", "reason": "network denied"}
            )
            == "[blocked] tool bash: network denied"
        )

    def test_sandbox_approval_prompt_is_actionable(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        prompts: list[str] = []

        def deny(prompt: str) -> bool:
            prompts.append(prompt)
            return False

        result = slash_commands._sandbox_run_with_approval(
            "run -- curl https://example.com", confirm_fn=deny
        )
        assert result.state == "denied"
        assert prompts
        assert "Sandbox approval required" in prompts[0]
        assert "Policy: local-safe" in prompts[0]
        assert "Default: deny" in prompts[0]

    def test_handler_streams_real_agent_tool_events_to_progress_sink(self):
        progress: list[tuple[str, dict[str, Any]]] = []
        handler = SlashCommandHandler(
            progress_sink=lambda name, payload: progress.append((name, payload))
        )
        handler.emit_event(
            "tool.requested", {"tool": "read_file", "args_preview": "{'path': 'a.txt'}"}
        )
        handler.emit_event("tool.executed", {"tool": "read_file", "summary": "read a.txt"})
        handler.emit_event("tool.result.blocked", {"tool": "bash", "reason": "network denied"})
        assert [name for name, _payload in progress] == [
            "tool.requested",
            "tool.executed",
            "tool.result.blocked",
        ]


class TestCommandRegistry:
    def test_register_and_lookup(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandDef, CommandRegistry

        registry = CommandRegistry()
        cmd = CommandDef(
            name="test", help_text="A test", category="meta", handler=lambda a, s: "ok"
        )
        registry.register(cmd)
        assert registry.has("test")
        assert registry.get("test") is cmd

    def test_alias_resolution(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandDef, CommandRegistry

        registry = CommandRegistry()
        cmd = CommandDef(
            name="exit",
            help_text="Exit",
            category="meta",
            handler=lambda a, s: "__EXIT__",
            aliases=["quit"],
        )
        registry.register(cmd)
        assert registry.get("quit") is cmd
        assert registry.get("/quit") is cmd
        assert registry.get("EXIT") is cmd

    def test_duplicate_detection(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandDef, CommandRegistry

        registry = CommandRegistry()
        cmd = CommandDef(name="dup", help_text="First", category="meta", handler=lambda a, s: "1")
        registry.register(cmd)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(cmd)

    def test_duplicate_alias_detection(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandDef, CommandRegistry

        registry = CommandRegistry()
        registry.register(
            CommandDef(
                name="first",
                help_text="First",
                category="meta",
                handler=lambda a, s: "1",
                aliases=["shared"],
            )
        )
        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                CommandDef(
                    name="second",
                    help_text="Second",
                    category="meta",
                    handler=lambda a, s: "2",
                    aliases=["shared"],
                )
            )

    def test_list_by_category(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandDef, CommandRegistry

        registry = CommandRegistry()
        registry.register(
            CommandDef(name="help", help_text="Help", category="meta", handler=lambda a, s: "h")
        )
        registry.register(
            CommandDef(name="run", help_text="Run", category="runtime", handler=lambda a, s: "r")
        )
        registry.register(
            CommandDef(
                name="status", help_text="Status", category="workspace", handler=lambda a, s: "s"
            )
        )

        meta_cmds = registry.list_commands("meta")
        assert len(meta_cmds) == 1
        assert meta_cmds[0].name == "help"

        all_cmds = registry.list_commands()
        assert len(all_cmds) == 3

    def test_categories(self):
        from agent_runtime_cockpit.cli_repl.commands import CommandDef, CommandRegistry

        registry = CommandRegistry()
        registry.register(
            CommandDef(name="a", help_text="A", category="meta", handler=lambda a, s: "a")
        )
        registry.register(
            CommandDef(name="b", help_text="B", category="runtime", handler=lambda a, s: "b")
        )
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


class TestPhase41P1Adapters:
    """Tests for Phase 41 P1 slash-command adapters: audit, task, providers, mcp."""

    def test_audit_list_empty(self, monkeypatch, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_audit_list

        monkeypatch.setenv("ARC_STUDIO_AUDIT_DIR", str(tmp_path / ".arc" / "audit"))
        result = render_audit_list(workspace=tmp_path)
        assert result.state == "absent"
        assert "No audit events" in result.text

    def test_audit_list_with_events(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_audit_list

        events_path = tmp_path / ".arc" / "audit" / "sandbox.events.jsonl"
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(
            '{"command":["ls","-la"],"classification":"read_only","allowed":true,"event_id":"evt-001"}\n'
            '{"command":["curl","http://x"],"classification":"network","allowed":false,"event_id":"evt-002"}\n',
            encoding="utf-8",
        )
        result = render_audit_list(
            workspace=tmp_path,
            limit=10,
        )
        assert result.state == "present"
        assert "evt-001" in result.text
        assert "evt-002" in result.text
        assert result.data["count"] == 2

    def test_audit_verify_ok(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_audit_verify

        events_path = tmp_path / "sandbox.events.jsonl"
        chain_path = tmp_path / "sandbox.audit.jsonl"
        events_path.write_text(
            '{"command":["ls","-la"],"classification":"read_only","allowed":true}\n',
            encoding="utf-8",
        )
        chain_path.write_text(
            '{"cmd":"ls -la","ok":true}\n',
            encoding="utf-8",
        )
        result = render_audit_verify("test-run", workspace=tmp_path)
        assert result.state in {"present", "denied"}

    def test_audit_verify_missing(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_audit_verify

        result = render_audit_verify("missing-run", workspace=tmp_path)
        assert result.state == "denied"

    def test_task_list_empty(self, monkeypatch, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_task_list

        monkeypatch.setenv("ARC_STUDIO_TASKS_DB", str(tmp_path / "tasks.db"))
        result = render_task_list(workspace=tmp_path)
        assert result.state in {"absent", "degraded"}

    def test_task_status_not_found(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_task_status

        result = render_task_status("nonexistent-id", workspace=tmp_path)
        assert result.state == "absent"

    def test_providers_status(self):
        from agent_runtime_cockpit.cli_repl.adapters import render_providers_status

        result = render_providers_status()
        assert result.state == "present"
        assert "Provider statuses:" in result.text

    def test_providers_summary(self):
        from agent_runtime_cockpit.cli_repl.adapters import render_providers_summary

        result = render_providers_summary()
        assert result.state == "present"
        assert "Provider accounts:" in result.text

    def test_providers_list_empty(self):
        from agent_runtime_cockpit.cli_repl.adapters import render_providers_list

        result = render_providers_list()
        assert result.state == "absent"
        assert "No provider accounts" in result.text

    def test_providers_add_and_remove(self, tmp_path):
        import os
        from unittest.mock import patch

        from agent_runtime_cockpit.cli_repl.adapters import (
            render_providers_add,
            render_providers_list,
            render_providers_remove,
        )

        # Use a temp config path
        config_dir = tmp_path / ".arc"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "providers.json"

        UNIQUE_ENV = "TEST_UNIQUE_KEY_12345"

        with patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config_file)}):
            result = render_providers_add("openai", UNIQUE_ENV, "test-openai")
            assert result.state == "present"
            assert "Provider account added" in result.text

            result = render_providers_list()
            assert result.state == "present"
            assert "openai" in result.text

            account_id = result.data.get("accounts", [{}])[0].get("id", "")
            result = render_providers_remove(account_id)
            assert result.state == "present"
            assert "removed" in result.text

    def test_providers_test(self, tmp_path):
        import os
        from unittest.mock import patch

        from agent_runtime_cockpit.cli_repl.adapters import (
            render_providers_add,
            render_providers_test,
        )

        config_dir = tmp_path / ".arc"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "providers.json"
        UNIQUE_ENV = "TEST_UNIQUE_PROVIDER_KEY_98765"

        with patch.dict(os.environ, {"ARC_PROVIDER_CONFIG": str(config_file)}):
            result = render_providers_add("openai", UNIQUE_ENV, "test")
            assert result.state == "present"
            account_id = result.data.get("id", "")

            # Test without env var - should show degraded
            result = render_providers_test(account_id)
            assert result.state == "degraded"
            assert "not set" in result.text

            # Test with env var - should show configured
            with patch.dict(os.environ, {UNIQUE_ENV: "sk-test"}):
                result = render_providers_test(account_id)
                assert result.state == "present"
                assert "configured" in result.text

    def test_mcp_status(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_mcp_status

        result = render_mcp_status(workspace=tmp_path)
        assert result.state in {"present", "degraded"}
        assert "MCP status:" in result.text

    def test_slash_audit_command(self):
        handler = SlashCommandHandler()
        result = handler.handle("/audit list", ChatSession())
        assert result is not None
        assert "Audit" in str(result) or "audit" in str(result).lower()

    def test_slash_task_list_command(self):
        handler = SlashCommandHandler()
        result = handler.handle("/task list", ChatSession())
        assert result is not None

    def test_slash_providers_status_command(self):
        handler = SlashCommandHandler()
        result = handler.handle("/providers", ChatSession())
        assert result is not None

    def test_slash_mcp_status_command(self):
        handler = SlashCommandHandler()
        result = handler.handle("/mcp", ChatSession())
        assert result is not None

    def test_help_includes_audit(self):
        handler = SlashCommandHandler()
        result = handler.handle("/help", ChatSession())
        assert "audit" in str(result).lower()

    def test_help_includes_tasks(self):
        handler = SlashCommandHandler()
        result = handler.handle("/help", ChatSession())
        assert "task" in str(result).lower()

    def test_help_includes_providers(self):
        handler = SlashCommandHandler()
        result = handler.handle("/help", ChatSession())
        assert "provider" in str(result).lower()

    def test_help_includes_mcp(self):
        handler = SlashCommandHandler()
        result = handler.handle("/help", ChatSession())
        assert "mcp" in str(result).lower()


class TestPhase41RemainingAdapters:
    def test_hitl_pending_empty(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_hitl_pending

        result = render_hitl_pending(workspace=tmp_path)
        assert result.state == "absent"
        assert "No pending HITL" in result.text

    def test_context_pack_missing_task_blocked(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_context_pack

        result = render_context_pack("", workspace=tmp_path)
        assert result.state == "blocked"

    def test_workspace_trust_status(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_workspace_trust_status

        result = render_workspace_trust_status(workspace=tmp_path)
        assert result.state in {"present", "degraded"}
        assert "Trust:" in result.text

    def test_config_show_and_validate(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import (
            render_config_show,
            render_config_validate,
        )

        show = render_config_show(workspace=tmp_path)
        validate = render_config_validate(workspace=tmp_path)
        assert show.state == "present"
        assert validate.state == "present"

    def test_replay_missing_run_degrades(self, tmp_path):
        from agent_runtime_cockpit.cli_repl.adapters import render_replay

        result = render_replay("missing-run", workspace=tmp_path)
        assert result.state in {"present", "degraded"}

    def test_battle_list_empty(self, monkeypatch, tmp_path):
        from agent_runtime_cockpit.cli_repl import adapters

        result = adapters.render_battle_list(workspace=tmp_path)
        assert result.state == "absent"

    def test_events_watch_empty(self):
        from agent_runtime_cockpit.cli_repl.adapters import render_events_watch
        from agent_runtime_cockpit.events.bus import reset_bus

        reset_bus()
        result = render_events_watch()
        assert result.state == "absent"
        assert "Live watch" in result.text

    def test_slash_remaining_commands_route(self):
        handler = SlashCommandHandler()
        session = ChatSession()
        commands = [
            "/hitl pending",
            "/context pack",
            "/workspace trust-status",
            "/config validate",
            "/replay missing-run",
            "/battle list",
            "/events watch",
        ]
        for command in commands:
            result = handler.handle(command, session)
            assert result is not None, command


class TestPhase416Sessions:
    def test_sessions_resume_loads_saved_session(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions_resume"))
        saved = ChatSession(id="resume-me", mode="plan")
        saved.add_message("user", "remember this")
        saved.save()
        current = ChatSession(id="current")

        result = SlashCommandHandler().handle("/sessions resume resume-me", current)

        assert "Resumed session resume-me" in str(result)
        assert current.id == "resume-me"
        assert current.mode == "plan"
        assert current.history[0]["content"] == "remember this"

    def test_sessions_resume_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions_missing"))
        current = ChatSession(id="current")

        result = SlashCommandHandler().handle("/sessions resume missing", current)

        assert "Session not found" in str(result)
        assert current.id == "current"

    def test_sessions_search_saved_messages(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions_search"))
        saved = ChatSession(id="search-me")
        saved.add_message("user", "needle phrase")
        saved.save()

        result = SlashCommandHandler().handle("/sessions search needle", ChatSession())

        assert "Session matches" in str(result)
        assert "search-me" in str(result)

    def test_history_search_active_session(self):
        session = ChatSession()
        session.add_message("user", "find this local message")

        result = SlashCommandHandler().handle("/history search local", session)

        assert "History matches" in str(result)
        assert "find this local message" in str(result)

    def test_history_search_no_match(self):
        session = ChatSession()
        session.add_message("user", "unrelated")

        result = SlashCommandHandler().handle("/history search absent", session)

        assert "No matching history" in str(result)


class TestPhase42InteractiveFoundations:
    def test_pipeline_and_runs_second_segment(self):
        handler = SlashCommandHandler()
        session = ChatSession()

        result = handler.handle("/version && /history", session)

        assert "ARC Studio" in str(result)
        assert "No messages" in str(result)

    def test_pipeline_and_short_circuits_on_failure(self):
        handler = SlashCommandHandler()
        session = ChatSession()

        result = handler.handle("/unknown && /version", session)

        assert "Unknown slash command" in str(result)
        assert "Skipped after &&" in str(result)

    def test_pipeline_or_runs_after_failure(self):
        handler = SlashCommandHandler()
        session = ChatSession()

        result = handler.handle("/unknown || /version", session)

        assert "Unknown slash command" in str(result)
        assert "ARC Studio" in str(result)

    def test_pipeline_pipe_forwards_text(self):
        handler = SlashCommandHandler()
        session = ChatSession()

        result = handler.handle("hello | /history search hello", session)

        assert "hello" in str(result)

    def test_pipeline_parse_error(self):
        result = SlashCommandHandler().handle("/version &&", ChatSession())

        assert "Pipeline parse error" in str(result)

    def test_pipeline_does_not_shell_execute(self, tmp_path):
        marker = tmp_path / "marker"
        result = SlashCommandHandler().handle(f"plain > {marker}", ChatSession())

        assert result is None
        assert not marker.exists()

    def test_dashboard_slash_command(self):
        result = SlashCommandHandler().handle("/dashboard", ChatSession())

        assert "ARC Dashboard" in str(result)
        assert "sandbox" in str(result)

    def test_dashboard_cli_command(self):
        result = CliRunner().invoke(app, ["dashboard"])

        assert result.exit_code == 0, result.output
        assert "ARC Dashboard" in result.output

    def test_alias_lifecycle_and_visible_expansion(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_ALIASES_FILE", str(tmp_path / "aliases.json"))
        handler = SlashCommandHandler()
        session = ChatSession()

        set_result = handler.handle("/alias set v /version", session)
        run_result = handler.handle("/alias run v", session)

        assert "Alias set" in str(set_result)
        assert "Alias expansion: v -> /version" in str(run_result)
        assert "ARC Studio" in str(run_result)

    def test_alias_workspace_precedence(self, monkeypatch, tmp_path):
        from agent_runtime_cockpit.cli_repl.aliases import get_alias, set_alias

        monkeypatch.setenv("ARC_STUDIO_ALIASES_FILE", str(tmp_path / "user-aliases.json"))
        set_alias("demo", "/version", scope="user", workspace=tmp_path)
        set_alias("demo", "/history", scope="workspace", workspace=tmp_path)

        record = get_alias("demo", workspace=tmp_path)

        assert record is not None
        assert record.scope == "workspace"
        assert record.command == "/history"

    def test_alias_recursion_guard(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_ALIASES_FILE", str(tmp_path / "aliases.json"))
        handler = SlashCommandHandler()
        session = ChatSession()
        handler.handle("/alias set loop /alias run loop", session)

        result = handler.handle("/alias run loop", session)

        assert "alias expansion depth exceeded" in str(result)

    def test_alias_expanded_sandbox_still_policy_gated(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARC_STUDIO_ALIASES_FILE", str(tmp_path / "aliases.json"))
        handler = SlashCommandHandler()
        session = ChatSession()
        handler.handle("/alias set danger /sandbox run -- rm -rf .", session)

        result = handler.handle("/alias run danger", session)

        assert "Alias expansion" in str(result)
        assert "Sandbox denied" in str(result)
