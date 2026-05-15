"""Audit — tamper-evident audit log and HITL decision records.

Provides:
  - chain.py: SHA-256 hash-chained audit log (existing, unauthenticated)
  - key_manager.py: HMAC-SHA256 audit key management (ADR-005)
  - hmac_chain.py: HMAC-authenticated audit chain writer/verifier
  - hitl.py: Human-in-the-Loop decision records (scaffold)
"""
from __future__ import annotations

from .chain import AuditChainWriter, verify
from .key_manager import (
    AuditKeyManager,
    AuditKeyStatus,
    sign_audit_record,
    verify_audit_signature,
)
from .hmac_chain import HmacAuditChainWriter, verify_hmac_chain, GENESIS
from .hitl import HitlPrompt, HitlResponse, HitlDecision

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
]
