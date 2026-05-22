"""NoneIsolationProvider — direct subprocess execution with no isolation."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from .base import IsolationProvider, IsolationResult

log = logging.getLogger(__name__)


class NoneIsolationProvider(IsolationProvider):
    """No isolation — direct subprocess execution (trusted workspaces only)."""

    @property
    def provider_id(self) -> str:
        return "none"

    async def health_check(self) -> bool:
        return True

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd else None,
            env=env,
            # enforcement: not-applicable - TODO: Add shell gate in future PR
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=duration,
                pid=proc.pid,
                provider=self.provider_id,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            stdout, stderr = await proc.communicate()
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=duration,
                pid=proc.pid,
                killed=True,
                kill_reason="timeout",
                provider=self.provider_id,
            )
