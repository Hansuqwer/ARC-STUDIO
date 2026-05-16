"""Cockpit evidence reference protocol schema."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


EVIDENCE_ID_RE = re.compile(r"^ev_[a-zA-Z0-9_-]{20,30}$")


class EvidenceKind(str, Enum):
    FILE = "file"
    TOOL_OUTPUT = "tool_output"
    RUN = "run"
    NODE = "node"
    LEDGER = "ledger"
    RECEIPT = "receipt"


class EvidenceRef(BaseModel):
    schema_version: int = 1
    evidence_id: str
    kind: EvidenceKind
    target: str
    label: Optional[str] = None
    range_: Optional[tuple[int, int]] = Field(default=None, alias="range")
    redacted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @field_validator("evidence_id")
    @classmethod
    def _valid_evidence_id(cls, value: str) -> str:
        if not EVIDENCE_ID_RE.match(value):
            raise ValueError(f"Invalid evidence_id: {value!r}")
        return value

    @field_validator("target")
    @classmethod
    def _target_not_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("EvidenceRef target must not be empty")
        return value

    @field_validator("range_")
    @classmethod
    def _valid_range(cls, value: Optional[tuple[int, int]]) -> Optional[tuple[int, int]]:
        if value is None:
            return value
        start, end = value
        if start < 0 or end < 0 or start > end:
            raise ValueError(f"Invalid range: ({start}, {end})")
        return value
