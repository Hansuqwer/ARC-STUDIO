"""Cockpit failure autopsy protocol schema."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .evidence_refs import EvidenceRef


class RetryOption(BaseModel):
    label: str
    command: Optional[str] = None
    risk: str = "medium"

    @field_validator("risk")
    @classmethod
    def _valid_risk(cls, value: str) -> str:
        if value not in ("low", "medium", "high"):
            raise ValueError(f"Invalid risk: {value}")
        return value


class FailureAutopsy(BaseModel):
    schema_version: int = 1
    run_id: str
    probable_cause: str = "unknown"
    confidence: str = "unknown"
    failed_node: Optional[str] = None
    last_safe_state: Optional[str] = None
    retry_options: list[RetryOption] = Field(default_factory=list)
    related_issues: list[str] = Field(default_factory=list)
    knows: list[str] = Field(default_factory=list)
    guesses: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    error_category: Optional[str] = None
    stack_summary: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def _valid_confidence(cls, value: str) -> str:
        if value not in ("high", "medium", "low", "unknown"):
            raise ValueError(f"Invalid confidence: {value}")
        return value

    @field_validator("error_category")
    @classmethod
    def _valid_error_category(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in (
            "tool_timeout",
            "provider_error",
            "validation",
            "internal",
            "unknown",
        ):
            raise ValueError(f"Invalid error_category: {value}")
        return value

    @model_validator(mode="after")
    def _valid_evidence_count(self) -> "FailureAutopsy":
        if len(self.knows) + len(self.guesses) > 50:
            raise ValueError("Too many knows/guesses (max 50 total)")
        return self
