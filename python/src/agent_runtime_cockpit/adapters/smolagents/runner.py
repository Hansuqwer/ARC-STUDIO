"""Smolagents runner with event streaming support.

Gated scaffold only. CodeAgent execution is high risk and must not run by default.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

SMOLAGENTS_RUNNER_GATE_ENV = "ARC_SMOLAGENTS_RUNNER_ENABLED"


def is_runner_enabled() -> bool:
    """Check if Smolagents runner is enabled via environment gate."""
    return os.environ.get(SMOLAGENTS_RUNNER_GATE_ENV, "").strip() == "1"


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


def run_smolagents_agent(
    agent: Any,
    task: str,
    run_id: str,
    emit_event: Callable[[str, str, dict], None],
) -> Any:
    """Run a Smolagents agent with event streaming.

    Requires ARC_SMOLAGENTS_RUNNER_ENABLED=1. This may execute generated code.
    """
    if not is_runner_enabled():
        raise RuntimeError(
            f"Smolagents runner is gated. Set {SMOLAGENTS_RUNNER_GATE_ENV}=1 to enable. "
            "This may execute generated code and make provider calls."
        )
    handler = SmolagentsEventHandler(run_id, emit_event)
    agent_type = type(agent).__name__
    try:
        handler.on_agent_start(agent_type, task)
        if agent_type == "CodeAgent":
            handler.on_code_execution(getattr(agent, "executor_type", None))
        if not hasattr(agent, "run"):
            raise TypeError("Smolagents agent has no run() method")
        result = agent.run(task)
        handler.on_agent_end(agent_type, result)
        return result
    except Exception as e:
        handler.on_agent_error(agent_type, e)
        raise
