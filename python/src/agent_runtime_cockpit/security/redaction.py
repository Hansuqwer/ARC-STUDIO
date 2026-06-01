"""ARC Redactor — strips secrets from ARC outputs before sending to frontend.

Never allow: API keys, tokens, passwords, private keys to reach the IDE.
"""

from __future__ import annotations

import re
from typing import Any

# Canonical secret-redaction patterns.
#
# This is the SINGLE source of truth for secret detection across ARC. Both the
# frontend ``Redactor`` and subprocess output redaction (``isolation.subprocess``)
# import from here so a secret redacted in one path is never leaked by another.
#
# Order matters: provider-prefixed keys (sk-ant- before sk-) are listed first so
# the more specific token is replaced before a broader pattern can partially match.
#
# Note: anthropic_key must precede openai_key because ``sk-ant-...`` also matches
# the broader ``sk-...`` pattern.
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}")),
    # OpenAI keys are >=20 chars (sk-proj-, sk-svcacct-, classic sk-...).
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{32,}")),
    # Bearer tokens with whitespace separator (Authorization headers, logs).
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}")),
    # user:pass@host credential leak in URLs.
    ("password_url", re.compile(r"(://[^:/\s]+:)[^@/\s]+(@)")),
    ("api_key", re.compile(r'(?i)(api[-_]?key|apikey)\s*[=:]\s*["\']?[\w\-]{10,}["\']?')),
    ("auth_token", re.compile(r"(?i)auth[-_]?token\s*[=:]\s*[\"']?[\w\-\.]{10,}[\"']?")),
    ("password", re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?.{4,}["\']?')),
    # Generic key=value secret assignment.
    (
        "generic_secret",
        re.compile(
            r"(?i)((?:secret|token|access_token)\s*[:=]\s*['\"]?)([^\s'\",}\]]{8,})(['\"]?)"
        ),
    ),
]

# Patterns that use capture groups to preserve surrounding context. Mapped to
# the substitution template so a single redactor can apply them correctly.
_SUBSTITUTION_TEMPLATES: dict[str, str] = {
    "password_url": r"\1[REDACTED]\2",
    "generic_secret": r"\1[REDACTED]\3",
}

REDACT_PLACEHOLDER = "[REDACTED]"


def redact_secrets(text: str) -> str:
    """Apply the canonical secret patterns to ``text``.

    Single shared implementation used by both the frontend ``Redactor`` and
    subprocess output redaction so detection coverage is identical everywhere.
    """
    result = text
    for name, pattern in SECRET_PATTERNS:
        template = _SUBSTITUTION_TEMPLATES.get(name)
        if template is not None:
            result = pattern.sub(template, result)
        else:
            result = pattern.sub(REDACT_PLACEHOLDER, result)
    return result


class Redactor:
    """Redact secrets from strings and dicts before they reach the frontend."""

    def redact_string(self, text: str) -> str:
        return redact_secrets(text)

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
