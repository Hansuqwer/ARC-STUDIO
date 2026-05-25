"""DSPy runner with event streaming support.

Phase 30: Gated scaffold only.
Requires ARC_DSPY_RUNNER_ENABLED=1 to execute.
No live provider calls without explicit gate.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger(__name__)

DSPY_RUNNER_GATE_ENV = "ARC_DSPY_RUNNER_ENABLED"


def is_runner_enabled() -> bool:
    """Check if DSPy runner is enabled via environment gate."""
    return os.environ.get(DSPY_RUNNER_GATE_ENV, "").strip() == "1"


class DSPyEventHandler:
    """DSPy event handler that emits ARC events.

    Phase 30: Scaffold for DSPy lifecycle events.
    Emits DSPY_* typed events for integration with ARC's event system.
    """

    def __init__(
        self,
        run_id: str,
        emit_event: Callable[[str, str, dict], None],
    ):
        self.run_id = run_id
        self.emit_event = emit_event
        self.sequence = 0

    def _next_sequence(self) -> int:
        seq = self.sequence
        self.sequence += 1
        return seq

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        event_data = {
            "sequence": self._next_sequence(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.emit_event(self.run_id, event_type, event_data)

    def on_module_start(self, module_type: str, signature: str | None = None) -> None:
        self._emit(
            "DSPY_MODULE_START",
            {
                "module_type": module_type,
                "signature": signature,
            },
        )

    def on_module_end(self, module_type: str, result: Any = None, duration_ms: int = 0) -> None:
        self._emit(
            "DSPY_MODULE_END",
            {
                "module_type": module_type,
                "result": str(result) if result is not None else None,
                "duration_ms": duration_ms,
                "status": "success",
            },
        )

    def on_module_error(self, module_type: str, error: Exception) -> None:
        self._emit(
            "DSPY_MODULE_ERROR",
            {
                "module_type": module_type,
                "error": str(error),
                "error_type": type(error).__name__,
                "status": "error",
            },
        )

    def on_predict_start(self, signature: str, inputs: dict[str, Any]) -> None:
        self._emit(
            "DSPY_PREDICT_START",
            {
                "signature": signature,
                "input_keys": list(inputs.keys()),
            },
        )

    def on_predict_end(self, signature: str, prediction: Any) -> None:
        self._emit(
            "DSPY_PREDICT_END",
            {
                "signature": signature,
                "prediction": str(prediction),
            },
        )

    def on_compile_start(self, optimizer: str, trainset_size: int) -> None:
        self._emit(
            "DSPY_COMPILE_START",
            {
                "optimizer": optimizer,
                "trainset_size": trainset_size,
            },
        )

    def on_compile_end(self, optimizer: str, duration_ms: int) -> None:
        self._emit(
            "DSPY_COMPILE_END",
            {
                "optimizer": optimizer,
                "duration_ms": duration_ms,
            },
        )

    def on_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        self._emit(
            "DSPY_TOOL_CALL",
            {
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

    def on_tool_result(self, tool_name: str, result: Any) -> None:
        self._emit(
            "DSPY_TOOL_RESULT",
            {
                "tool_name": tool_name,
                "result": str(result),
            },
        )


def run_dspy_program(
    program: Any,
    inputs: dict[str, Any],
    run_id: str,
    emit_event: Callable[[str, str, dict], None],
) -> Any:
    """Run a DSPy program with event streaming.

    GATED: Requires ARC_DSPY_RUNNER_ENABLED=1.
    Without the gate, raises RuntimeError.

    Args:
        program: DSPy Module instance
        inputs: Input dictionary
        run_id: Run identifier
        emit_event: Callback to emit events

    Returns:
        Program result

    Raises:
        RuntimeError: If runner gate is not set
        Exception: If program execution fails

    """
    if not is_runner_enabled():
        raise RuntimeError(
            f"DSPy runner is gated. Set {DSPY_RUNNER_GATE_ENV}=1 to enable. "
            "This will execute DSPy programs which may make provider calls."
        )

    handler = DSPyEventHandler(run_id, emit_event)
    module_type = type(program).__name__

    try:
        handler.on_module_start(module_type)

        if hasattr(program, "forward"):
            result = program.forward(**inputs)
        elif callable(program):
            result = program(**inputs)
        else:
            raise TypeError(f"DSPy program {module_type} is not callable")

        handler.on_module_end(module_type, result)
        return result

    except Exception as e:
        handler.on_module_error(module_type, e)
        raise
