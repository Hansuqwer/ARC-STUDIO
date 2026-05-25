"""Event-driven notification system (Phase 32 / R25).

Provides a local typed event bus, webhook delivery with HMAC signing,
and CLI watch mode for ARC events.

Event types:
  - hitl_required
  - hitl_decided
  - audit_verified
  - run_completed
  - run_failed
  - quota_warning
"""

from __future__ import annotations

from .bus import EventBus, get_bus, reset_bus, set_bus
from .types import (
    ArcEvent,
    AuditVerified,
    EVENT_TYPE_MAP,
    HitlDecided,
    HitlRequired,
    QuotaWarning,
    RunCompleted,
    RunFailed,
    parse_event,
)

__all__ = [
    "EventBus",
    "get_bus",
    "reset_bus",
    "set_bus",
    "ArcEvent",
    "HitlRequired",
    "HitlDecided",
    "AuditVerified",
    "RunCompleted",
    "RunFailed",
    "QuotaWarning",
    "EVENT_TYPE_MAP",
    "parse_event",
]
