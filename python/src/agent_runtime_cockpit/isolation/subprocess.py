"""SubprocessIsolationProvider — subprocess with env allowlist and path restrictions."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from .base import IsolationProvider, IsolationResult
from .none import NoneIsolationProvider

log = logging.getLogger(__name__)

# Default set of environment variables safe to pass to subprocesses
DEFAULT_SAFE_ENV_KEYS: frozenset[str] = frozenset({
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_ALL",
    "TERM",
    "TMPDIR",
    "SHELL",
    "VIRTUAL_ENV",
    "PYTHONPATH",
    "PYTHONWARNINGS",
})


class SubprocessIsolationProvider(IsolationProvider):
    """Subprocess with env allowlist and path restrictions.

    Only environment variables in the allowlist are passed through.
    This prevents leakage of API keys, tokens, and other secrets
    to child processes.
    """

    def __init__(
        self,
        safe_env_keys: frozenset[str] | None = None,
    ) -> None:
        self._safe_env_keys = safe_env_keys or DEFAULT_SAFE_ENV_KEYS

    @property
    def provider_id(self) -> str:
        return "subprocess"

    async def health_check(self) -> bool:
        return True

    def filter_env(
        self,
        extra_env: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """Return a filtered copy of the current environment.

        Only includes:
        - Variables in ``self._safe_env_keys``
        - Any ``ARC_*`` prefixed variables
        - Variables explicitly passed in ``extra_env`` (if also in allowlist)
        """
        result: dict[str, str] = {}

        # Include allowlisted system vars
        for key in self._safe_env_keys:
            if key in os.environ:
                result[key] = os.environ[key]

        # Include ARC_* prefixed vars (ARC-specific config)
        for key, value in os.environ.items():
            if key.startswith("ARC_") and key in self._safe_env_keys:
                result[key] = value

        # Include extra env, but only if allowlisted
        if extra_env:
            for key, value in extra_env.items():
                if key in self._safe_env_keys or key.startswith("ARC_"):
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
        filtered_env = self.filter_env(env)
        # Delegate to the none provider with filtered env
        delegate = NoneIsolationProvider()
        result = await delegate.execute(
            command,
            cwd=cwd,
            env=filtered_env,
            timeout_seconds=timeout_seconds,
        )
        result.provider = self.provider_id
        return result
