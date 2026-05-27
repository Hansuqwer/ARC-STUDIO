"""Pydantic models for webhook configuration (Phase 32 / R25).

Phase 52: DeadLetterEntry hardened with attempt_count, payload_hash,
last_error alias, failed_at alias, and redacted_payload.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"wh-{uuid4().hex[:12]}"


class WebhookConfig(BaseModel):
    id: str = Field(default_factory=_new_id)
    url: str
    secret: str
    enabled_events: list[str] = Field(default_factory=lambda: ["*"])
    retry_max: int = 5
    retry_base_delay_s: float = 1.0
    created_at: str = Field(default_factory=_now_iso)


def _payload_hash(payload: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON of payload (secrets already redacted)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DeadLetterEntry(BaseModel):
    """Dead-letter log entry for failed webhook deliveries.

    Phase 52 additions:
    - ``attempt_count``: number of delivery attempts made.
    - ``payload_hash``: SHA-256 of the redacted payload (no plaintext secrets).
    - ``last_error``: alias for ``error`` (for consistency with spec).
    - ``failed_at``: alias for ``timestamp`` (for consistency with spec).
    - ``payload`` must be redacted before construction; this model does not
      perform redaction itself — callers must use Redactor first.
    """

    id: str = Field(default_factory=_new_id)
    webhook_id: str
    url: str
    event_type: str
    payload: dict[str, Any]
    error: str
    timestamp: str = Field(default_factory=_now_iso)
    # Phase 52 additions
    attempt_count: int = Field(default=1, ge=1, description="Number of delivery attempts made")
    payload_hash: str = Field(default="", description="SHA-256 of redacted payload")
    last_error: str = Field(default="", description="Last error message (same as error)")
    failed_at: str = Field(default="", description="Timestamp of final failure (same as timestamp)")

    def model_post_init(self, __context: Any) -> None:
        """Compute derived fields after construction."""
        # Compute payload hash if not provided
        if not self.payload_hash:
            object.__setattr__(self, "payload_hash", _payload_hash(self.payload))
        # Populate aliases
        if not self.last_error:
            object.__setattr__(self, "last_error", self.error)
        if not self.failed_at:
            object.__setattr__(self, "failed_at", self.timestamp)
