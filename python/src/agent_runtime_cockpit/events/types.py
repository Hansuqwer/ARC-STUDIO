"""Typed event models for the ARC Event Bus (Phase 32 / R25)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"evt-{uuid4().hex[:12]}"


class ArcEvent(BaseModel):
    event_id: str = Field(default_factory=_new_id)
    event_type: str
    run_id: Optional[str] = None
    timestamp: str = Field(default_factory=_now_iso)
    payload: dict[str, Any] = Field(default_factory=dict)


class HitlRequired(ArcEvent):
    event_type: Literal["hitl_required"] = "hitl_required"
    hitl_id: str
    step_id: str
    prompt_text: str
    context: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=list)
    timeout_seconds: int = 300


class HitlDecided(ArcEvent):
    event_type: Literal["hitl_decided"] = "hitl_decided"
    hitl_id: str
    decision: str
    operator_id: str = "anonymous"
    notes: str = ""


class AuditVerified(ArcEvent):
    event_type: Literal["audit_verified"] = "audit_verified"
    ok: bool
    mode: str
    records_checked: int = 0
    reason: str = ""
    duration_ms: int = 0


class RunCompleted(ArcEvent):
    event_type: Literal["run_completed"] = "run_completed"
    workflow_id: str
    duration_ms: int = 0
    status: str = "completed"


class RunFailed(ArcEvent):
    event_type: Literal["run_failed"] = "run_failed"
    workflow_id: str
    duration_ms: int = 0
    error: str = ""
    error_detail: str = ""


class QuotaWarning(ArcEvent):
    event_type: Literal["quota_warning"] = "quota_warning"
    dimension: str
    usage_pct: float = 0.0
    limit: float = 0.0
    current: float = 0.0


class SessionChanged(ArcEvent):
    event_type: Literal["session_changed"] = "session_changed"
    session_id: str
    operation: Literal["write", "delete", "update"]
    workspace: str


class AuditOverrideEvent(ArcEvent):
    """Emitted when a user overrides an automated protocol/risk decision.

    Phase 51: records operator overrides for the adaptive consensus protocol
    so they can be audited and reviewed.
    """

    event_type: Literal["audit_override"] = "audit_override"
    override_type: str  # e.g. "protocol_override"
    original_value: str  # e.g. "bft_escrow"
    override_value: str  # e.g. "raft"
    operator_id: str = "cli"
    reason: str = ""
    context: dict = {}  # type: ignore[assignment]


class TaskStateChanged(ArcEvent):
    """Emitted when a task transitions to a new state (Phase 54)."""

    event_type: Literal["task_state_changed"] = "task_state_changed"
    task_id: str
    task_type: str = ""
    operation: str = ""
    old_status: str = ""
    new_status: str = ""


class TaskCompleted(ArcEvent):
    """Emitted when a task completes successfully (Phase 54)."""

    event_type: Literal["task_completed"] = "task_completed"
    task_id: str
    task_type: str = ""
    operation: str = ""
    duration_ms: int = 0


class TaskFailed(ArcEvent):
    """Emitted when a task fails (Phase 54)."""

    event_type: Literal["task_failed"] = "task_failed"
    task_id: str
    task_type: str = ""
    operation: str = ""
    error: str = ""
    duration_ms: int = 0


class EvalCompleted(ArcEvent):
    """Emitted when an eval completes (Phase 58)."""

    event_type: Literal["eval_completed"] = "eval_completed"
    run_id: str
    pass_rate: float = 0.0
    total: int = 0
    failures_count: int = 0


class SandboxCommandEvent(ArcEvent):
    """Local/recent mirror of a sandbox audit event."""

    event_type: Literal["sandbox_command"] = "sandbox_command"


class ToolOutputVirtualized(ArcEvent):
    """Emitted when a tool output > threshold is stored as a handle."""

    event_type: Literal["tool_output_virtualized"] = "tool_output_virtualized"
    tool_name: str
    original_size_bytes: int
    handle_uri: str
    estimated_tokens_saved: int


class ContextCompacted(ArcEvent):
    """Emitted when R-02 compaction evicts messages from the context window."""

    event_type: Literal["context_compacted"] = "context_compacted"
    tokens_before: int
    tokens_after: int
    messages_evicted_count: int
    evicted_handles: list[str] = []


class ModelChanged(ArcEvent):
    """Emitted when the active model changes in the current session.

    capabilities_added: features present in current_model but not previous_model.
    capabilities_removed: features present in previous_model but not current_model.
    Both lists use the same capability keys as capability_gates.py: vision, tools, reasoning, etc.
    """

    event_type: Literal["model_changed"] = "model_changed"
    previous_model: str
    current_model: str
    capabilities_added: list[str] = []
    capabilities_removed: list[str] = []


EVENT_TYPE_MAP: dict[str, type[ArcEvent]] = {
    "hitl_required": HitlRequired,
    "hitl_decided": HitlDecided,
    "audit_verified": AuditVerified,
    "run_completed": RunCompleted,
    "run_failed": RunFailed,
    "quota_warning": QuotaWarning,
    "session_changed": SessionChanged,
    "audit_override": AuditOverrideEvent,
    "task_state_changed": TaskStateChanged,
    "task_completed": TaskCompleted,
    "task_failed": TaskFailed,
    "eval_completed": EvalCompleted,
    "sandbox_command": SandboxCommandEvent,
    "tool_output_virtualized": ToolOutputVirtualized,
    "context_compacted": ContextCompacted,
    "model_changed": ModelChanged,
}


def parse_event(payload: dict[str, Any]) -> ArcEvent:
    event_type = payload.get("event_type", "")
    cls = EVENT_TYPE_MAP.get(event_type)
    if cls is None:
        return ArcEvent(**payload)
    return cls(**payload)
