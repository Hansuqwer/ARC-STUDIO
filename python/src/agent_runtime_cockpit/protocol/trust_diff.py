"""Cockpit trust diff protocol schema."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


DIFF_ID_RE = re.compile(r"^td_[a-zA-Z0-9_-]{20,30}$")


class TrustDiff(BaseModel):
    schema_version: int = 1
    diff_id: str
    workspace_path: str
    before: list[str] = Field(default_factory=list)
    after: list[str] = Field(default_factory=list)
    added_capabilities: list[str] = Field(default_factory=list)
    removed_restrictions: list[str] = Field(default_factory=list)
    affected_runtimes: list[str] = Field(default_factory=list)
    reason: str = "unknown"
    requires_confirmation: bool = False
    confirmed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("diff_id")
    @classmethod
    def _valid_diff_id(cls, value: str) -> str:
        if not DIFF_ID_RE.match(value):
            raise ValueError(f"Invalid diff_id: {value!r}")
        return value

    @field_validator("reason")
    @classmethod
    def _valid_reason(cls, value: str) -> str:
        if value not in ("workspace_first_trust", "profile_switch", "runtime_added", "unknown"):
            raise ValueError(f"Invalid reason: {value}")
        return value
