"""NoneIsolationProvider — direct subprocess execution with no isolation."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import IsolationProvider, IsolationResult
from .subprocess import (
    DEFAULT_SAFE_ENV_KEYS,
    _BoundedPipeReader,
    _is_blocked_env_key,
    redact_output,
)

log = logging.getLogger(__name__)


class NoneIsolationProvider(IsolationProvider):
    """No isolation — direct subprocess execution (trusted workspaces only)."""

    def __init__(
        self,
        *,
        safe_env_keys: frozenset[str] | None = None,
        workspace_root: Path | None = None,
        max_output_bytes: int = 65_536,
        redact: bool = True,
    ) -> None:
        self._safe_env_keys = safe_env_keys or DEFAULT_SAFE_ENV_KEYS
        self._workspace_root = workspace_root
        self._max_output_bytes = max_output_bytes
        self._redact = redact

    @property
    def provider_id(self) -> str:
        return "none"

    async def health_check(self) -> bool:
        return True

    def describe(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "available": True,
            "security_posture": "diagnostics_only_no_isolation",
            "user_selectable": False,
        }

    def filter_env(self, extra_env: Optional[dict[str, str]] = None) -> dict[str, str]:
        result = {
            key: os.environ[key]
            for key in self._safe_env_keys
            if key in os.environ and not _is_blocked_env_key(key)
        }
        if extra_env:
            for key, value in extra_env.items():
                if key in self._safe_env_keys and not _is_blocked_env_key(key):
                    result[key] = value
        return result

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        popen_cwd = cwd
        if self._workspace_root and cwd:
            root = self._workspace_root.resolve()
            resolved = cwd.resolve()
            if cwd.is_symlink() or not resolved.is_relative_to(root):
                raise ValueError(f"cwd escapes workspace: {cwd}")
            # Run the resolved path (mirrors SubprocessIsolationProvider) so the
            # process cannot be steered through a symlinked parent component
            # between the check and the exec.
            popen_cwd = resolved
        filtered_env = self.filter_env(env)
        start = time.monotonic()
        proc = subprocess.Popen(
            command,
            cwd=str(popen_cwd) if popen_cwd else None,
            env=filtered_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        assert proc.stdout is not None
        assert proc.stderr is not None
        stdout_reader = _BoundedPipeReader(proc.stdout, self._max_output_bytes)
        stderr_reader = _BoundedPipeReader(proc.stderr, self._max_output_bytes)
        stdout_reader.start()
        stderr_reader.start()
        try:
            proc.wait(timeout=timeout_seconds)
            duration = int((time.monotonic() - start) * 1000)
            stdout_reader.join()
            stderr_reader.join()
            stdout = stdout_reader.text()
            stderr = stderr_reader.text()
            redacted_stdout = redact_output(stdout) if self._redact else stdout
            redacted_stderr = redact_output(stderr) if self._redact else stderr
            return IsolationResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout=redacted_stdout,
                stderr=redacted_stderr,
                duration_ms=duration,
                pid=proc.pid,
                provider=self.provider_id,
                stdout_truncated=stdout_reader.truncated,
                stderr_truncated=stderr_reader.truncated,
                redaction_applied=redacted_stdout != stdout or redacted_stderr != stderr,
            )
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            proc.wait()
            stdout_reader.join()
            stderr_reader.join()
            duration = int((time.monotonic() - start) * 1000)
            stdout = stdout_reader.text()
            stderr = stderr_reader.text()
            redacted_stdout = redact_output(stdout) if self._redact else stdout
            redacted_stderr = redact_output(stderr) if self._redact else stderr
            return IsolationResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout=redacted_stdout,
                stderr=redacted_stderr,
                duration_ms=duration,
                pid=proc.pid,
                killed=True,
                kill_reason="timeout",
                provider=self.provider_id,
                stdout_truncated=stdout_reader.truncated,
                stderr_truncated=stderr_reader.truncated,
                redaction_applied=redacted_stdout != stdout or redacted_stderr != stderr,
            )
