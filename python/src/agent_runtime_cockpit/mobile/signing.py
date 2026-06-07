"""Signed plan envelope for ARC Mobile Runtime.

Phase 7 skeleton: HMAC-SHA256 signing of MobileActionPlan.
This provides tamper-detection for plans in transit.

Production note: This uses a symmetric HMAC key stored locally.
A future version will support asymmetric signing (Ed25519) once
a key management strategy is decided. The envelope format is
stable; the algorithm field allows migration.

Usage:
    key = os.urandom(32)  # or load from secure storage
    envelope = sign_plan(plan, key)
    assert verify_plan(envelope, key)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict

from .hashing import plan_hash as _plan_hash
from .models import MobileActionPlan

SIGNING_ALGORITHM = "hmac-sha256"
SIGNING_VERSION = "1"


class SignedPlanEnvelope(BaseModel):
    """A MobileActionPlan wrapped with a tamper-evident signature."""

    model_config = ConfigDict(extra="forbid")

    algorithm: str = SIGNING_ALGORITHM
    version: str = SIGNING_VERSION
    plan_id: str
    plan_hash: str  # SHA-256 of canonical plan JSON
    signed_at: str  # ISO-8601 UTC
    nonce: str  # 32 hex chars — prevents replay
    signature: str  # HMAC-SHA256(plan_hash + nonce + signed_at, key) hex
    plan: dict[str, Any]  # serialised MobileActionPlan


def _signing_message(plan_hash: str, nonce: str, signed_at: str) -> bytes:
    """Canonical bytes signed by the HMAC key."""
    return f"{plan_hash}:{nonce}:{signed_at}".encode()


def sign_plan(plan: MobileActionPlan, key: bytes) -> SignedPlanEnvelope:
    """Sign a MobileActionPlan and return a SignedPlanEnvelope.

    key: raw bytes (≥16 bytes recommended; 32 bytes for AES-128 equivalent).
    """
    ph = _plan_hash(plan)
    nonce = secrets.token_hex(16)
    signed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    msg = _signing_message(ph, nonce, signed_at)
    sig = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return SignedPlanEnvelope(
        plan_id=plan.plan_id,
        plan_hash=ph,
        signed_at=signed_at,
        nonce=nonce,
        signature=sig,
        plan=plan.model_dump(mode="json"),
    )


def verify_plan(envelope: SignedPlanEnvelope, key: bytes) -> bool:
    """Verify a SignedPlanEnvelope. Returns True iff signature is valid.

    Also verifies the embedded plan_hash matches the plan contents.
    """
    try:
        # Re-derive plan hash from embedded plan
        plan = MobileActionPlan.model_validate(envelope.plan)
        computed_plan_hash = _plan_hash(plan)
        if computed_plan_hash != envelope.plan_hash:
            return False

        # Verify HMAC
        msg = _signing_message(envelope.plan_hash, envelope.nonce, envelope.signed_at)
        expected = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, envelope.signature)
    except Exception:  # noqa: BLE001
        return False
