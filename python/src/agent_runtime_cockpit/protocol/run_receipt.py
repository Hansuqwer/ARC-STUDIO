"""Cockpit run receipt protocol schema."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .evidence_refs import EvidenceRef

RECEIPT_ID_RE = re.compile(r"^rcpt_[a-zA-Z0-9_-]{20,30}$")


class FileChange(BaseModel):
    path: str
    added: int = 0
    removed: int = 0


class RunReceipt(BaseModel):
    schema_version: int = 1
    receipt_id: str
    run_id: str
    session_id: Optional[str] = None
    contract_id: Optional[str] = None
    status: str
    summary: str
    cost_usd: float | str = "unknown"
    duration_ms: int = 0
    files_changed: list[FileChange] = Field(default_factory=list)
    approvals: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    rollback_command: Optional[str] = None
    trust_boundaries_crossed: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    audit_chain_ref: Optional[str] = None
    signature: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("receipt_id")
    @classmethod
    def _valid_receipt_id(cls, value: str) -> str:
        if not RECEIPT_ID_RE.match(value):
            raise ValueError(f"Invalid receipt_id: {value!r}")
        return value

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value: str) -> str:
        if value not in ("completed", "failed", "cancelled"):
            raise ValueError(f"Invalid receipt status: {value}")
        return value

    @field_validator("summary")
    @classmethod
    def _summary_size(cls, value: str) -> str:
        if len(value) > 2000:
            raise ValueError("Summary exceeds 2000 chars")
        return value

    def canonical_bytes(self) -> bytes:
        data = self.model_dump(mode="json", by_alias=True, exclude={"signature"})
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, key: str) -> None:
        self.signature = hmac.new(key.encode(), self.canonical_bytes(), hashlib.sha256).hexdigest()

    def verify(self, key: str) -> bool:
        if not self.signature:
            return False
        expected = hmac.new(key.encode(), self.canonical_bytes(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)
