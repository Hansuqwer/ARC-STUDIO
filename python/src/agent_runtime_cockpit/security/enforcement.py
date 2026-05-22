"""
Centralized enforcement helpers for trust and paid-call gates (Phase 23).

Provides enforcement functions that emit typed denial events (Phase 22) when
actions are blocked by security policies. Integrates with existing trust.py
and profiles.py infrastructure.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Callable, Optional

from .trust import TrustLevel, resolve_trust, TRUST_DB
from .profiles import RunProfile
from ..protocol.denial_events import (
    TrustDeniedEvent,
    TrustDenialData,
    PaidCallDeniedEvent,
    PaidCallDenialData,
    ShellDeniedEvent,
    ShellDenialData,
    NetworkDeniedEvent,
    NetworkDenialData,
)


# Type alias for event emission callback
EventEmitter = Callable[[str, str, dict], None]


class EnforcementError(Exception):
    """Base exception for enforcement failures."""

    def __init__(self, message: str, denial_event: dict | None = None):
        super().__init__(message)
        self.denial_event = denial_event


class TrustEnforcementError(EnforcementError):
    """Raised when trust enforcement blocks an action."""


class PaidCallEnforcementError(EnforcementError):
    """Raised when paid-call gate blocks an action."""


class ShellEnforcementError(EnforcementError):
    """Raised when shell execution is blocked."""


class NetworkEnforcementError(EnforcementError):
    """Raised when network access is blocked."""


def enforce_workspace_trust(
    workspace: Path,
    action: str,
    run_id: str,
    sequence: int,
    emit_event: Optional[EventEmitter] = None,
    trust_db: Path = TRUST_DB,
    allow_if_no_db: bool = False,
) -> None:
    """
    Enforce workspace trust before allowing an action.

    Emits TRUST_DENIED event if the workspace is untrusted.

    Args:
        workspace: Path to the workspace to check
        action: Description of the action being blocked (e.g., "run_execution")
        run_id: Run ID for event emission
        sequence: Event sequence number
        emit_event: Optional callback to emit events (run_id, event_type, data)
        trust_db: Path to the external trust database
        allow_if_no_db: If True, allow execution when no trust DB exists

    Raises:
        TrustEnforcementError: If the workspace is untrusted
    """
    resolution = resolve_trust(workspace, trust_db=trust_db)

    if resolution.level == TrustLevel.UNTRUSTED:
        if allow_if_no_db and not trust_db.exists():
            return

        # Create typed denial event
        denial_data = TrustDenialData(
            action=action,
            workspace_path=str(workspace.resolve()),
            reason=resolution.reason,
            trust_level=resolution.level.value,
            required_trust_level="trusted",
            remediation="Run 'arc workspace trust' to mark this workspace as trusted",
        )

        denial_event = TrustDeniedEvent(
            type="TRUST_DENIED",
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            run_id=run_id,
            sequence=sequence,
            data=denial_data,
        )

        # Emit event if callback provided
        if emit_event:
            emit_event(run_id, "TRUST_DENIED", denial_event.model_dump(by_alias=True))

        # Raise enforcement error
        raise TrustEnforcementError(
            f"Workspace '{workspace}' is untrusted: {resolution.reason}. "
            f"Run 'arc workspace trust' to approve this workspace.",
            denial_event=denial_event.model_dump(by_alias=True),
        )


def enforce_paid_call_gate(
    profile: RunProfile,
    action: str,
    run_id: str,
    sequence: int,
    emit_event: Optional[EventEmitter] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Enforce paid-call gate before allowing provider calls.

    Emits PAID_CALL_DENIED event if the profile doesn't allow paid calls.

    Args:
        profile: Run profile with permission settings
        action: Description of the action being blocked (e.g., "provider_call")
        run_id: Run ID for event emission
        sequence: Event sequence number
        emit_event: Optional callback to emit events
        provider: Optional provider name for context
        model: Optional model name for context

    Raises:
        PaidCallEnforcementError: If paid calls are not allowed
    """
    if not profile.allow_paid_calls:
        # Create typed denial event
        denial_data = PaidCallDenialData(
            action=action,
            provider=provider,
            model=model,
            reason=f"Profile '{profile.id}' does not allow paid calls",
            profile_id=profile.id,
            allow_paid_calls=False,
            remediation="Use --allow-paid flag or switch to a profile with allow_paid_calls=true",
        )

        denial_event = PaidCallDeniedEvent(
            type="PAID_CALL_DENIED",
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            run_id=run_id,
            sequence=sequence,
            data=denial_data,
        )

        # Emit event if callback provided
        if emit_event:
            emit_event(run_id, "PAID_CALL_DENIED", denial_event.model_dump(by_alias=True))

        # Raise enforcement error
        raise PaidCallEnforcementError(
            f"Paid calls not allowed by profile '{profile.id}'. "
            f"Use --allow-paid flag or switch to a profile with allow_paid_calls=true.",
            denial_event=denial_event.model_dump(by_alias=True),
        )


