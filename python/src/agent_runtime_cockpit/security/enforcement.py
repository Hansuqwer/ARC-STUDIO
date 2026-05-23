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

from .context import EnforcementContext, DryRunAbort, get_enforcement_context
from .trust import TrustLevel, resolve_trust, TRUST_DB
from .profiles import RunProfile
from ._bypass_rate_limit import should_emit_warning, mark_warning_emitted
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
from ..protocol._bypass import (
    PolicyBypassWarning,
    PolicyBypassWarningData,
    PolicyBypassReason,
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
    ctx: Optional[EnforcementContext] = None,
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
        ctx: Optional enforcement context (uses global context if None)

    Raises:
        TrustEnforcementError: If the workspace is untrusted
        DryRunAbort: If dry-run mode is enabled
    """
    # Get enforcement context
    ctx = ctx or get_enforcement_context()

    # Dry-run branch: always denies, cannot be bypassed
    if ctx.dry_run:
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = TrustDenialData(
            action=action,
            workspace_path=str(workspace.resolve()),
            reason="dry_run",
            trust_level="unknown",
            required_trust_level="trusted",
            remediation="Remove --dry-run flag to execute this operation",
            correlation_id=correlation_id,
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

        # Raise DryRunAbort
        raise DryRunAbort(
            f"Dry-run: would check workspace trust for '{action}' in {workspace}",
            denial_event=denial_event.model_dump(by_alias=True),
        )

    # Bypass gate if trust_workspace flag is set
    if ctx.trust_workspace:
        return

    # Normal trust enforcement
    resolution = resolve_trust(workspace, trust_db=trust_db)

    if resolution.level == TrustLevel.UNTRUSTED:
        if allow_if_no_db and not trust_db.exists():
            return

        # Create typed denial event
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = TrustDenialData(
            action=action,
            workspace_path=str(workspace.resolve()),
            reason=resolution.reason,
            trust_level=resolution.level.value,
            required_trust_level="trusted",
            remediation="Run 'arc workspace trust' to mark this workspace as trusted",
            correlation_id=correlation_id,
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
    ctx: Optional[EnforcementContext] = None,
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
        ctx: Optional enforcement context (uses global context if None)

    Raises:
        PaidCallEnforcementError: If paid calls are not allowed
        DryRunAbort: If dry-run mode is enabled
    """
    # Get enforcement context
    ctx = ctx or get_enforcement_context()

    # Dry-run branch: always denies, cannot be bypassed
    if ctx.dry_run:
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = PaidCallDenialData(
            action=action,
            provider=provider,
            model=model,
            reason="dry_run",
            profile_id=profile.id,
            allow_paid_calls=False,
            remediation="Remove --dry-run flag to execute this operation",
            correlation_id=correlation_id,
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

        # Raise DryRunAbort
        raise DryRunAbort(
            f"Dry-run: would check paid-call gate for '{action}'",
            denial_event=denial_event.model_dump(by_alias=True),
        )

    # Bypass gate if allow_paid flag is set OR profile allows paid calls
    if ctx.allow_paid or profile.allow_paid_calls:
        return

    # If we get here, paid calls are not allowed
    # Create typed denial event
    correlation_id = EnforcementContext.generate_correlation_id()
    denial_data = PaidCallDenialData(
        action=action,
        provider=provider,
        model=model,
        reason=f"Profile '{profile.id}' does not allow paid calls",
        profile_id=profile.id,
        allow_paid_calls=False,
        remediation="Use --allow-paid flag or switch to a profile with allow_paid_calls=true",
        correlation_id=correlation_id,
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
    ctx: Optional[EnforcementContext] = None,
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
        ctx: Optional enforcement context (uses global context if None)

    Raises:
        ShellEnforcementError: If shell execution is not allowed
        DryRunAbort: If dry-run mode is enabled
    """
    # Get enforcement context
    ctx = ctx or get_enforcement_context()

    # Dry-run branch: always denies, cannot be bypassed
    if ctx.dry_run:
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = ShellDenialData(
            action=action,
            command=command,
            reason="dry_run",
            profile_id=profile.id,
            allow_shell=False,
            remediation="Remove --dry-run flag to execute this operation",
            correlation_id=correlation_id,
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

        # Raise DryRunAbort
        raise DryRunAbort(
            f"Dry-run: would check shell gate for '{action}'",
            denial_event=denial_event.model_dump(by_alias=True),
        )

    # Normal shell enforcement
    if not profile.allow_shell:
        # Create typed denial event
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = ShellDenialData(
            action=action,
            command=command,
            reason=f"Profile '{profile.id}' does not allow shell execution",
            profile_id=profile.id,
            allow_shell=False,
            remediation="Use a profile with allow_shell=true or get explicit approval",
            correlation_id=correlation_id,
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
    ctx: Optional[EnforcementContext] = None,
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
        ctx: Optional enforcement context (uses global context if None)

    Raises:
        NetworkEnforcementError: If network access is not allowed
        DryRunAbort: If dry-run mode is enabled
    """
    # Get enforcement context
    ctx = ctx or get_enforcement_context()

    # Dry-run branch: always denies, cannot be bypassed
    if ctx.dry_run:
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = NetworkDenialData(
            action=action,
            url=url,
            reason="dry_run",
            profile_id=profile.id,
            allow_network=False,
            remediation="Remove --dry-run flag to execute this operation",
            correlation_id=correlation_id,
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

        # Raise DryRunAbort
        raise DryRunAbort(
            f"Dry-run: would check network gate for '{action}'",
            denial_event=denial_event.model_dump(by_alias=True),
        )

    # Normal network enforcement
    if not profile.allow_network:
        # Create typed denial event
        correlation_id = EnforcementContext.generate_correlation_id()
        denial_data = NetworkDenialData(
            action=action,
            url=url,
            reason=f"Profile '{profile.id}' does not allow network access",
            profile_id=profile.id,
            allow_network=False,
            remediation="Use a profile with allow_network=true",
            correlation_id=correlation_id,
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


def emit_policy_bypass_warning(
    run_id: str,
    sequence: int,
    policy_id: str,
    bypass_reason: PolicyBypassReason,
    surface: str,
    surface_identifier: str,
    suggested_remediation: str,
    parent_run_id: Optional[str] = None,
    emit_event: Optional[EventEmitter] = None,
) -> bool:
    """
    Emit a policy bypass warning when enforcement cannot be applied.

    Unlike denial events, bypass warnings are non-blocking. They indicate that
    enforcement could not be applied due to architectural limitations (e.g.,
    custom HTTP client, uninstrumented tool).

    Rate-limited to one warning per (run_id, surface_identifier) combination
    to prevent warning spam when the same uninstrumented surface is called
    repeatedly.

    Args:
        run_id: Run ID for event emission
        sequence: Event sequence number
        policy_id: Policy that was bypassed (e.g., "trust_gate", "network_gate")
        bypass_reason: Reason code for the bypass
        surface: Surface type (e.g., "provider_call", "tool_execution")
        surface_identifier: Specific identifier (e.g., "custom_provider.execute")
        suggested_remediation: How to fix the bypass
        parent_run_id: Optional parent run ID
        emit_event: Optional callback to emit events (run_id, event_type, data)

    Returns:
        True if warning was emitted, False if suppressed by rate-limiting
    """
    # Check rate-limiting: only emit once per (run_id, surface_identifier)
    if not should_emit_warning(run_id, surface_identifier):
        return False

    # Create bypass warning event
    warning_data = PolicyBypassWarningData(
        policy_id=policy_id,
        bypass_reason=bypass_reason,
        surface=surface,
        surface_identifier=surface_identifier,
        suggested_remediation=suggested_remediation,
        parent_run_id=parent_run_id,
    )

    warning_event = PolicyBypassWarning(
        type="POLICY_BYPASS_WARNING",
        timestamp=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        run_id=run_id,
        sequence=sequence,
        data=warning_data,
    )

    # Emit event if callback provided
    if emit_event:
        emit_event(run_id, "POLICY_BYPASS_WARNING", warning_event.model_dump(by_alias=True))

    # Mark warning as emitted for rate-limiting
    mark_warning_emitted(run_id, surface_identifier)

    return True
