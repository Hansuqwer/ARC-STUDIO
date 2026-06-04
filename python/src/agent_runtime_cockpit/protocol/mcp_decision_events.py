"""Typed event for MCP outbound call risk decisions.

Schema version 2. Mirrors CapabilityCardDecisionEvent pattern.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class McpCallDecisionData(BaseModel):
    """Data payload for MCP_CALL_DECISION event."""

    model_config = {"extra": "ignore"}

    server_id: str
    tool_name: str
    decision: Literal["allow", "deny", "warn"]
    risk_level: Literal["low", "medium", "high", "critical"]
    policy: Literal["strict", "permissive"]
    reason: str
    injection_severity: str | None = None
    manifest_risk: str | None = None
    roots_violation: bool = False
    drift: str | None = None
    correlation_id: str | None = None


class McpCallDecisionEvent(BaseModel):
    """MCP_CALL_DECISION event emitted when risk gate evaluates a tool call."""

    model_config = {"extra": "ignore"}

    schema_version: int = 2
    type: Literal["MCP_CALL_DECISION"]
    timestamp: str
    run_id: str
    sequence: int
    data: McpCallDecisionData


__all__ = ["McpCallDecisionData", "McpCallDecisionEvent"]
