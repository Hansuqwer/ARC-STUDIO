"""Typed audit event schema for EU AI Act compliance (ADR-021).

Each event type is a Pydantic model with a ``to_audit_event()`` method
that returns a dict consumable by ``HmacAuditChainWriter.append()``.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    llm_request = "llm_request"
    llm_response = "llm_response"
    tool_call = "tool_call"
    tool_result = "tool_result"
    hitl_prompt = "hitl_prompt"
    hitl_response = "hitl_response"
    budget_decision = "budget_decision"
    run_started = "run_started"
    run_completed = "run_completed"
    run_failed = "run_failed"
    run_cancelled = "run_cancelled"


class TrustLevel(str, Enum):
    trusted = "trusted"
    untrusted = "untrusted"
    mixed = "mixed"


class StopReason(str, Enum):
    end_turn = "end_turn"
    tool_use = "tool_use"
    max_tokens = "max_tokens"
    stop_sequence = "stop_sequence"
    cancelled = "cancelled"


class RuntimeMode(str, Enum):
    fake = "fake"
    gated_local = "gated_local"
    provider_backed = "provider_backed"


# ---------------------------------------------------------------------------
# Event payload models
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """Base class for all audit events.

    Subclasses must override ``event_type`` and implement ``to_audit_event()``.
    """

    run_id: str
    session_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    @abstractmethod
    def event_type(self) -> AuditEventType: ...

    @abstractmethod
    def to_audit_event(self) -> dict[str, Any]:
        """Serialize to dict for HmacAuditChainWriter."""
        ...


class LlmRequestEvent(AuditEvent):
    provider: str
    model: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 1.0

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.llm_request

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "messages": self.messages,
            "tools": self.tools,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


class LlmResponseEvent(AuditEvent):
    provider: str
    model: str
    response_id: str = ""
    stop_reason: Optional[StopReason] = None
    usage: dict[str, int] = Field(default_factory=dict)
    content: list[dict[str, Any]] = Field(default_factory=list)
    total_cost: Optional[Decimal] = None
    currency: str = "USD"
    measured: bool = True

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.llm_response

    def to_audit_event(self) -> dict[str, Any]:
        cost = None
        if self.total_cost is not None:
            cost = {
                "total_cost": str(self.total_cost),
                "currency": self.currency,
                "measured": self.measured,
            }
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "response_id": self.response_id,
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "usage": self.usage,
            "content": self.content,
            "cost": cost,
        }


class ToolCallEvent(AuditEvent):
    tool_name: str
    tool_id: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)
    trust_level: TrustLevel = TrustLevel.untrusted

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.tool_call

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "arguments": self.arguments,
            "trust_level": self.trust_level.value,
        }


class ToolResultEvent(AuditEvent):
    tool_name: str
    tool_id: str = ""
    result: dict[str, Any] = Field(default_factory=dict)
    trust_level: TrustLevel = TrustLevel.untrusted
    error: Optional[dict[str, str]] = None

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.tool_result

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "result": self.result,
            "trust_level": self.trust_level.value,
            "error": self.error,
        }


class BudgetDecisionEvent(AuditEvent):
    decision: Literal["allowed", "blocked"]
    reason: str
    budget_state: dict[str, str] = Field(default_factory=dict)

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.budget_decision

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "decision": self.decision,
            "reason": self.reason,
            "budget_state": self.budget_state,
        }


class RunStartedEvent(AuditEvent):
    runtime: str = ""
    mode: RuntimeMode = RuntimeMode.fake
    profile: str = "default"
    isolation: str = "subprocess"

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.run_started

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "runtime": self.runtime,
            "mode": self.mode.value,
            "profile": self.profile,
            "isolation": self.isolation,
        }


class RunCompletedEvent(AuditEvent):
    runtime: str = ""

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.run_completed

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "runtime": self.runtime,
        }


class RunFailedEvent(AuditEvent):
    runtime: str = ""
    reason: str = ""

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.run_failed

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "runtime": self.runtime,
            "reason": self.reason,
        }


class RunCancelledEvent(AuditEvent):
    runtime: str = ""
    reason: str = ""

    @property
    def event_type(self) -> AuditEventType:
        return AuditEventType.run_cancelled

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "runtime": self.runtime,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Factory: dict -> typed event (for deserialization and verification)
# ---------------------------------------------------------------------------

_EVENT_TYPE_MAP: dict[AuditEventType, type[AuditEvent]] = {
    AuditEventType.llm_request: LlmRequestEvent,
    AuditEventType.llm_response: LlmResponseEvent,
    AuditEventType.tool_call: ToolCallEvent,
    AuditEventType.tool_result: ToolResultEvent,
    AuditEventType.budget_decision: BudgetDecisionEvent,
    AuditEventType.run_started: RunStartedEvent,
    AuditEventType.run_completed: RunCompletedEvent,
    AuditEventType.run_failed: RunFailedEvent,
    AuditEventType.run_cancelled: RunCancelledEvent,
}


def event_from_dict(data: dict[str, Any]) -> AuditEvent:
    """Reconstruct a typed audit event from a dict.

    The dict should contain at minimum ``type``, ``run_id``, and ``timestamp``
    (as produced by ``to_audit_event()``).
    """
    event_type_str = data.get("type")
    if not event_type_str:
        raise ValueError("Audit event dict missing 'type' field")
    try:
        event_type = AuditEventType(event_type_str)
    except ValueError:
        raise ValueError(f"Unknown audit event type: {event_type_str!r}")
    cls = _EVENT_TYPE_MAP.get(event_type)
    if cls is None:
        raise ValueError(f"No handler registered for event type: {event_type!r}")
    return cls(**data)
