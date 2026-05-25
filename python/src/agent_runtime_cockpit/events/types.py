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


EVENT_TYPE_MAP: dict[str, type[ArcEvent]] = {
    "hitl_required": HitlRequired,
    "hitl_decided": HitlDecided,
    "audit_verified": AuditVerified,
    "run_completed": RunCompleted,
    "run_failed": RunFailed,
    "quota_warning": QuotaWarning,
}


def parse_event(payload: dict[str, Any]) -> ArcEvent:
    event_type = payload.get("event_type", "")
    cls = EVENT_TYPE_MAP.get(event_type)
    if cls is None:
        return ArcEvent(**payload)
    return cls(**payload)
