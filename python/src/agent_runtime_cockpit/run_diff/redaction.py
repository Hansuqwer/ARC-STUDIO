"""Redaction utilities for Run Diff / Time Travel."""

from __future__ import annotations

from typing import Any

# Import canonical patterns from security.redaction (single source of truth)
try:
    from agent_runtime_cockpit.security.redaction import (
        SECRET_PATTERNS as _SECRET_PATTERNS_IMPORTED,
        REDACT_PLACEHOLDER as _PLACEHOLDER_IMPORTED,
    )

    _SECRET_PATTERNS_LIST = _SECRET_PATTERNS_IMPORTED
    REDACT_PLACEHOLDER = _PLACEHOLDER_IMPORTED
except Exception:
    _SECRET_PATTERNS_LIST = []
    REDACT_PLACEHOLDER = "[REDACTED]"

SECRET_PATTERNS = _SECRET_PATTERNS_LIST

_ALWAYS_REDACT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "password",
        "token",
        "access_token",
        "auth_token",
        "bearer_token",
        "private_key",
        "credential",
        "key",
        "passphrase",
        "aws_key",
        "github_token",
        "anthropic_key",
        "openai_key",
    }
)


def _should_redact_key(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in _ALWAYS_REDACT_KEYS)


def redact_value(key: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if _should_redact_key(key) and value and value != REDACT_PLACEHOLDER:
        return REDACT_PLACEHOLDER
    return value


def redact_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    result = text
    for name, pattern in SECRET_PATTERNS:
        if name == "password_url":
            result = pattern.sub(r"\1[REDACTED]\2", result)
        elif name == "generic_secret":
            result = pattern.sub(r"\1[REDACTED]\3", result)
        else:
            result = pattern.sub(REDACT_PLACEHOLDER, result)
    return result


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact secrets from a dict. Handles nested dicts/lists."""
    if not isinstance(data, dict):
        return data
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = redact_dict(v)
        elif isinstance(v, list):
            result[k] = [
                redact_dict(item) if isinstance(item, dict) else redact_value(k, item) for item in v
            ]
        else:
            result[k] = redact_value(k, v)
    return result


def redact_report(report: dict[str, Any]) -> dict[str, Any]:
    """Redact all secrets from a RunDiffReport dict before display/export.

    Handles nested dicts, lists, and string values recursively.
    """
    if not isinstance(report, dict):
        return report
    result: dict[str, Any] = {}
    for k, v in report.items():
        if isinstance(v, str):
            result[k] = redact_text(v)
        elif isinstance(v, dict):
            result[k] = redact_dict(v)
        elif isinstance(v, list):
            result[k] = [
                redact_dict(item)
                if isinstance(item, dict)
                else redact_text(item)
                if isinstance(item, str)
                else item
                for item in v
            ]
        else:
            result[k] = v
    return result


def is_safe(text: str) -> bool:
    if not isinstance(text, str):
        return True
    return not any(pattern.search(text) for _, pattern in SECRET_PATTERNS)
