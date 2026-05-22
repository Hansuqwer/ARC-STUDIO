"""
Typed denial event types for trust and paid-call enforcement (Phase 23).

Uses Phase 22 discriminated union foundation to provide type-safe denial events
when actions are blocked by trust or paid-call gates.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel

from .typed_events import RunEventBase


# ─── Trust Denial Events ─────────────────────────────────────────────────────


class TrustDenialData(BaseModel):
    """Data payload for TRUST_DENIED event."""

    action: str  # What action was blocked (e.g., "run_execution", "provider_call", "mcp_start")
    workspace_path: str
    reason: str
    trust_level: str  # "untrusted", "partial", "trusted"
    required_trust_level: str = "trusted"
    remediation: str = "Run 'arc workspace trust' to mark this workspace as trusted"
    correlation_id: str | None = None  # For tracking denial → retry flow


class TrustDeniedEvent(BaseModel):
    """TRUST_DENIED event when workspace trust blocks an action."""

    schema_version: int = 2
    type: Literal["TRUST_DENIED"]
    timestamp: str
    run_id: str
    sequence: int
    data: TrustDenialData


# ─── Paid Call Denial Events ─────────────────────────────────────────────────


class PaidCallDenialData(BaseModel):
    """Data payload for PAID_CALL_DENIED event."""

    action: str  # What action was blocked (e.g., "provider_call", "model_invocation")
    provider: str | None = None
    model: str | None = None
    reason: str
    profile_id: str
    allow_paid_calls: bool = False
    remediation: str = "Use --allow-paid flag or switch to a profile with allow_paid_calls=true"
    correlation_id: str | None = None  # For tracking denial → retry flow


class PaidCallDeniedEvent(BaseModel):
    """PAID_CALL_DENIED event when paid-call gate blocks an action."""

    schema_version: int = 2
    type: Literal["PAID_CALL_DENIED"]
    timestamp: str
    run_id: str
    sequence: int
    data: PaidCallDenialData


# ─── Shell Execution Denial Events ───────────────────────────────────────────


class ShellDenialData(BaseModel):
    """Data payload for SHELL_DENIED event."""

    action: str  # What action was blocked (e.g., "shell_command", "subprocess_spawn")
    command: str | None = None
    reason: str
    profile_id: str
    allow_shell: bool = False
    remediation: str = "Use a profile with allow_shell=true or get explicit approval"
    correlation_id: str | None = None  # For tracking denial → retry flow


class ShellDeniedEvent(BaseModel):
    """SHELL_DENIED event when shell execution is blocked."""

    schema_version: int = 2
    type: Literal["SHELL_DENIED"]
    timestamp: str
    run_id: str
    sequence: int
    data: ShellDenialData


# ─── Network Access Denial Events ────────────────────────────────────────────


class NetworkDenialData(BaseModel):
    """Data payload for NETWORK_DENIED event."""

    action: str  # What action was blocked (e.g., "http_request", "websocket_connect")
    url: str | None = None
    reason: str
    profile_id: str
    allow_network: bool = False
    remediation: str = "Use a profile with allow_network=true"
    correlation_id: str | None = None  # For tracking denial → retry flow


class NetworkDeniedEvent(BaseModel):
    """NETWORK_DENIED event when network access is blocked."""

    schema_version: int = 2
    type: Literal["NETWORK_DENIED"]
    timestamp: str
    run_id: str
    sequence: int
    data: NetworkDenialData


# ─── Generic Permission Denial Event ─────────────────────────────────────────


class PermissionDenialData(BaseModel):
    """Data payload for PERMISSION_DENIED event (generic fallback)."""

    action: str
    reason: str
    permission_type: str  # "trust", "paid_call", "shell", "network", "secrets", "other"
    context: dict[str, str] | None = None
    remediation: str | None = None
    correlation_id: str | None = None  # For tracking denial → retry flow


class PermissionDeniedEvent(BaseModel):
    """PERMISSION_DENIED event for generic permission failures."""

    schema_version: int = 2
    type: Literal["PERMISSION_DENIED"]
    timestamp: str
    run_id: str
    sequence: int
    data: PermissionDenialData


# ─── Type Guards ─────────────────────────────────────────────────────────────


def is_trust_denied(event: RunEventBase) -> bool:
    """Type guard for TRUST_DENIED events."""
    return event.type == "TRUST_DENIED"


def is_paid_call_denied(event: RunEventBase) -> bool:
    """Type guard for PAID_CALL_DENIED events."""
    return event.type == "PAID_CALL_DENIED"


def is_shell_denied(event: RunEventBase) -> bool:
    """Type guard for SHELL_DENIED events."""
    return event.type == "SHELL_DENIED"


def is_permission_denied(event: RunEventBase) -> bool:
    """Type guard for any permission denial event."""
    return event.type in {
        "TRUST_DENIED",
        "PAID_CALL_DENIED",
        "SHELL_DENIED",
        "NETWORK_DENIED",
        "PERMISSION_DENIED",
    }
