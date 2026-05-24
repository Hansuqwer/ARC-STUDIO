"""Rate-limiting for policy bypass warnings (Phase 22.1).

Deduplicates bypass warnings per (run_id, surface_identifier) to prevent
warning spam when the same uninstrumented surface is called repeatedly.
"""

from __future__ import annotations

from contextvars import ContextVar

# Global contextvar to track emitted warnings per run
# Stores set of (run_id, surface_identifier) tuples that have been emitted
_emitted_warnings: ContextVar[set[tuple[str, str]]] = ContextVar("bypass_warning_dedup")


def _get_emitted_set() -> set[tuple[str, str]]:
    """Get the current set of emitted warnings, initializing if needed.

    Returns:
        Set of (run_id, surface_identifier) tuples that have been emitted

    """
    try:
        return _emitted_warnings.get()
    except LookupError:
        # Not set yet, initialize with empty set
        emitted: set[tuple[str, str]] = set()
        _emitted_warnings.set(emitted)
        return emitted


def should_emit_warning(run_id: str, surface_identifier: str) -> bool:
    """Check if a bypass warning should be emitted.

    Returns True if this is the first time we're warning about this
    (run_id, surface_identifier) combination in the current execution context.

    Args:
        run_id: Run ID for the current execution
        surface_identifier: Identifier for the uninstrumented surface

    Returns:
        True if warning should be emitted, False if already emitted

    """
    emitted = _get_emitted_set()
    key = (run_id, surface_identifier)
    return key not in emitted


def mark_warning_emitted(run_id: str, surface_identifier: str) -> None:
    """Mark a bypass warning as emitted.

    Adds the (run_id, surface_identifier) tuple to the dedup set so
    subsequent calls with the same combination will be suppressed.

    Args:
        run_id: Run ID for the current execution
        surface_identifier: Identifier for the uninstrumented surface

    """
    emitted = _get_emitted_set()
    key = (run_id, surface_identifier)
    emitted.add(key)


def reset_warning_state() -> None:
    """Reset the warning dedup state.

    Clears all tracked warnings. Useful for testing or when starting
    a new execution context.
    """
    _emitted_warnings.set(set())


def get_emitted_count() -> int:
    """Get the number of unique warnings emitted in the current context.

    Returns:
        Count of unique (run_id, surface_identifier) combinations emitted

    """
    return len(_get_emitted_set())
