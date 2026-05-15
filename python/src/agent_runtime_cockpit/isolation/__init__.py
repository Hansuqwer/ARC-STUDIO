"""Isolation providers — execution boundary abstraction (ADR-006)."""
from .base import IsolationProvider, IsolationResult
from .none import NoneIsolationProvider
from .subprocess import SubprocessIsolationProvider

__all__ = [
    "IsolationProvider",
    "IsolationResult",
    "NoneIsolationProvider",
    "SubprocessIsolationProvider",
]
