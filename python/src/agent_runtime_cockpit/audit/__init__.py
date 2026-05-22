"""Audit — tamper-evident audit log and HITL decision records (ADR-021).

Provides:
  - chain.py: SHA-256 hash-chained audit log (unauthenticated)
  - key_manager.py: HMAC-SHA256 audit key management (ADR-005)
  - hmac_chain.py: HMAC-authenticated audit chain writer/verifier
  - hitl.py: Human-in-the-Loop decision records (scaffold)
  - schema.py: Typed audit event models for EU AI Act compliance
  - storage.py: Managed per-run audit chain lifecycle
"""
from __future__ import annotations

from .chain import AuditChainWriter, verify
from .hitl import HitlDecision, HitlPrompt, HitlResponse
from .hmac_chain import GENESIS, HmacAuditChainWriter, verify_hmac_chain
from .key_manager import (
    AuditKeyManager,
    AuditKeyStatus,
    sign_audit_record,
    verify_audit_signature,
)
from .schema import (
    AuditEvent,
    AuditEventType,
    BudgetDecisionEvent,
    LlmRequestEvent,
    LlmResponseEvent,
    RunCancelledEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunStartedEvent,
    RuntimeMode,
    StopReason,
    ToolCallEvent,
    ToolResultEvent,
    TrustLevel,
    event_from_dict,
)
from .session import AuditSession, audit_session
from .storage import AuditChainStore

__all__ = [
    "AuditChainWriter",
    "verify",
    "AuditKeyManager",
    "AuditKeyStatus",
    "sign_audit_record",
    "verify_audit_signature",
    "HmacAuditChainWriter",
    "verify_hmac_chain",
    "GENESIS",
    "HitlPrompt",
    "HitlResponse",
    "HitlDecision",
    "AuditEvent",
    "AuditEventType",
    "BudgetDecisionEvent",
    "LlmRequestEvent",
    "LlmResponseEvent",
    "RunCancelledEvent",
    "RunCompletedEvent",
    "RunFailedEvent",
    "RunStartedEvent",
    "RuntimeMode",
    "StopReason",
    "ToolCallEvent",
    "ToolResultEvent",
    "TrustLevel",
    "event_from_dict",
    "AuditChainStore",
    "AuditSession",
    "audit_session",
]
