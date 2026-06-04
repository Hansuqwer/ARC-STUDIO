"""Audit session context manager — typed HMAC audit for adapter run lifecycles.

Usage in any adapter::

    async with AuditSession(run_id="run_abc") as session:
        session.log_run_started(runtime="swarmgraph", mode=RuntimeMode.gated_local)
        # ... during run ...
        session.log_llm_request(provider="anthropic", model="claude-3-5-sonnet")
        session.log_llm_response(provider="anthropic", model="claude-3-5-sonnet")
        session.log_tool_call(tool_name="read_file")
        session.log_tool_result(tool_name="read_file")
        # ... on completion ...
        session.log_run_completed()
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from .schema import (
    AuditEvent,
    BudgetDecisionEvent,
    LlmRequestEvent,
    LlmResponseEvent,
    RunCancelledEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunStartedEvent,
    RuntimeMode,
    ToolCallEvent,
    ToolResultEvent,
    TrustLevel,
)
from .storage import AuditChainStore

_REDACT_SENTINEL = "<redacted>"


@dataclass
class RedactionConfig:
    """Controls which audit event fields are redacted.

    Read from environment variables on instantiation:

    - ``ARC_AUDIT_REDACT_MESSAGES`` → redact LLM messages (default: false)
    - ``ARC_AUDIT_REDACT_TOOL_ARGS`` → redact tool arguments (default: false)
    - ``ARC_AUDIT_REDACT_TOOL_RESULTS`` → redact tool results (default: false)
    """

    redact_messages: bool = False
    redact_tool_args: bool = False
    redact_tool_results: bool = False

    @classmethod
    def from_env(cls) -> RedactionConfig:
        return cls(
            redact_messages=os.environ.get("ARC_AUDIT_REDACT_MESSAGES", "").lower()
            in ("1", "true", "yes"),
            redact_tool_args=os.environ.get("ARC_AUDIT_REDACT_TOOL_ARGS", "").lower()
            in ("1", "true", "yes"),
            redact_tool_results=os.environ.get("ARC_AUDIT_REDACT_TOOL_RESULTS", "").lower()
            in ("1", "true", "yes"),
        )


def redact_event(event: AuditEvent, config: RedactionConfig) -> AuditEvent:
    """Return a copy of *event* with sensitive fields replaced.

    Redaction is applied before HMAC signing, so redacted and unredacted
    chains have different signatures. This is intentional: the audit chain
    verifies what was logged, not what was executed.
    """
    if isinstance(event, LlmRequestEvent):
        return _redact_llm_request(event, config)
    if isinstance(event, LlmResponseEvent):
        return _redact_llm_response(event, config)
    if isinstance(event, ToolCallEvent):
        return _redact_tool_call(event, config)
    if isinstance(event, ToolResultEvent):
        return _redact_tool_result(event, config)
    return event


def _redact_llm_request(event: LlmRequestEvent, config: RedactionConfig) -> LlmRequestEvent:
    if config.redact_messages:
        event = event.model_copy(update={"messages": [_REDACT_SENTINEL]})
    return event


def _redact_llm_response(event: LlmResponseEvent, config: RedactionConfig) -> LlmResponseEvent:
    if config.redact_messages:
        event = event.model_copy(update={"content": [_REDACT_SENTINEL]})
    return event


def _redact_tool_call(event: ToolCallEvent, config: RedactionConfig) -> ToolCallEvent:
    if config.redact_tool_args:
        event = event.model_copy(update={"arguments": {"__redacted__": _REDACT_SENTINEL}})
    return event


def _redact_tool_result(event: ToolResultEvent, config: RedactionConfig) -> ToolResultEvent:
    if config.redact_tool_results:
        event = event.model_copy(update={"result": {"__redacted__": _REDACT_SENTINEL}})
    return event


class AuditSession:
    """Context manager wrapping AuditChainStore for adapter use.

    Opens on enter, appends events during the run, and verifies on exit.
    If the HMAC key is unavailable, appends fail closed.
    """

    def __init__(
        self,
        run_id: str,
        session_id: str = "",
        store: Optional[AuditChainStore] = None,
        redaction: Optional[RedactionConfig] = None,
    ) -> None:
        self.run_id = run_id
        self.session_id = session_id
        self.store = store or AuditChainStore()
        self._redaction = redaction or RedactionConfig.from_env()
        self._ok = False
        self._msg = ""

    # -- Lifecycle events --

    def log_run_started(
        self,
        runtime: str = "",
        mode: RuntimeMode = RuntimeMode.fake,
        profile: str = "default",
        isolation: str = "subprocess",
    ) -> None:
        self._append(
            RunStartedEvent(
                run_id=self.run_id,
                session_id=self.session_id,
                runtime=runtime,
                mode=mode,
                profile=profile,
                isolation=isolation,
            )
        )

    def log_run_completed(self, runtime: str = "") -> None:
        self._append(
            RunCompletedEvent(run_id=self.run_id, session_id=self.session_id, runtime=runtime)
        )

    def log_run_failed(self, runtime: str = "", reason: str = "") -> None:
        self._append(
            RunFailedEvent(
                run_id=self.run_id, session_id=self.session_id, runtime=runtime, reason=reason
            )
        )

    def log_run_cancelled(self, runtime: str = "", reason: str = "") -> None:
        self._append(
            RunCancelledEvent(
                run_id=self.run_id, session_id=self.session_id, runtime=runtime, reason=reason
            )
        )

    # -- LLM events --

    def log_llm_request(
        self,
        provider: str = "",
        model: str = "",
        messages: Optional[list] = None,
        tools: Optional[list] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> None:
        self._append(
            LlmRequestEvent(
                run_id=self.run_id,
                session_id=self.session_id,
                provider=provider,
                model=model,
                messages=messages or [],
                tools=tools or [],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )

    def log_llm_response(self, provider: str = "", model: str = "", **kwargs) -> None:
        self._append(
            LlmResponseEvent(
                run_id=self.run_id,
                session_id=self.session_id,
                provider=provider,
                model=model,
                **kwargs,
            )
        )

    # -- Tool events --

    def log_tool_call(
        self,
        tool_name: str = "",
        tool_id: str = "",
        arguments: Optional[dict] = None,
        trust_level: TrustLevel = TrustLevel.untrusted,
    ) -> None:
        self._append(
            ToolCallEvent(
                run_id=self.run_id,
                session_id=self.session_id,
                tool_name=tool_name,
                tool_id=tool_id,
                arguments=arguments or {},
                trust_level=trust_level,
            )
        )

    def log_tool_result(
        self,
        tool_name: str = "",
        tool_id: str = "",
        result: Optional[dict] = None,
        trust_level: TrustLevel = TrustLevel.untrusted,
        error: Optional[dict] = None,
    ) -> None:
        self._append(
            ToolResultEvent(
                run_id=self.run_id,
                session_id=self.session_id,
                tool_name=tool_name,
                tool_id=tool_id,
                result=result or {},
                trust_level=trust_level,
                error=error,
            )
        )

    # -- Budget events --

    def log_budget_decision(
        self, decision: str = "allowed", reason: str = "", budget_state: Optional[dict] = None
    ) -> None:
        self._append(
            BudgetDecisionEvent(
                run_id=self.run_id,
                session_id=self.session_id,
                decision=decision,  # type: ignore[arg-type]
                reason=reason,
                budget_state=budget_state or {},
            )
        )

    # -- Internal --

    def _append(self, event: AuditEvent) -> None:
        self.store.append_event(redact_event(event, self._redaction))

    def verify(self) -> tuple[bool, str]:
        """Verify the audit chain for this run."""
        ok, msg = self.store.verify_run(self.run_id)
        return ok, msg

    def verify_and_log(self) -> None:
        """Verify and store the result."""
        self._ok, self._msg = self.store.verify_run(self.run_id)

    @property
    def verified(self) -> bool:
        return self._ok

    @property
    def verification_message(self) -> str:
        return self._msg

    # -- Context manager --

    async def __aenter__(self) -> AuditSession:
        self.store.ensure_run(self.run_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.log_run_failed(reason=str(exc_val))
        self.verify_and_log()


@asynccontextmanager
async def audit_session(
    run_id: str, session_id: str = "", store: Optional[AuditChainStore] = None
) -> AsyncIterator[AuditSession]:
    """Convenience async context manager for audit sessions.

    Usage::

        async with audit_session("run_abc") as session:
            session.log_run_started()
            session.log_llm_request(...)
            session.log_run_completed()
    """
    session = AuditSession(run_id=run_id, session_id=session_id, store=store)
    async with session:
        yield session
