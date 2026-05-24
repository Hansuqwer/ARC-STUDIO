"""ARC Studio audit event schema — Pydantic models for ADR-021 audit chain.

Mirrors the TypeScript types in packages/arc-protocol-ts/src/audit-events.ts.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    AUDIT_CHAIN_STARTED = "AUDIT_CHAIN_STARTED"
    AUDIT_CHAIN_LINK_ADDED = "AUDIT_CHAIN_LINK_ADDED"
    AUDIT_CHAIN_SEALED = "AUDIT_CHAIN_SEALED"
    AUDIT_CHAIN_VERIFIED = "AUDIT_CHAIN_VERIFIED"
    AUDIT_CHAIN_FAILED = "AUDIT_CHAIN_FAILED"
    AUDIT_KEY_ROTATED = "AUDIT_KEY_ROTATED"
    AUDIT_EXPORTED = "AUDIT_EXPORTED"


class AuditEventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    run_id: str = Field(alias="runId")
    event_type: AuditEventType = Field(alias="eventType")
    timestamp: str
    sequence: int
    severity: AuditEventSeverity
    producer: str
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "use_enum_values": True}


class AuditChainLink(BaseModel):
    chain_id: str = Field(alias="chainId")
    previous_hash: str = Field(alias="previousHash")
    hash: str
    event: AuditEvent
    sealed_at: str | None = Field(default=None, alias="sealedAt")

    model_config = {"populate_by_name": True, "use_enum_values": True}


class AuditChainManifest(BaseModel):
    chain_id: str = Field(alias="chainId")
    run_id: str = Field(alias="runId")
    links: list[AuditChainLink]
    schema_version: int = Field(default=1, alias="schemaVersion")
    created_at: str = Field(alias="createdAt")
    sealed_at: str | None = Field(default=None, alias="sealedAt")
    verified_at: str | None = Field(default=None, alias="verifiedAt")
    status: str  # 'active' | 'sealed' | 'verified' | 'compromised'

    model_config = {"populate_by_name": True, "use_enum_values": True}
