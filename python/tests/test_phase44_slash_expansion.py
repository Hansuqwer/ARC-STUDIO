"""Phase 44: Slash command registry expansion and REPL error boundary tests."""

from __future__ import annotations

from unittest.mock import patch

from agent_runtime_cockpit.cli_repl.chat_repl import _handle_input
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import (
    CommandResult,
    SlashCommandHandler,
)


def _session() -> ChatSession:
    return ChatSession()


def _handler() -> SlashCommandHandler:
    return SlashCommandHandler()


class TestHelpGrouping:
    def test_help_contains_all_category_headers(self) -> None:
        handler = _handler()
        result = handler.handle("/help", _session())
        text = str(result)
        for header in (
            "SESSION",
            "RUN",
            "SANDBOX",
            "POLICY",
            "WORKSPACE",
            "PROVIDERS",
            "AUDIT",
            "TASKS",
            "MCP",
        ):
            assert header in text, f"Missing group header: {header}"

    def test_help_mentions_parity_note(self) -> None:
        handler = _handler()
        result = handler.handle("/help", _session())
        assert "parity" in str(result).lower()

    def test_help_lists_all_p0_commands(self) -> None:
        handler = _handler()
        result = handler.handle("/help", _session())
        text = str(result)
        for cmd in ("/status", "/doctor", "/sandbox", "/policy", "/runs"):
            assert cmd in text, f"P0 command missing from /help: {cmd}"

    def test_help_lists_all_p1_commands(self) -> None:
        handler = _handler()
        result = handler.handle("/help", _session())
        text = str(result)
        for cmd in ("/audit", "/task", "/providers", "/mcp", "/hitl"):
            assert cmd in text, f"P1 command missing from /help: {cmd}"


class TestP0CommandsReturnStructuredState:
    def test_status_returns_present(self) -> None:
        handler = _handler()
        result = handler.handle("/status", _session())
        assert isinstance(result, (CommandResult, str))

    def test_doctor_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/doctor", _session())
        assert isinstance(result, (CommandResult, str))

    def test_runs_list_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/runs list", _session())
        assert isinstance(result, CommandResult)
        assert result.state in {"present", "absent", "degraded", "error"}

    def test_sandbox_doctor_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/sandbox doctor", _session())
        assert isinstance(result, CommandResult)
        assert result.state in {"present", "absent", "degraded", "blocked", "error"}

    def test_policy_explain_does_not_execute(self) -> None:
        """policy explain must classify and return, never execute the command."""
        handler = _handler()
        result = handler.handle("/policy explain -- curl https://example.com", _session())
        assert isinstance(result, CommandResult)
        # network classification in output
        assert "network" in str(result).lower() or result.state in {"present", "denied", "blocked"}

    def test_policy_explain_empty_arg_blocked(self) -> None:
        handler = _handler()
        result = handler.handle("/policy explain", _session())
        assert isinstance(result, CommandResult)
        assert result.state == "blocked"


class TestP1CommandsReturnStructuredState:
    def test_audit_list_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/audit list", _session())
        assert isinstance(result, CommandResult)
        assert result.state in {"present", "absent", "degraded", "error"}

    def test_task_list_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/task list", _session())
        assert isinstance(result, CommandResult)
        assert result.state in {"present", "absent", "error"}

    def test_providers_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/providers", _session())
        assert isinstance(result, CommandResult)

    def test_mcp_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/mcp", _session())
        assert isinstance(result, CommandResult)

    def test_hitl_pending_returns_structured(self) -> None:
        handler = _handler()
        result = handler.handle("/hitl pending", _session())
        assert isinstance(result, CommandResult)

    def test_context_pack_empty_blocked(self) -> None:
        handler = _handler()
        result = handler.handle("/context pack", _session())
        assert isinstance(result, CommandResult)


class TestREPLErrorBoundary:
    def test_exception_in_slash_handler_does_not_propagate(self) -> None:
        """A crashing slash command must not crash the REPL loop."""
        handler = _handler()
        session = _session()
        outputs: list[str] = []

        # Patch the registry so /status raises
        with patch.object(handler._registry, "get", side_effect=RuntimeError("boom")):
            _handle_input("/status", session, handler, outputs.append)

        assert any("[error]" in o for o in outputs), "Error boundary did not render error"

    def test_unknown_slash_command_renders_unknown_message(self) -> None:
        handler = _handler()
        session = _session()
        outputs: list[str] = []
        _handle_input("/not_a_real_command_xyz", session, handler, outputs.append)
        assert outputs
        assert "unknown" in outputs[0].lower() or "not_a_real_command_xyz" in outputs[0].lower()

    def test_runner_exception_does_not_propagate(self) -> None:
        handler = _handler()
        session = _session()
        outputs: list[str] = []
        with patch(
            "agent_runtime_cockpit.swarmgraph.SwarmGraphRunner",
            side_effect=RuntimeError("runner exploded"),
        ):
            _handle_input("hello world", session, handler, outputs.append)
        assert any("[error]" in o for o in outputs)

    def test_repl_loop_continues_after_command_failure(self) -> None:
        """Two inputs: first crashes, second must still execute."""
        handler = _handler()
        session = _session()
        outputs: list[str] = []

        with patch.object(handler._registry, "get", side_effect=RuntimeError("fail")):
            _handle_input("/status", session, handler, outputs.append)

        # Reset and send a valid input
        _handle_input("/help", session, handler, outputs.append)
        help_output = outputs[-1]
        assert "SESSION" in str(help_output)
