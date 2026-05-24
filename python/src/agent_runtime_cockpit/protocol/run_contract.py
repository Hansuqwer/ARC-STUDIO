"""Cockpit run contract protocol schema."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .run_receipt import RunReceipt

CONTRACT_ID_RE = re.compile(r"^ctr_[a-zA-Z0-9_-]{20,30}$")


class ContractStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    FULFILLED = "fulfilled"
    VIOLATED = "violated"


class RunContract(BaseModel):
    schema_version: int = 1
    contract_id: str
    run_id: Optional[str] = None
    session_id: str
    objective: str
    runtime: str
    mode: str
    allowed_tools: list[str] = Field(default_factory=list)
    write_scope: list[str] = Field(default_factory=list)
    cost_ceiling_usd: float | str = "unknown"
    approval_policy: str = "auto"
    rollback_plan: str = "none"
    evidence_expected: list[str] = Field(default_factory=list)
    status: ContractStatus = ContractStatus.PROPOSED
    terms_digest: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    accepted_at: Optional[str] = None
    fulfilled_at: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contract_id")
    @classmethod
    def _valid_contract_id(cls, value: str) -> str:
        if not CONTRACT_ID_RE.match(value):
            raise ValueError(f"Invalid contract_id: {value!r}")
        return value

    @field_validator("mode")
    @classmethod
    def _valid_mode(cls, value: str) -> str:
        if value not in ("plan", "build", "auto"):
            raise ValueError(f"Invalid mode: {value}")
        return value

    @field_validator("cost_ceiling_usd")
    @classmethod
    def _valid_cost(cls, value: float | str) -> float | str:
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError("cost_ceiling_usd must be non-negative")
        return value

    def is_satisfied_by(self, receipt: RunReceipt) -> bool:
        if receipt.run_id != self.run_id:
            return False
        if receipt.status in ("failed", "cancelled"):
            return False
        if isinstance(self.cost_ceiling_usd, (int, float)):
            actual = (
                receipt.cost_usd if isinstance(receipt.cost_usd, (int, float)) else float("inf")
            )
            if actual > self.cost_ceiling_usd:
                return False
        return True
