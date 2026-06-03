"""Redaction helpers for observability export.

Wraps security/redaction.py. Fail-closed: if redaction raises, returns
a safe placeholder. Never returns raw secrets.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import RedactionSummary

log = logging.getLogger(__name__)

_REDACTED = "[REDACTED]"
_SECRET_KEY_SUBSTRINGS = (
    "key",
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "auth",
    "bearer",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private",
    "access_token",
    "refresh_token",
)


def _is_secret_key(key: str) -> bool:
    lk = key.lower().replace("-", "_")
    return any(s in lk for s in _SECRET_KEY_SUBSTRINGS)


def redact_value(value: Any, key: str = "") -> tuple[Any, int]:
    """Redact a single value. Returns (redacted_value, tokens_removed)."""
    from ..security.redaction import Redactor

    redactor = Redactor()

    if _is_secret_key(key) and isinstance(value, str) and value:
        return _REDACTED, 1

    if isinstance(value, str):
        try:
            if not redactor.is_safe(value):
                return _REDACTED, 1
        except Exception:
            return _REDACTED, 1
        return value, 0

    if isinstance(value, dict):
        result, count = redact_dict(value)
        return result, count

    if isinstance(value, list):
        result, count = redact_list(value)
        return result, count

    return value, 0


def redact_dict(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Recursively redact a dict. Returns (redacted_dict, total_tokens_removed)."""
    out: dict[str, Any] = {}
    total = 0
    for k, v in data.items():
        rv, n = redact_value(v, key=k)
        out[k] = rv
        total += n
    return out, total


def redact_list(lst: list[Any]) -> tuple[list[Any], int]:
    out = []
    total = 0
    for item in lst:
        rv, n = redact_value(item)
        out.append(rv)
        total += n
    return out, total


def redact_attributes(attrs: dict[str, Any]) -> tuple[dict[str, Any], int]:
    return redact_dict(attrs)


def build_redaction_summary(tokens: int, fields: int = 0) -> RedactionSummary:
    return RedactionSummary(tokens_redacted=tokens, fields_redacted=fields)
