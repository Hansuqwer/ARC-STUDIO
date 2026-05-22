"""
Enforcement context for security gates (Phase 23.1).

Provides centralized context management for enforcement decisions across
trust, paid-call, shell, and network gates. Supports dry-run mode and
CLI flag overrides.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class EnforcementContext:
    """Context for enforcement decisions.

    Attributes:
        allow_paid: Bypass paid-call gate (from --allow-paid flag)
        trust_workspace: Bypass workspace trust gate (from --trust-workspace flag)
        dry_run: Deny all operations and log what would be denied (from --dry-run flag)
    """

    allow_paid: bool = False
    trust_workspace: bool = False
    dry_run: bool = False

    def copy_with(self, **kwargs) -> "EnforcementContext":
        """Create a copy with updated fields.

        Args:
            **kwargs: Fields to update (allow_paid, trust_workspace, dry_run)

        Returns:
            New EnforcementContext with updated fields
        """
        return EnforcementContext(
            allow_paid=kwargs.get("allow_paid", self.allow_paid),
            trust_workspace=kwargs.get("trust_workspace", self.trust_workspace),
            dry_run=kwargs.get("dry_run", self.dry_run),
        )

    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a unique correlation ID for tracking denial → retry flow.

        Returns:
            12-character hex string from UUID4
        """
        return uuid.uuid4().hex[:12]


class DryRunAbort(Exception):
    """Raised when dry-run mode blocks an operation.

    Dry-run mode always denies operations and emits denial events with
    dry_run=True. This exception is caught at the CLI boundary and exits
    with code 2.

    Attributes:
        message: Human-readable description of what was denied
        denial_event: Full denial event dict for logging/audit
    """

    def __init__(self, message: str, denial_event: dict):
        super().__init__(message)
        self.denial_event = denial_event


# Global context variable (thread-safe via contextvars)
_enforcement_context: ContextVar[EnforcementContext] = ContextVar(
    "enforcement_context", default=EnforcementContext()
)


def get_enforcement_context() -> EnforcementContext:
    """Get current enforcement context.

    Returns the context for the current execution context (thread/async task).
    If no context has been set, returns the default context (all flags False).

    Returns:
        Current EnforcementContext
    """
    return _enforcement_context.get()


def set_enforcement_context(ctx: EnforcementContext) -> None:
    """Set enforcement context for current execution.

    Sets the context for the current thread/async task. Worker threads
    should use copy_context() to inherit the parent context.

    Args:
        ctx: EnforcementContext to set
    """
    _enforcement_context.set(ctx)
