"""Secret redaction for mobile manifests and capabilities.

Uses the repo's canonical security/redaction.py as the source of truth.
Fail-closed: if redaction raises, returns safe placeholder.
"""

from __future__ import annotations

from typing import Any

_REDACTED = "[REDACTED]"
_SECRET_KEYS = (
    "key",
    "token",
    "secret",
    "password",
    "credential",
    "api_key",
    "apikey",
    "auth",
    "bearer",
    "private",
)


def _is_secret_key(k: str) -> bool:
    lk = k.lower().replace("-", "_")
    return any(s in lk for s in _SECRET_KEYS)


def redact_dict(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    from ..security.redaction import Redactor

    redactor = Redactor()
    out: dict[str, Any] = {}
    total = 0
    for k, v in data.items():
        if _is_secret_key(k) and isinstance(v, str) and v:
            out[k] = _REDACTED
            total += 1
        elif isinstance(v, str):
            try:
                out[k] = v if redactor.is_safe(v) else _REDACTED
                if out[k] == _REDACTED:
                    total += 1
            except Exception:
                out[k] = _REDACTED
                total += 1
        elif isinstance(v, dict):
            out[k], n = redact_dict(v)
            total += n
        elif isinstance(v, list):
            out[k], n = redact_list(v)
            total += n
        else:
            out[k] = v
    return out, total


def redact_list(lst: list[Any]) -> tuple[list[Any], int]:
    out = []
    total = 0
    for item in lst:
        if isinstance(item, dict):
            r, n = redact_dict(item)
            out.append(r)
            total += n
        elif isinstance(item, list):
            r, n = redact_list(item)
            out.append(r)
            total += n
        elif isinstance(item, str) and item:
            try:
                from ..security.redaction import Redactor

                redactor = Redactor()
                safe = redactor.is_safe(item)
                out.append(item if safe else _REDACTED)
                if not safe:
                    total += 1
            except Exception:
                out.append(_REDACTED)
                total += 1
        else:
            out.append(item)
    return out, total
