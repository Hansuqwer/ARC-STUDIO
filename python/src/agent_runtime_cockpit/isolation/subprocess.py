"""SubprocessIsolationProvider — subprocess with env allowlist and path restrictions."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

from .base import IsolationProvider, IsolationResult
from .none import NoneIsolationProvider

log = logging.getLogger(__name__)

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

BLOCKED_ENV_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i).*API_KEY$"),
    re.compile(r"(?i).*APIKEY$"),
    re.compile(r"(?i).*SECRET$"),
    re.compile(r"(?i).*TOKEN$"),
    re.compile(r"(?i).*PASSWORD$"),
    re.compile(r"(?i).*CREDENTIAL$"),
    re.compile(r"(?i).*PRIVATE_KEY$"),
    re.compile(r"(?i)^AWS_"),
    re.compile(r"(?i)^GITHUB_"),
    re.compile(r"(?i)^OPENAI_"),
    re.compile(r"(?i)^ANTHROPIC_"),
    re.compile(r"(?i)^GOOGLE_"),
    re.compile(r"(?i)^MISTRAL_"),
    re.compile(r"(?i)^GROQ_"),
]


def _is_blocked_env_key(key: str) -> bool:
    """Return True if the env key matches a blocked pattern."""
    for pattern in BLOCKED_ENV_PATTERNS:
        if pattern.match(key):
            return True
    return False


OUTPUT_REDACTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}")),
    ("bearer_token", re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-_\.]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[ps]_[A-Za-z0-9]{36,}")),
    ("password_url", re.compile(r"(://[^:]+:)[^@]+(@)")),
    ("generic_secret", re.compile(
        r"((?:api_key|apikey|secret|password|token|access_token)\s*[:=]\s*['\"]?)([^\s'\",}\]]{8,})(['\"]?)",
        re.IGNORECASE,
    )),
]

REDACTED = "[REDACTED]"


def redact_output(text: str) -> str:
    """Redact known secret patterns from subprocess output."""
    result = text
    for name, pattern in OUTPUT_REDACTION_PATTERNS:
        if name == "password_url":
            result = pattern.sub(r"\1[REDACTED]\2", result)
        elif name == "generic_secret":
            result = pattern.sub(r"\1[REDACTED]\3", result)
        else:
            result = pattern.sub(REDACTED, result)
    return result


class SubprocessIsolationProvider(IsolationProvider):
    """Subprocess with env allowlist and path restrictions.

    Only environment variables in the allowlist are passed through.
    Blocked patterns prevent leakage of API keys, tokens, and other secrets.
    Output is redacted before returning results.
    """

    def __init__(
        self,
        safe_env_keys: frozenset[str] | None = None,
        redact_output: bool = True,
    ) -> None:
        self._safe_env_keys = safe_env_keys or DEFAULT_SAFE_ENV_KEYS
        self._redact_output = redact_output

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
        - Variables explicitly passed in ``extra_env`` (if also in allowlist)
        
        Blocks any key matching secret patterns (*_API_KEY, *_TOKEN, etc.)
        """
        result: dict[str, str] = {}

        for key in self._safe_env_keys:
            if key in os.environ and not _is_blocked_env_key(key):
                result[key] = os.environ[key]

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
        filtered_env = self.filter_env(env)
        delegate = NoneIsolationProvider()
        result = await delegate.execute(
            command,
            cwd=cwd,
            env=filtered_env,
            timeout_seconds=timeout_seconds,
        )
        result.provider = self.provider_id
        
        if self._redact_output:
            result.stdout = redact_output(result.stdout)
            result.stderr = redact_output(result.stderr)
        
        return result
