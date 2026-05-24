"""Human-in-the-Loop decision records — audit-signed HITL persistence (ADR-005)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HitlDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    SKIP = "skip"


class HitlPrompt(BaseModel):
    """A HITL prompt sent to a human operator."""

    hitl_id: str
    run_id: str
    step_id: str
    prompt_text: str
    context: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=lambda: [d.value for d in HitlDecision])
    timeout_seconds: int = 300
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HitlResponse(BaseModel):
    """A human operator's response to a HITL prompt."""

    hitl_id: str
    run_id: str
    decision: HitlDecision
    operator_id: str = "anonymous"
    modified_data: Optional[dict[str, Any]] = None
    notes: str = ""
    responded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_event(self) -> dict[str, Any]:
        """Convert to an audit-signable event dict."""
        return {
            "type": "hitl_decision",
            "hitl_id": self.hitl_id,
            "run_id": self.run_id,
            "decision": self.decision.value,
            "operator_id": self.operator_id,
            "modified_data": self.modified_data,
            "notes": self.notes,
            "responded_at": self.responded_at,
        }
