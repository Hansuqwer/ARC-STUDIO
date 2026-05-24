"""ARC Redactor — strips secrets from ARC outputs before sending to frontend.

Never allow: API keys, tokens, passwords, private keys to reach the IDE.
"""

from __future__ import annotations

import re
from typing import Any

# Patterns that must be redacted
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("api_key", re.compile(r'(?i)(api[-_]?key|apikey)\s*[=:]\s*["\']?[\w\-]{10,}["\']?')),
    ("auth_token", re.compile(r"(?i)(auth[-_]?token|bearer\s+[\w\-\.]{10,})")),
    ("password", re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?.{4,}["\']?')),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{32,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-]{10,}")),
]

REDACT_PLACEHOLDER = "[REDACTED]"


class Redactor:
    """Redact secrets from strings and dicts before they reach the frontend."""

    def redact_string(self, text: str) -> str:
        for name, pattern in SECRET_PATTERNS:
            text = pattern.sub(REDACT_PLACEHOLDER, text)
        return text

    def redact_dict(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self.redact_value(k, v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.redact_dict(item) for item in data]
        if isinstance(data, str):
            return self.redact_string(data)
        return data

    def redact_value(self, key: str, value: Any) -> Any:
        # Redact by key name
        if any(
            secret in key.lower()
            for secret in ("key", "token", "password", "secret", "credential", "auth")
        ):
            if isinstance(value, str) and value:
                return REDACT_PLACEHOLDER
        return self.redact_dict(value)

    def is_safe(self, text: str) -> bool:
        """Return True if text contains no detectable secrets."""
        return not any(pattern.search(text) for _, pattern in SECRET_PATTERNS)
