"""Approval grant engine for ARC Mobile Runtime.

Phase 7 skeleton: models and in-memory grant store.
ApprovalGrant is a scoped, time-limited, revocable permission
to execute a specific capability.

Production note: grants will need persistent storage and
cryptographic binding to signed plans. This skeleton provides
the correct data model and semantics.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict

_GRANT_STORE: dict[str, "ApprovalGrant"] = {}


class ApprovalGrant(BaseModel):
    """A scoped, expiring, revocable approval grant."""

    model_config = ConfigDict(extra="forbid")

    grant_id: str
    capability_id: str
    scope: str  # e.g. "read:once", "write:session"
    issued_at: str
    expires_at: str
    revoked: bool = False
    subject: Optional[str] = None  # user/device identifier (opaque)
    plan_hash: Optional[str] = None  # bind to a specific signed plan

    def is_valid(self) -> bool:
        """Return True iff the grant is unexpired and not revoked."""
        if self.revoked:
            return False
        now = datetime.now(timezone.utc)
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return now < expires
        except Exception:  # noqa: BLE001
            return False


def issue_grant(
    capability_id: str,
    scope: str,
    ttl_seconds: int,
    *,
    subject: str | None = None,
    plan_hash: str | None = None,
) -> ApprovalGrant:
    """Issue a new ApprovalGrant and store it in memory."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=ttl_seconds)
    grant = ApprovalGrant(
        grant_id=str(uuid.uuid4()),
        capability_id=capability_id,
        scope=scope,
        issued_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=expires.isoformat().replace("+00:00", "Z"),
        subject=subject,
        plan_hash=plan_hash,
    )
    _GRANT_STORE[grant.grant_id] = grant
    return grant


def revoke_grant(grant_id: str) -> bool:
    """Revoke a grant. Returns True if the grant was found and revoked."""
    grant = _GRANT_STORE.get(grant_id)
    if grant is None:
        return False
    _GRANT_STORE[grant_id] = grant.model_copy(update={"revoked": True})
    return True


def get_grant(grant_id: str) -> ApprovalGrant | None:
    return _GRANT_STORE.get(grant_id)


def list_active_grants() -> list[ApprovalGrant]:
    return [g for g in _GRANT_STORE.values() if g.is_valid()]


def clear_grants() -> None:
    """Clear all grants (test helper)."""
    _GRANT_STORE.clear()
