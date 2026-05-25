"""Pydantic models for webhook configuration (Phase 32 / R25)."""

from __future__ import annotations

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


class DeadLetterEntry(BaseModel):
    id: str = Field(default_factory=_new_id)
    webhook_id: str
    url: str
    event_type: str
    payload: dict[str, Any]
    error: str
    timestamp: str = Field(default_factory=_now_iso)
