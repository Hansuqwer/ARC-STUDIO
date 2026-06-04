"""Runtime enforcement gate for Capability Cards.

Decision rules are deterministic and LLM-free (CoSAI rule).
Fail-closed: missing key, invalid signature, parse error → deny, not allow.

Mode resolution order:
  1. CLI flag (--enforce-cards / --no-enforce-cards)
  2. Env var ARC_CAPABILITIES_ENFORCE (off|warn|strict)
  3. Default: warn
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

from .models import AuditLevel, HitlRequirement, TrustLevel, CARD_SCHEMA_VERSION

if TYPE_CHECKING:
    from .models import CapabilityCard
    from .signing import SignedCapabilityCard
    from .registry import CardRegistry
    from ..security.context import EnforcementContext


Decision = Literal["allow", "deny", "warn"]
Mode = Literal["off", "warn", "strict"]

_AUDIT_ORDER = {
    AuditLevel.NONE: 0,
    AuditLevel.ARC_SHA256: 1,
    AuditLevel.SWARMGRAPH_HMAC: 2,
    AuditLevel.FULL: 3,
}


class DenialReason(str, Enum):
    SIGNATURE_INVALID = "capability_card_signature_invalid"
    SIGNATURE_MISSING = "capability_card_signature_missing"
    TRUST_LEVEL_REQUIRED = "capability_card_trust_level_required"
    PAID_CALL_NOT_ALLOWED = "capability_card_paid_call_not_allowed"
    AUDIT_LEVEL_INSUFFICIENT = "capability_card_audit_level_insufficient"
    HITL_REQUIRED = "capability_card_hitl_required"
    CARD_NOT_FOUND = "capability_card_not_found"
    CARD_OPAQUE = "capability_card_opaque"
    REQUIRES_REVIEW = "capability_card_requires_review"
    SCHEMA_VERSION_UNSUPPORTED = "capability_card_schema_version_unsupported"


@dataclass(frozen=True)
class EnforcementResult:
    decision: Decision
    reason: str  # DenialReason value or "ok"
    card_id: Optional[str]
    card_hash: Optional[str]
    correlation_id: str
    details: dict  # safe-to-serialize structured detail


def resolve_mode(
    env: dict | None = None,
    cli_override: Optional[Mode] = None,
) -> Mode:
    """Resolve enforcement mode from CLI flag → env var → default (warn)."""
    if cli_override is not None:
        return cli_override
    env = env if env is not None else os.environ
    raw = env.get("ARC_CAPABILITIES_ENFORCE", "").lower()
    if raw in ("off", "warn", "strict"):
        return raw  # type: ignore[return-value]
    return "warn"


def enforce_card(
    *,
    card: Optional["CapabilityCard"],
    signed: Optional["SignedCapabilityCard"],
    ctx: Optional["EnforcementContext"] = None,
    mode: Mode = "warn",
    verifier_secret_key: Optional[str] = None,
    verifier_public_key_pem: Optional[str] = None,
    current_audit_mode: Literal["sha256", "hmac"] = "sha256",
    run_has_hitl_gate: bool = False,
) -> EnforcementResult:
    """Enforce a Capability Card, returning a deterministic decision.

    Decision rules are evaluated in strict order; first failing rule wins.
    """
    from ..security.context import EnforcementContext, get_enforcement_context
    from .signing import verify_card
    from .hashing import card_hash as compute_hash

    if ctx is None:
        ctx = get_enforcement_context()

    def _correlation() -> str:
        return EnforcementContext.generate_correlation_id()

    def _allow(
        reason: str = "ok",
        card_id: Optional[str] = None,
        card_hash: Optional[str] = None,
        details: dict | None = None,
    ) -> EnforcementResult:
        return EnforcementResult(
            decision="allow",
            reason=reason,
            card_id=card_id,
            card_hash=card_hash,
            correlation_id=_correlation(),
            details=details or {},
        )

    def _deny_or_warn(
        reason: DenialReason,
        card_id: Optional[str] = None,
        card_hash: Optional[str] = None,
        details: dict | None = None,
    ) -> EnforcementResult:
        decision: Decision = "deny" if mode == "strict" else "warn"
        return EnforcementResult(
            decision=decision,
            reason=reason.value,
            card_id=card_id,
            card_hash=card_hash,
            correlation_id=_correlation(),
            details=details or {},
        )

    # Rule 0: mode off → always allow
    if mode == "off":
        cid = card.id if card else None
        ch = compute_hash(card) if card else None
        return _allow(card_id=cid, card_hash=ch)

    # Rule 1: no card at all
    if card is None and signed is None:
        return _deny_or_warn(DenialReason.CARD_NOT_FOUND)

    # Resolve the card object (prefer signed.card)
    c = signed.card if signed is not None else card
    if c is None:
        return _deny_or_warn(DenialReason.CARD_NOT_FOUND)

    cid = c.id
    ch = compute_hash(c)

    # Rule 2: schema version mismatch
    if c.schema_version != CARD_SCHEMA_VERSION:
        return _deny_or_warn(
            DenialReason.SCHEMA_VERSION_UNSUPPORTED,
            card_id=cid,
            card_hash=ch,
            details={"expected": str(CARD_SCHEMA_VERSION), "got": str(c.schema_version)},
        )

    # Rule 3: opaque / requires_review
    if getattr(c, "opaque", False):
        return _deny_or_warn(DenialReason.CARD_OPAQUE, card_id=cid, card_hash=ch)
    if getattr(c, "requires_review", False):
        return _deny_or_warn(DenialReason.REQUIRES_REVIEW, card_id=cid, card_hash=ch)

    # Rule 4: signature verification
    if signed is not None:
        has_verifier = verifier_secret_key is not None or verifier_public_key_pem is not None
        if not has_verifier:
            return _deny_or_warn(DenialReason.SIGNATURE_MISSING, card_id=cid, card_hash=ch)
        valid = verify_card(
            signed,
            secret_key=verifier_secret_key,
            public_key_pem=verifier_public_key_pem,
        )
        if not valid:
            return _deny_or_warn(DenialReason.SIGNATURE_INVALID, card_id=cid, card_hash=ch)
    elif mode == "strict":
        # Unsigned in strict mode
        return EnforcementResult(
            decision="deny",
            reason=DenialReason.SIGNATURE_MISSING.value,
            card_id=cid,
            card_hash=ch,
            correlation_id=_correlation(),
            details={},
        )

    # Rule 5: trust level
    trust = getattr(c, "trust", None)
    if trust is not None:
        tl = getattr(trust, "trust_level", None)
        if tl == TrustLevel.PRIVILEGED and not ctx.trust_workspace:
            return _deny_or_warn(DenialReason.TRUST_LEVEL_REQUIRED, card_id=cid, card_hash=ch)

    # Rule 6: paid call gate
    caps = getattr(c, "capabilities", None)
    cost = getattr(c, "cost", None)
    paid_required = (caps is not None and getattr(caps, "can_make_paid_calls", False)) or (
        cost is not None and getattr(cost, "paid_call_gate", False)
    )
    if paid_required and not ctx.allow_paid:
        return _deny_or_warn(DenialReason.PAID_CALL_NOT_ALLOWED, card_id=cid, card_hash=ch)

    # Rule 7: audit level
    audit = getattr(c, "audit", None)
    if audit is not None:
        required_level = getattr(audit, "audit_level", AuditLevel.NONE)
        current_level = (
            AuditLevel.ARC_SHA256 if current_audit_mode == "sha256" else AuditLevel.SWARMGRAPH_HMAC
        )
        if _AUDIT_ORDER.get(required_level, 0) > _AUDIT_ORDER.get(current_level, 0):
            return _deny_or_warn(
                DenialReason.AUDIT_LEVEL_INSUFFICIENT,
                card_id=cid,
                card_hash=ch,
                details={"required": required_level.value, "current": current_level.value},
            )

    # Rule 8: HITL
    if trust is not None:
        hitl = getattr(trust, "hitl_requirement", HitlRequirement.NONE)
        if hitl == HitlRequirement.BLOCKING and not run_has_hitl_gate:
            return _deny_or_warn(DenialReason.HITL_REQUIRED, card_id=cid, card_hash=ch)

    return _allow(card_id=cid, card_hash=ch)


def enforce_card_by_id(
    *,
    card_id: str,
    registry: "CardRegistry",
    ctx: Optional["EnforcementContext"] = None,
    mode: Mode = "warn",
    verifier_secret_key: Optional[str] = None,
    verifier_public_key_pem: Optional[str] = None,
    current_audit_mode: Literal["sha256", "hmac"] = "sha256",
    run_has_hitl_gate: bool = False,
) -> EnforcementResult:
    """Enforce by looking up a card from the registry first."""
    c = registry.load(card_id)
    return enforce_card(
        card=c,
        signed=None,
        ctx=ctx,
        mode=mode,
        verifier_secret_key=verifier_secret_key,
        verifier_public_key_pem=verifier_public_key_pem,
        current_audit_mode=current_audit_mode,
        run_has_hitl_gate=run_has_hitl_gate,
    )


__all__ = [
    "Decision",
    "Mode",
    "DenialReason",
    "EnforcementResult",
    "resolve_mode",
    "enforce_card",
    "enforce_card_by_id",
]
