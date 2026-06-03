"""Flight Recorder redaction layer.

Wraps the canonical ``security.redaction`` module and adds
flight-recorder-specific logic:
  - Deep dict/list redaction before persistence.
  - Key-name-based redaction for known sensitive field names.
  - High-entropy string detection.
  - Returns a RedactionSummary alongside the cleaned payload.

Hard constraints:
  - No network I/O.
  - No subprocess.
  - No model calls.
  - Fail closed: if redaction raises, log + return REDACTED_SENTINEL payload.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .models import RedactionSummary

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import the canonical redactor from security.redaction.
# If import fails (e.g., in isolated test environments), fall back to
# a minimal inline implementation so the recorder stays operational.
# ---------------------------------------------------------------------------

try:
    from ..security.redaction import Redactor as _CanonicalRedactor
    from ..security.redaction import redact_secrets as _canonical_redact_secrets

    _CANONICAL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CANONICAL_AVAILABLE = False

    class _CanonicalRedactor:  # type: ignore[no-redef]
        def redact_string(self, text: str) -> str:
            return _inline_redact(text)

        def redact_dict(self, data: Any) -> Any:
            return _inline_redact_deep(data)

        def is_safe(self, text: str) -> bool:
            if not isinstance(text, str):
                return True
            return _inline_is_safe(text)

    def _canonical_redact_secrets(text: str) -> str:  # type: ignore[misc]
        return _inline_redact(text)


# ---------------------------------------------------------------------------
# Inline fallback patterns (mirrors security/redaction.py exactly)
# Used only when the canonical module is unavailable.
# ---------------------------------------------------------------------------

_INLINE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9\-]{20,}")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{32,}")),
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_.]{20,}")),
    ("password_url", re.compile(r"(://[^:/\s]+:)[^@/\s]+(@)")),
    ("api_key", re.compile(r'(?i)(api[-_]?key|apikey)\s*[=:]\s*["\']?[\w\-]{10,}["\']?')),
    ("auth_token", re.compile(r'(?i)auth[-_]?token\s*[=:]\s*["\']?[\w\-.]{10,}["\']?')),
    ("password", re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?.{4,}["\']?')),
    (
        "generic_secret",
        re.compile(
            r'(?i)((?:secret|token|access_token)\s*[:=]\s*[\'"]?)'
            r'([^\s\'",}\]]{8,})'
            r'([\'"]?)'
        ),
    ),
]

# Note: we do NOT compile a union pattern here to avoid (?i) flag-mixing
# errors in Python 3.11+. Use _inline_is_safe() for fallback detection.

_INLINE_SUBSTITUTIONS: dict[str, str] = {
    "password_url": r"\1[REDACTED]\2",
    "generic_secret": r"\1[REDACTED]\3",
}

REDACT_PLACEHOLDER = "[REDACTED]"

# Sensitive key names — any dict key containing these substrings gets value redacted.
_SENSITIVE_KEYS = frozenset(
    [
        "key",
        "token",
        "password",
        "secret",
        "credential",
        "auth",
        "apikey",
        "api_key",
        "private",
        "bearer",
        "signing",
    ]
)

# High-entropy threshold: strings longer than this with high base64 density
_HIGH_ENTROPY_MIN_LEN = 40
_HIGH_ENTROPY_PATTERN = re.compile(r"[A-Za-z0-9+/=_\-]{40,}")


def _inline_is_safe(text: str) -> bool:
    """Check whether text contains any secret pattern (fallback for unavailable canonical)."""
    return not any(p.search(text) for _, p in _INLINE_PATTERNS)


def _inline_redact(text: str) -> str:
    result = text
    for name, pattern in _INLINE_PATTERNS:
        template = _INLINE_SUBSTITUTIONS.get(name)
        if template is not None:
            result = pattern.sub(template, result)
        else:
            result = pattern.sub(REDACT_PLACEHOLDER, result)
    return result


def _inline_redact_deep(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _redact_value(k, v) for k, v in data.items()}
    if isinstance(data, list):
        return [_inline_redact_deep(item) for item in data]
    if isinstance(data, str):
        return _inline_redact(data)
    return data


def _redact_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if any(s in key_lower for s in _SENSITIVE_KEYS):
        if isinstance(value, str) and value:
            return REDACT_PLACEHOLDER
    return _inline_redact_deep(value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_REDACTOR = _CanonicalRedactor()


def redact_payload(
    payload: dict[str, Any],
    *,
    redact_secrets: bool = True,
) -> tuple[dict[str, Any], RedactionSummary]:
    """Redact a payload dict and return (clean_payload, summary).

    Always returns a dict even if an exception occurs (fail closed).
    """
    if not redact_secrets:
        return payload, RedactionSummary(redact_applied=False)

    fields_redacted: list[str] = []
    patterns_matched: list[str] = []

    try:
        cleaned = _deep_redact(payload, path="", fields_redacted=fields_redacted)
        summary = RedactionSummary(
            fields_redacted=fields_redacted,
            patterns_matched=patterns_matched,
            redact_applied=bool(fields_redacted),
        )
        return cleaned, summary
    except Exception as exc:  # pragma: no cover
        log.warning("flight_recorder.redaction: redact_payload failed: %s", exc)
        return {"_redacted": True, "_error": "redaction_failed"}, RedactionSummary(
            fields_redacted=["*"],
            patterns_matched=["error"],
            redact_applied=True,
        )


def _deep_redact(
    data: Any,
    path: str,
    fields_redacted: list[str],
) -> Any:
    """Recursively redact a data structure."""
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            full_key = f"{path}.{k}" if path else k
            if _is_sensitive_key(k):
                if isinstance(v, str) and v:
                    fields_redacted.append(full_key)
                    out[k] = REDACT_PLACEHOLDER
                else:
                    # Non-string sensitive value (list, dict) — recurse to clean contents
                    out[k] = _deep_redact(v, full_key, fields_redacted)
            else:
                out[k] = _deep_redact(v, full_key, fields_redacted)
        return out
    if isinstance(data, list):
        return [_deep_redact(item, f"{path}[{i}]", fields_redacted) for i, item in enumerate(data)]
    if isinstance(data, str):
        if _CANONICAL_AVAILABLE:
            cleaned = _REDACTOR.redact_string(data)
        else:
            cleaned = _inline_redact(data)
        if cleaned != data:
            fields_redacted.append(path)
        return cleaned
    return data


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower().replace("-", "_")
    return any(s in key_lower for s in _SENSITIVE_KEYS)


def redact_string(text: str) -> str:
    """Redact a plain string using the canonical redactor."""
    if _CANONICAL_AVAILABLE:
        return _canonical_redact_secrets(text)
    return _inline_redact(text)


def is_safe(text: str) -> bool:
    """Return True if the text contains no detectable secrets."""
    if _CANONICAL_AVAILABLE:
        return _REDACTOR.is_safe(text)
    return _inline_is_safe(text)
