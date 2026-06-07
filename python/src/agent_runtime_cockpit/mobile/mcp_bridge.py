"""MCP dev-bridge guard for ARC Mobile Runtime (Phase 20).

A **default-OFF**, fail-closed admission guard for a future local MCP dev bridge. It does NOT
open any network connection or listener — it only decides, deterministically, whether a
connection *would* be admitted. Admission requires ALL of: the bridge explicitly enabled, a
loopback-only host, a matching token (constant-time compare), and a non-expired TTL. Any
missing/failed condition denies. No production MCP gateway, no remote listener.
"""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BridgeDecision:
    allowed: bool
    reason: str
    deterministic: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "deterministic": self.deterministic}


@dataclass
class MobileMcpDevBridge:
    """Default-off, fail-closed admission guard for a loopback MCP dev bridge."""

    enabled: bool = False
    token: str | None = None
    ttl_seconds: int | None = None
    started_at: datetime | None = None
    allowed_hosts: set[str] = field(default_factory=lambda: set(_LOOPBACK_HOSTS))

    @staticmethod
    def issue_token() -> str:
        """Generate a fresh bridge token (caller passes it to the connecting dev client)."""
        return secrets.token_urlsafe(32)

    def enable(self, token: str, ttl_seconds: int, now: datetime | None = None) -> None:
        """Explicitly enable the bridge with a token + TTL. Off until this is called."""
        if not token:
            raise ValueError("a non-empty token is required to enable the dev bridge")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        self.enabled = True
        self.token = token
        self.ttl_seconds = ttl_seconds
        self.started_at = now or _now()

    def disable(self) -> None:
        self.enabled = False
        self.token = None
        self.started_at = None

    def _expired(self, now: datetime) -> bool:
        if self.started_at is None or self.ttl_seconds is None:
            return True
        return now >= self.started_at + timedelta(seconds=self.ttl_seconds)

    def check_connection(
        self, host: str, token: str | None, now: datetime | None = None
    ) -> BridgeDecision:
        """Deterministic, fail-closed admission decision for a dev-client connection."""
        now = now or _now()
        if not self.enabled:
            return BridgeDecision(False, "bridge disabled (default-off)")
        if host not in self.allowed_hosts:
            return BridgeDecision(False, f"non-loopback host '{host}' refused")
        if not token or self.token is None or not hmac.compare_digest(token, self.token):
            return BridgeDecision(False, "invalid or missing token")
        if self._expired(now):
            return BridgeDecision(False, "bridge token TTL expired")
        return BridgeDecision(True, "loopback dev connection admitted")
