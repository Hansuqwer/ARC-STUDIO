"""MicroVM provider preflight/doctor support.

This provider intentionally does not execute commands yet. It only reports
whether host prerequisites exist for later macOS/Linux lightweight microVM work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..security.sandbox import microvm_preflight
from .base import IsolationProvider, IsolationResult


class MicroVMIsolationProvider(IsolationProvider):
    """Doctor-only microVM provider for macOS/Linux."""

    @property
    def provider_id(self) -> str:
        return "microvm"

    async def health_check(self) -> bool:
        return microvm_preflight()["status"] == "ready"

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        raise NotImplementedError("microVM execution is not implemented; use doctor/preflight only")

    def describe(self) -> dict[str, object]:
        return microvm_preflight()
