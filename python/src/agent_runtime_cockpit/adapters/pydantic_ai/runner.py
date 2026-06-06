"""Pydantic AI runner with live streaming support.

Phase 29 PR 29.3: Live streaming via Pydantic AI run events.

Implements event handler that subscribes to Pydantic AI run events and
emits TypedRunEvent for integration with ARC's event system.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger(__name__)


class PydanticAIEventHandler:
    """Pydantic AI event handler that emits ARC events.

    Phase 29 PR 29.3: Subscribes to Pydantic AI run events and converts them
    to ARC's TypedRunEvent format for live streaming.
    """

    def __init__(
        self,
        run_id: str,
        emit_event: Callable[[str, str, dict], None],
    ):
        """Initialize event handler.

        Args:
            run_id: Run identifier
            emit_event: Callback to emit events (run_id, event_type, data)

        """
        self.run_id = run_id
        self.emit_event = emit_event
        self.sequence = 0

    def _next_sequence(self) -> int:
        """Get next sequence number."""
        seq = self.sequence
        self.sequence += 1
        return seq

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event with sequence number."""
        event_data = {
            "sequence": self._next_sequence(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.emit_event(self.run_id, event_type, event_data)

    def on_run_start(self, agent_name: str, input_data: dict[str, Any]) -> None:
        """Called when an agent run starts."""
        self._emit(
            "AGENT_RUN_START",
            {
                "agent_name": agent_name,
                "input": input_data,
            },
        )

    def on_run_end(self, agent_name: str, result: Any) -> None:
        """Called when an agent run completes successfully."""
        self._emit(
            "AGENT_RUN_END",
            {
                "agent_name": agent_name,
                "result": str(result),
                "status": "success",
            },
        )

    def on_run_error(self, agent_name: str, error: Exception) -> None:
        """Called when an agent run fails with an error."""
        self._emit(
            "AGENT_RUN_ERROR",
            {
                "agent_name": agent_name,
                "error": str(error),
                "error_type": type(error).__name__,
                "status": "error",
            },
        )

    def on_validation_error(self, agent_name: str, validation_error: dict[str, Any]) -> None:
        """Called when validation fails.

        Pydantic AI validation errors are surfaced as typed event variant.
        """
        self._emit(
            "VALIDATION_ERROR",
            {
                "agent_name": agent_name,
                "validation_error": validation_error,
                "error_type": "ValidationError",
            },
        )

    def on_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Called when a tool is invoked."""
        self._emit(
            "TOOL_CALL",
            {
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

    def on_tool_result(self, tool_name: str, result: Any) -> None:
        """Called when a tool returns a result."""
        self._emit(
            "TOOL_RESULT",
            {
                "tool_name": tool_name,
                "result": str(result),
            },
        )

    def on_model_request(self, model: str, messages: list[dict[str, Any]]) -> None:
        """Called when making a request to the model."""
        self._emit(
            "MODEL_REQUEST",
            {
                "model": model,
                "message_count": len(messages),
            },
        )

    def on_model_response(self, model: str, response: str) -> None:
        """Called when receiving a response from the model."""
        self._emit(
            "MODEL_RESPONSE",
            {
                "model": model,
                "response": response,
            },
        )


def run_agent_with_streaming(
    agent: Any,
    input_data: dict[str, Any],
    run_id: str,
    emit_event: Callable[[str, str, dict], None],
) -> Any:
    """Run a Pydantic AI agent with live event streaming.

    Not yet implemented. Will call ``agent.run_sync()`` / ``agent.run()``
    with ``PydanticAIEventHandler`` once the pydantic_ai SDK is vendored.
    Use ``pydantic_ai.models.test.TestModel`` for offline testing.

    Raises:
        NotImplementedError: Always — runner is not yet implemented.

    """
    raise NotImplementedError(
        "pydantic_ai runner is not yet implemented. "
        "Implement using agent.run_sync(prompt, deps=...) with TestModel for offline tests."
    )
