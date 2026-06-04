"""Typed event for Capability Card enforcement decisions.

Mirrors the shape of denial_events.py. Schema version 2.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CapabilityCardDecisionData(BaseModel):
    """Data payload for CAPABILITY_CARD_DECISION event."""

    model_config = {"extra": "ignore"}

    action: str
    decision: Literal["allow", "deny", "warn"]
    reason: str
    card_id: str | None = None
    card_hash: str | None = None
    entity_type: str | None = None
    mode: Literal["off", "warn", "strict"]
    remediation: str = ""
    correlation_id: str | None = None
    details: dict[str, str] | None = None


class CapabilityCardDecisionEvent(BaseModel):
    """CAPABILITY_CARD_DECISION event emitted at adapter/MCP/SwarmGraph boundaries."""

    model_config = {"extra": "ignore"}

    schema_version: int = 2
    type: Literal["CAPABILITY_CARD_DECISION"]
    timestamp: str
    run_id: str
    sequence: int
    data: CapabilityCardDecisionData


__all__ = ["CapabilityCardDecisionData", "CapabilityCardDecisionEvent"]
