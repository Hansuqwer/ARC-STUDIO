"""LangChain runner with live streaming support.

Phase 26 T3: Live streaming via BaseCallbackHandler.

Implements ARCCallbackHandler that subscribes to LangChain callbacks and
emits TypedRunEvent for integration with ARC's event system.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from ...protocol._bypass import PolicyBypassReason
from ...protocol.schemas import RunEvent, RunRecord, RunStatus
from ...security.enforcement import emit_policy_bypass_warning

log = logging.getLogger(__name__)


class ARCCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that emits ARC events.

    Phase 26 T3: Subscribes to LangChain callbacks and converts them to
    ARC's TypedRunEvent format for live streaming.
    """

    def __init__(
        self,
        run_id: str,
        emit_event: Callable[[str, str, dict], None],
        provider_registry: Optional[dict] = None,
    ):
        """Initialize callback handler.

        Args:
            run_id: Run identifier
            emit_event: Callback to emit events (run_id, event_type, data)
            provider_registry: Optional registry of known providers

        """
        super().__init__()
        self.run_id = run_id
        self.emit_event = emit_event
        self.provider_registry = provider_registry or {}
        self.sequence = 0
        self._chain_stack: list[str] = []

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

    # Chain callbacks
    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain starts running."""
        chain_name = serialized.get("name", "unknown_chain")
        self._chain_stack.append(chain_name)

        self._emit(
            "CHAIN_START",
            {
                "chain_name": chain_name,
                "inputs": inputs,
                "depth": len(self._chain_stack),
            },
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain finishes running."""
        chain_name = self._chain_stack.pop() if self._chain_stack else "unknown_chain"

        self._emit(
            "CHAIN_END",
            {
                "chain_name": chain_name,
                "outputs": outputs,
            },
        )

    def on_chain_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when a chain errors."""
        chain_name = self._chain_stack.pop() if self._chain_stack else "unknown_chain"

        self._emit(
            "CHAIN_ERROR",
            {
                "chain_name": chain_name,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

    # LLM callbacks
    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts generating."""
        llm_name = serialized.get("name", "unknown_llm")

        # Check if provider is known
        if llm_name not in self.provider_registry:
            # Emit policy bypass warning for unknown provider
            emit_policy_bypass_warning(
                run_id=self.run_id,
                sequence=self._next_sequence(),
                policy_id="provider_registry",
                bypass_reason=PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN,
                surface="llm_call",
                surface_identifier=llm_name,
                suggested_remediation=f"Register {llm_name} in ProviderClient registry or use a known provider",
                emit_event=self.emit_event,
            )

        self._emit(
            "LLM_START",
            {
                "llm_name": llm_name,
                "prompts": prompts,
                "prompt_count": len(prompts),
            },
        )

    def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any,
    ) -> None:
        """Called when LLM generates a new token."""
        self._emit(
            "LLM_TOKEN",
            {
                "token": token,
            },
        )

    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Called when LLM finishes generating."""
        self._emit(
            "LLM_END",
            {
                "generations": len(response.generations),
                "llm_output": response.llm_output,
            },
        )

    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when LLM errors."""
        self._emit(
            "LLM_ERROR",
            {
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

    # Tool callbacks
    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts running."""
        tool_name = serialized.get("name", "unknown_tool")

        self._emit(
            "TOOL_START",
            {
                "tool_name": tool_name,
                "input": input_str,
            },
        )

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes running."""
        self._emit(
            "TOOL_END",
            {
                "output": output,
            },
        )

    def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when a tool errors."""
        self._emit(
            "TOOL_ERROR",
            {
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )


class LangChainRunner:
    """Runner for executing LangChain chains with ARC event streaming.

    Phase 26 T3: Executes chains with ARCCallbackHandler for live event streaming.
    """

    def __init__(self, workspace: Path):
        """Initialize runner.

        Args:
            workspace: Workspace path

        """
        self.workspace = workspace
        self.events: list[RunEvent] = []

    def run(
        self,
        chain: Any,
        inputs: dict[str, Any],
        provider_registry: Optional[dict] = None,
    ) -> RunRecord:
        """Run a LangChain chain with event streaming.

        Args:
            chain: LangChain Runnable to execute
            inputs: Input dictionary for the chain
            provider_registry: Optional registry of known providers

        Returns:
            RunRecord with execution results and events

        """
        run_id = f"langchain-{uuid.uuid4().hex[:12]}"
        started = datetime.now(timezone.utc)

        # Create callback handler
        handler = ARCCallbackHandler(
            run_id=run_id,
            emit_event=self._emit_event,
            provider_registry=provider_registry,
        )

        # Emit run start event
        self._emit_event(
            run_id,
            "RUN_STARTED",
            {
                "sequence": 0,
                "timestamp": started.isoformat(),
                "runtime": "langchain",
            },
        )

        try:
            # Execute chain with callback
            result = chain.invoke(inputs, config={"callbacks": [handler]})

            # Emit run completed event
            ended = datetime.now(timezone.utc)
            self._emit_event(
                run_id,
                "RUN_COMPLETED",
                {
                    "sequence": handler._next_sequence(),
                    "timestamp": ended.isoformat(),
                    "result": result,
                },
            )

            return RunRecord(
                id=run_id,
                workflow_id="langchain_chain",
                runtime="langchain",
                status=RunStatus.COMPLETED,
                started_at=started.isoformat(),
                ended_at=ended.isoformat(),
                events=self.events,
                metadata={"result": result},
            )

        except Exception as e:
            # Emit run failed event
            ended = datetime.now(timezone.utc)
            self._emit_event(
                run_id,
                "RUN_FAILED",
                {
                    "sequence": handler._next_sequence(),
                    "timestamp": ended.isoformat(),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            return RunRecord(
                id=run_id,
                workflow_id="langchain_chain",
                runtime="langchain",
                status=RunStatus.FAILED,
                started_at=started.isoformat(),
                ended_at=ended.isoformat(),
                events=self.events,
                metadata={"error": str(e)},
            )

    def _emit_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event and store it.

        Args:
            run_id: Run identifier
            event_type: Type of event
            data: Event data

        """
        event = RunEvent(
            type=event_type,
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            run_id=run_id,
            sequence=data.get("sequence", 0),
            data=data,
        )
        self.events.append(event)
