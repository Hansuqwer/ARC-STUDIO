"""Haystack runner with event streaming support.

Phase 31: Gated scaffold only.
Requires ARC_HAYSTACK_RUNNER_ENABLED=1 to execute.
No live provider calls without explicit gate.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger(__name__)

HAYSTACK_RUNNER_GATE_ENV = "ARC_HAYSTACK_RUNNER_ENABLED"


def is_runner_enabled() -> bool:
    """Check if Haystack runner is enabled via environment gate."""
    return os.environ.get(HAYSTACK_RUNNER_GATE_ENV, "").strip() == "1"


class HaystackEventHandler:
    """Haystack event handler that emits ARC events.

    Phase 31: Scaffold for Haystack pipeline lifecycle events.
    Emits HAYSTACK_* typed events for integration with ARC's event system.
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

    def on_pipeline_start(
        self, pipeline_name: str, component_count: int, inputs: dict[str, Any]
    ) -> None:
        self._emit(
            "HAYSTACK_PIPELINE_START",
            {
                "pipeline_name": pipeline_name,
                "component_count": component_count,
                "input_keys": list(inputs.keys()),
            },
        )

    def on_pipeline_end(self, pipeline_name: str, result: Any = None, duration_ms: int = 0) -> None:
        self._emit(
            "HAYSTACK_PIPELINE_END",
            {
                "pipeline_name": pipeline_name,
                "result_keys": list(result.keys()) if isinstance(result, dict) else None,
                "duration_ms": duration_ms,
                "status": "success",
            },
        )

    def on_pipeline_error(self, pipeline_name: str, error: Exception) -> None:
        self._emit(
            "HAYSTACK_PIPELINE_ERROR",
            {
                "pipeline_name": pipeline_name,
                "error": str(error),
                "error_type": type(error).__name__,
                "status": "error",
            },
        )

    def on_component_start(self, component_name: str, component_type: str) -> None:
        self._emit(
            "HAYSTACK_COMPONENT_START",
            {
                "component_name": component_name,
                "component_type": component_type,
            },
        )

    def on_component_end(
        self, component_name: str, component_type: str, duration_ms: int = 0
    ) -> None:
        self._emit(
            "HAYSTACK_COMPONENT_END",
            {
                "component_name": component_name,
                "component_type": component_type,
                "duration_ms": duration_ms,
            },
        )

    def on_component_error(
        self, component_name: str, component_type: str, error: Exception
    ) -> None:
        self._emit(
            "HAYSTACK_COMPONENT_ERROR",
            {
                "component_name": component_name,
                "component_type": component_type,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )


def run_haystack_pipeline(
    pipeline: Any,
    inputs: dict[str, Any],
    run_id: str,
    emit_event: Callable[[str, str, dict], None],
    pipeline_name: str = "haystack_pipeline",
) -> Any:
    """Run a Haystack pipeline with event streaming.

    GATED: Requires ARC_HAYSTACK_RUNNER_ENABLED=1.
    Without the gate, raises RuntimeError.

    Args:
        pipeline: Haystack Pipeline instance
        inputs: Input dictionary for pipeline.run()
        run_id: Run identifier
        emit_event: Callback to emit events
        pipeline_name: Optional pipeline name for events

    Returns:
        Pipeline run result

    Raises:
        RuntimeError: If runner gate is not set
        Exception: If pipeline execution fails

    """
    if not is_runner_enabled():
        raise RuntimeError(
            f"Haystack runner is gated. Set {HAYSTACK_RUNNER_GATE_ENV}=1 to enable. "
            "This will execute Haystack pipelines which may make provider calls."
        )

    handler = HaystackEventHandler(run_id, emit_event)

    try:
        component_count = 0
        if hasattr(pipeline, "walk"):
            try:
                component_count = len(list(pipeline.walk()))
            except (TypeError, AttributeError):
                pass
        if component_count == 0 and hasattr(pipeline, "_components"):
            try:
                component_count = len(pipeline._components)
            except (TypeError, AttributeError):
                pass

        handler.on_pipeline_start(pipeline_name, component_count, inputs)

        if hasattr(pipeline, "run"):
            result = pipeline.run(inputs)
        elif callable(pipeline):
            result = pipeline(inputs)
        else:
            raise TypeError("Haystack pipeline is not callable or has no run() method")

        handler.on_pipeline_end(pipeline_name, result)
        return result

    except Exception as e:
        handler.on_pipeline_error(pipeline_name, e)
        raise
