"""Runtime pack redaction utilities.

Integrates with the canonical ARC redactor in ``security/redaction.py`` so the
same secret patterns are used everywhere. If that module is unavailable (for
example when this package is imported in isolation), a self-contained fallback
pattern set is used.

Secrets must never appear in serialized manifests, logs, fixtures, or generated
scaffold output, so this module is used by the registry before any manifest is
written to disk and by ``validation.py`` to fail a manifest that embeds a secret.
"""

from __future__ import annotations

import re
from typing import Any

try:  # pragma: no cover - exercised indirectly depending on import context
    from ..security.redaction import (
        REDACT_PLACEHOLDER,
        SECRET_PATTERNS,
    )
    from ..security.redaction import (
        redact_secrets as _redact_secrets,
    )

    HAS_CANONICAL_REDACTOR = True
except Exception:  # pragma: no cover - fallback path
    HAS_CANONICAL_REDACTOR = False

    SECRET_PATTERNS = [
        ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
        ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}")),
        ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
        ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{32,}")),
        ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}")),
        ("password_url", re.compile(r"(://[^:/\s]+:)[^@/\s]+(@)")),
        ("api_key", re.compile(r'(?i)(api[-_]?key|apikey)\s*[=:]\s*["\']?[\w\-]{10,}["\']?')),
        ("auth_token", re.compile(r"(?i)auth[-_]?token\s*[=:]\s*[\"']?[\w\-\.]{10,}[\"']?")),
        (
            "generic_secret",
            re.compile(
                r"(?i)((?:secret|token|access_token)\s*[:=]\s*['\"]?)([^\s'\",}\]]{8,})(['\"]?)"
            ),
        ),
    ]
    REDACT_PLACEHOLDER = "[REDACTED]"

    def _redact_secrets(text: str) -> str:
        result = text
        for name, pattern in SECRET_PATTERNS:
            if name == "password_url":
                result = pattern.sub(r"\1[REDACTED]\2", result)
            elif name == "generic_secret":
                result = pattern.sub(r"\1[REDACTED]\3", result)
            else:
                result = pattern.sub(REDACT_PLACEHOLDER, result)
        return result


_SENSITIVE_KEY_FRAGMENTS = ["key", "token", "password", "secret", "credential", "auth", "bearer"]


def _redact_value(data: Any) -> Any:
    """Recursively redact secrets from a dict/list/str."""
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for k, v in data.items():
            if any(fragment in k.lower() for fragment in _SENSITIVE_KEY_FRAGMENTS):
                result[k] = REDACT_PLACEHOLDER if isinstance(v, str) and v else v
            else:
                result[k] = _redact_value(v)
        return result
    if isinstance(data, list):
        return [_redact_value(item) for item in data]
    if isinstance(data, str):
        return _redact_secrets(data)
    return data


def redact_manifest(manifest: Any) -> Any:
    """Return a redacted dict copy of a manifest (or dict) safe for serialization."""
    data = manifest.model_dump() if hasattr(manifest, "model_dump") else dict(manifest)
    return _redact_value(data)


def redact_string(text: str) -> str:
    """Redact secrets from a plain string (used for log lines)."""
    return _redact_secrets(text)


def find_secrets(manifest: Any) -> list[str]:
    """Return the names of secret patterns detected anywhere in a manifest.

    Used by validation to *reject* manifests that embed secrets. The raw secret
    value is never returned — only the pattern name (for example ``openai_key``).
    Sensitive key names that carry a non-empty string value are reported as
    ``sensitive_key:<name>``.
    """
    found: list[str] = []
    raw = manifest.model_dump() if hasattr(manifest, "model_dump") else dict(manifest)

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if (
                    any(fragment in k.lower() for fragment in _SENSITIVE_KEY_FRAGMENTS)
                    and isinstance(v, str)
                    and v
                    and v != REDACT_PLACEHOLDER
                ):
                    found.append(f"sensitive_key:{k}")
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif isinstance(obj, str):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(obj):
                    found.append(name)

    _walk(raw)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for name in found:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def is_safe_manifest(manifest: Any) -> bool:
    """True if no secret patterns are detected in the manifest."""
    return not find_secrets(manifest)


__all__ = [
    "redact_manifest",
    "redact_string",
    "find_secrets",
    "is_safe_manifest",
    "REDACT_PLACEHOLDER",
    "HAS_CANONICAL_REDACTOR",
]
