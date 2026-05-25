"""Smolagents runner with event streaming support.

Gated scaffold only. CodeAgent execution is high risk and must not run by default.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

SMOLAGENTS_RUNNER_GATE_ENV = "ARC_SMOLAGENTS_RUNNER_ENABLED"
SMOLAGENTS_LIVE_PROVIDER_GATE_ENV = "ARC_ALLOW_LIVE_PROVIDER_TESTS"
SMOLAGENTS_CODE_AGENT_CONFIRM_ENV = "RUN_SMOLAGENTS_CODE_AGENT"
SMOLAGENTS_CODE_AGENT_CONFIRM_VALUE = "I_UNDERSTAND_CODE_EXECUTION_RISK"
SMOLAGENTS_SANDBOX_ENV = "ARC_SMOLAGENTS_SANDBOX"


def is_runner_enabled() -> bool:
    """Check if Smolagents runner is enabled via environment gate."""
    return os.environ.get(SMOLAGENTS_RUNNER_GATE_ENV, "").strip() == "1"


def is_live_provider_enabled() -> bool:
    """Check if live provider calls are enabled via shared ARC gate."""
    return os.environ.get(SMOLAGENTS_LIVE_PROVIDER_GATE_ENV, "").strip().lower() == "true"


def is_code_agent_confirmed() -> bool:
    """Check explicit CodeAgent risk confirmation."""
    return (
        os.environ.get(SMOLAGENTS_CODE_AGENT_CONFIRM_ENV, "").strip()
        == SMOLAGENTS_CODE_AGENT_CONFIRM_VALUE
    )


def configured_sandbox() -> str | None:
    """Return configured Smolagents sandbox marker, if any."""
    sandbox = os.environ.get(SMOLAGENTS_SANDBOX_ENV, "").strip()
    return sandbox or None


class SmolagentsGateError(RuntimeError):
    """Raised when Smolagents execution is blocked by ARC gates."""


class SmolagentsEventHandler:
    """Smolagents event handler that emits ARC events."""

    def __init__(self, run_id: str, emit_event: Callable[[str, str, dict], None]):
        self.run_id = run_id
        self.emit_event = emit_event
        self.sequence = 0

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        event_data = {
            "sequence": self.sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.sequence += 1
        self.emit_event(self.run_id, event_type, event_data)

    def on_agent_start(self, agent_type: str, task: str) -> None:
        self._emit("SMOLAGENTS_AGENT_START", {"agent_type": agent_type, "task": task})

    def on_agent_end(self, agent_type: str, result: Any) -> None:
        self._emit(
            "SMOLAGENTS_AGENT_END",
            {"agent_type": agent_type, "result": str(result), "status": "success"},
        )

    def on_agent_error(self, agent_type: str, error: Exception) -> None:
        self._emit(
            "SMOLAGENTS_AGENT_ERROR",
            {"agent_type": agent_type, "error": str(error), "error_type": type(error).__name__},
        )

    def on_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        self._emit("SMOLAGENTS_TOOL_CALL", {"tool_name": tool_name, "arguments": arguments})

    def on_code_execution(self, sandbox: str | None = None) -> None:
        self._emit(
            "SMOLAGENTS_CODE_EXECUTION",
            {"sandbox": sandbox, "warning": "code execution path is gated"},
        )

    def on_gate_denied(self, agent_type: str, reason: str, gate: str) -> None:
        self._emit(
            "SMOLAGENTS_GATE_DENIED",
            {"agent_type": agent_type, "reason": reason, "gate": gate, "status": "denied"},
        )


def _raise_gate_denied(
    handler: SmolagentsEventHandler | None,
    agent_type: str,
    reason: str,
    gate: str,
) -> None:
    if handler is not None:
        handler.on_gate_denied(agent_type, reason, gate)
    raise SmolagentsGateError(reason)


def _enforce_gates(handler: SmolagentsEventHandler | None, agent_type: str) -> str | None:
    if not is_runner_enabled():
        _raise_gate_denied(
            handler,
            agent_type,
            f"Smolagents runner is gated. Set {SMOLAGENTS_RUNNER_GATE_ENV}=1 to enable.",
            SMOLAGENTS_RUNNER_GATE_ENV,
        )
    if not is_live_provider_enabled():
        _raise_gate_denied(
            handler,
            agent_type,
            "Live provider calls disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true to enable.",
            SMOLAGENTS_LIVE_PROVIDER_GATE_ENV,
        )
    if agent_type != "CodeAgent":
        return None
    sandbox = configured_sandbox()
    if sandbox is None:
        _raise_gate_denied(
            handler,
            agent_type,
            f"CodeAgent execution requires {SMOLAGENTS_SANDBOX_ENV}=docker|e2b|modal|microvm.",
            SMOLAGENTS_SANDBOX_ENV,
        )
    if not is_code_agent_confirmed():
        _raise_gate_denied(
            handler,
            agent_type,
            f"CodeAgent execution requires {SMOLAGENTS_CODE_AGENT_CONFIRM_ENV}={SMOLAGENTS_CODE_AGENT_CONFIRM_VALUE}.",
            SMOLAGENTS_CODE_AGENT_CONFIRM_ENV,
        )
    return sandbox


def run_smolagents_agent(
    agent: Any,
    task: str,
    run_id: str,
    emit_event: Callable[[str, str, dict], None],
) -> Any:
    """Run a Smolagents agent with event streaming.

    Requires ARC_SMOLAGENTS_RUNNER_ENABLED=1. This may execute generated code.
    """
    handler = SmolagentsEventHandler(run_id, emit_event)
    agent_type = type(agent).__name__
    sandbox = _enforce_gates(handler, agent_type)
    try:
        handler.on_agent_start(agent_type, task)
        if agent_type == "CodeAgent":
            handler.on_code_execution(sandbox or getattr(agent, "executor_type", None))
        if not hasattr(agent, "run"):
            raise TypeError("Smolagents agent has no run() method")
        result = agent.run(task)
        handler.on_agent_end(agent_type, result)
        return result
    except Exception as e:
        handler.on_agent_error(agent_type, e)
        raise
