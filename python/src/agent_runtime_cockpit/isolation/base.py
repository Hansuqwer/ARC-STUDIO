"""
Isolation provider protocol — abstract interface for execution boundary control.

Each provider implements a different isolation strategy:
  - ``none``: direct subprocess execution (trusted workspace only)
  - ``subprocess``: subprocess with env allowlist and path restrictions
  - ``docker``: Docker-compatible container isolation (future, P2+)

See ADR-006 for the full isolation provider design.
"""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class IsolationResult(BaseModel):
    """Result of an isolated command execution."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    pid: Optional[int] = None
    killed: bool = False
    kill_reason: Optional[str] = None
    provider: str = "unknown"


class IsolationProvider(abc.ABC):
    """Abstract interface for execution isolation backends."""

    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this isolation provider (e.g. 'none', 'subprocess')."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return True if this isolation provider is available and healthy."""
        ...

    @abc.abstractmethod
    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        """Execute a command under this isolation boundary."""
        ...

    def describe(self) -> dict[str, object]:
        """Human-readable description of this provider's capabilities."""
        return {
            "provider_id": self.provider_id,
            "available": True,
        }
