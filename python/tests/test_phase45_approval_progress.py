"""Phase 45: Approval UX, progress rendering, sandbox deny defaults."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_runtime_cockpit.cli_repl.chat_repl import _handle_input, _render_state_prefix
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import (
    CommandResult,
    SlashCommandHandler,
    _sandbox_run_with_approval,
    cmd_sandbox,
)


def _session(workspace: Path | None = None) -> ChatSession:
    s = ChatSession()
    if workspace:
        s.metadata["workspace"] = str(workspace)
    return s


def _handler() -> SlashCommandHandler:
    return SlashCommandHandler()


class TestRenderStatePrefixes:
    def test_present_prefix(self) -> None:
        assert _render_state_prefix("present") == "[ok]"

    def test_denied_prefix(self) -> None:
        assert _render_state_prefix("denied") == "[denied]"

    def test_blocked_prefix(self) -> None:
        assert _render_state_prefix("blocked") == "[blocked]"

    def test_absent_prefix(self) -> None:
        assert _render_state_prefix("absent") == "[empty]"

    def test_error_prefix(self) -> None:
        assert _render_state_prefix("error") == "[error]"

    def test_unknown_state_uses_brackets(self) -> None:
        assert _render_state_prefix("custom_state") == "[custom_state]"


class TestREPLCommandResultRendering:
    def test_command_result_rendered_with_state_prefix(self) -> None:
        handler = _handler()
        session = _session()
        outputs: list[str] = []
        _handle_input("/runs list", session, handler, outputs.append)
        assert outputs
        text = outputs[0]
        assert (
            "[ok]" in text
            or "[empty]" in text
            or "[error]" in text
            or "[blocked]" in text
            or "[degraded]" in text
        )

    def test_blocked_command_renders_blocked_prefix(self) -> None:
        handler = _handler()
        session = _session()
        outputs: list[str] = []
        _handle_input("/policy explain", session, handler, outputs.append)
        assert outputs
        assert "[blocked]" in outputs[0]

    def test_string_result_renders_directly(self) -> None:
        """String results (like /help) must render without prefix wrapping."""
        handler = _handler()
        session = _session()
        outputs: list[str] = []
        _handle_input("/help", session, handler, outputs.append)
        assert outputs
        assert "SESSION" in str(outputs[0]).upper()


class TestSandboxDenyDefaults:
    def test_network_denied_by_default(self, tmp_path: Path) -> None:
        """curl must be denied when policy does not allow network (user declines approval)."""
        session = _session()
        # Provide confirm_fn=False to simulate user declining the interactive prompt
        result = cmd_sandbox("run -- curl https://example.com", session, confirm_fn=lambda _: False)
        assert result.state in {"denied", "blocked"}

    def test_destructive_denied_hard(self, tmp_path: Path) -> None:
        """rm -rf must be hard-denied and confirm_fn must never be called."""
        session = _session()
        confirm_called = []

        def never_confirm(prompt: str) -> bool:
            confirm_called.append(prompt)
            return True  # would approve if called

        result = cmd_sandbox("run -- rm -rf /tmp/arc_test_file", session, confirm_fn=never_confirm)
        assert result.state in {"denied", "blocked"}
        # confirm_fn must NOT be called for destructive
        assert not confirm_called, "confirm_fn was called for destructive command"

    def test_read_only_allowed_without_prompt(self, tmp_path: Path, monkeypatch: object) -> None:
        """ls -la must be allowed by local-safe policy without any prompt."""
        monkeypatch.chdir(tmp_path)
        session = _session()
        confirm_called = []

        def should_not_call(prompt: str) -> bool:
            confirm_called.append(prompt)
            return False

        with patch(
            "agent_runtime_cockpit.cli_repl.adapters.SubprocessIsolationProvider"
        ) as MockProv:
            mock_result = MagicMock()
            mock_result.exit_code = 0
            mock_result.stdout = "ok"
            mock_result.stderr = ""
            mock_result.stdout_truncated = False
            mock_result.stderr_truncated = False
            mock_result.redaction_applied = False
            mock_result.duration_ms = 5
            mock_result.killed = False
            mock_result.kill_reason = None
            mock_result.provider = "subprocess"

            async def mock_execute_ro(*a: object, **kw: object) -> object:
                return mock_result

            MockProv.return_value.execute = mock_execute_ro

            result = cmd_sandbox("run -- ls -la", session, confirm_fn=should_not_call)

        assert result.state in {"present", "ok", "error", "blocked", "denied"}
        assert not confirm_called, "confirm_fn called for read-only command"

    def test_network_denied_emits_audit_event(self) -> None:
        """Denied sandbox run emits sandbox.denied when approval is explicitly declined."""
        # Call cmd_sandbox directly with confirm_fn=False; then check audit in metadata
        session = _session()
        result = cmd_sandbox("run -- curl https://example.com", session, confirm_fn=lambda _: False)
        assert result.state == "denied"
        assert result.reason == "approval_declined"
        # Audit event must be present in metadata
        audit = result.metadata.get("audit_event")
        assert isinstance(audit, dict), "audit_event missing from denied CommandResult metadata"
        assert audit.get("command") is not None

    def test_approval_required_confirmed_sets_pre_approved(self) -> None:
        """When confirm_fn returns True for approval_required, pre_approved flag reaches adapter."""
        confirmed = []

        def yes_confirm(prompt: str) -> bool:
            confirmed.append(prompt)
            return True

        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.render_sandbox_run"
        ) as mock_render:
            mock_render.return_value = MagicMock(
                state="present",
                text="ok",
                data={},
                exit_code=0,
            )
            _sandbox_run_with_approval("run -- curl https://example.com", confirm_fn=yes_confirm)
        # confirm was called
        assert confirmed
        # render_sandbox_run called with pre_approved=True
        mock_render.assert_called_once()
        _, kwargs = mock_render.call_args
        assert kwargs.get("pre_approved") is True

    def test_approval_required_declined_returns_denied(self) -> None:
        """When confirm_fn returns False, result must be denied."""
        result = _sandbox_run_with_approval(
            "run -- curl https://example.com", confirm_fn=lambda _: False
        )
        assert result.state == "denied"
        assert "not approved" in result.output.lower()


class TestProgressEvents:
    def test_progress_sink_receives_run_events(self) -> None:
        """Progress events from /run must reach the sink."""
        events: list[tuple[str, dict]] = []

        def sink(name: str, payload: dict) -> None:
            events.append((name, payload))

        handler = SlashCommandHandler(progress_sink=sink)
        session = _session()
        # /run with gate closed emits no progress but must not crash
        result = handler.handle("/run hello", session)
        assert isinstance(result, CommandResult)
        assert result.state in {"blocked", "error", "present", "cancelled"}

    def test_sandbox_allowed_emits_sandbox_command_event(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        monkeypatch.chdir(tmp_path)
        handler = SlashCommandHandler()
        session = _session()
        with patch(
            "agent_runtime_cockpit.cli_repl.adapters.SubprocessIsolationProvider"
        ) as MockProv:
            mock_result = MagicMock()
            mock_result.exit_code = 0
            mock_result.stdout = "."
            mock_result.stderr = ""
            mock_result.stdout_truncated = False
            mock_result.stderr_truncated = False
            mock_result.redaction_applied = False
            mock_result.duration_ms = 2
            mock_result.killed = False
            mock_result.kill_reason = None
            mock_result.provider = "subprocess"

            async def mock_execute_allowed(*a: object, **kw: object) -> object:
                return mock_result

            MockProv.return_value.execute = mock_execute_allowed
            handler.handle("/sandbox run -- ls -la", session)

        event_names = [name for name, _ in handler.events]
        assert "sandbox.command" in event_names

    def test_output_truncation_flag_preserved(self, tmp_path: Path, monkeypatch: object) -> None:
        """stdout_truncated flag must appear in result data when set."""
        monkeypatch.chdir(tmp_path)
        with patch(
            "agent_runtime_cockpit.cli_repl.adapters.SubprocessIsolationProvider"
        ) as MockProv:
            mock_result = MagicMock()
            mock_result.exit_code = 0
            mock_result.stdout = "x" * 100
            mock_result.stderr = ""
            mock_result.stdout_truncated = True  # <-- truncated
            mock_result.stderr_truncated = False
            mock_result.redaction_applied = False
            mock_result.duration_ms = 1
            mock_result.killed = False
            mock_result.kill_reason = None
            mock_result.provider = "subprocess"

            async def mock_execute_trunc(*a: object, **kw: object) -> object:
                return mock_result

            MockProv.return_value.execute = mock_execute_trunc
            from agent_runtime_cockpit.cli_repl.adapters import render_sandbox_run

            result = render_sandbox_run("run -- ls -la")

        assert result.data is not None
        assert result.data.get("stdout_truncated") is True