def enforce_shell_gate(
    profile: RunProfile,
    action: str,
    run_id: str,
    sequence: int,
    emit_event: Optional[EventEmitter] = None,
    command: Optional[str] = None,
) -> None:
    """
    Enforce shell execution gate before allowing shell commands.

    Emits SHELL_DENIED event if the profile doesn't allow shell execution.

    Args:
        profile: Run profile with permission settings
        action: Description of the action being blocked (e.g., "shell_command")
        run_id: Run ID for event emission
        sequence: Event sequence number
        emit_event: Optional callback to emit events
        command: Optional command string for context

    Raises:
        ShellEnforcementError: If shell execution is not allowed
    """
    if not profile.allow_shell:
        # Create typed denial event
        denial_data = ShellDenialData(
            action=action,
            command=command,
            reason=f"Profile '{profile.id}' does not allow shell execution",
            profile_id=profile.id,
            allow_shell=False,
            remediation="Use a profile with allow_shell=true or get explicit approval",
        )

        denial_event = ShellDeniedEvent(
            type="SHELL_DENIED",
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            run_id=run_id,
            sequence=sequence,
            data=denial_data,
        )

        # Emit event if callback provided
        if emit_event:
            emit_event(run_id, "SHELL_DENIED", denial_event.model_dump(by_alias=True))

        # Raise enforcement error
        raise ShellEnforcementError(
            f"Shell execution not allowed by profile '{profile.id}'. "
            f"Use a profile with allow_shell=true.",
            denial_event=denial_event.model_dump(by_alias=True),
        )


def enforce_network_gate(
    profile: RunProfile,
    action: str,
    run_id: str,
    sequence: int,
    emit_event: Optional[EventEmitter] = None,
    url: Optional[str] = None,
) -> None:
    """
    Enforce network access gate before allowing network operations.

    Emits NETWORK_DENIED event if the profile doesn't allow network access.

    Args:
        profile: Run profile with permission settings
        action: Description of the action being blocked (e.g., "http_request")
        run_id: Run ID for event emission
        sequence: Event sequence number
        emit_event: Optional callback to emit events
        url: Optional URL for context

    Raises:
        NetworkEnforcementError: If network access is not allowed
    """
    if not profile.allow_network:
        # Create typed denial event
        denial_data = NetworkDenialData(
            action=action,
            url=url,
            reason=f"Profile '{profile.id}' does not allow network access",
            profile_id=profile.id,
            allow_network=False,
            remediation="Use a profile with allow_network=true",
        )

        denial_event = NetworkDeniedEvent(
            type="NETWORK_DENIED",
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            run_id=run_id,
            sequence=sequence,
            data=denial_data,
        )

        # Emit event if callback provided
        if emit_event:
            emit_event(run_id, "NETWORK_DENIED", denial_event.model_dump(by_alias=True))

        # Raise enforcement error
        raise NetworkEnforcementError(
            f"Network access not allowed by profile '{profile.id}'. "
            f"Use a profile with allow_network=true.",
            denial_event=denial_event.model_dump(by_alias=True),
        )
