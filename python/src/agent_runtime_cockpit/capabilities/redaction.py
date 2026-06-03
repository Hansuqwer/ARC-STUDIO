"""Capability Card redaction utilities.

Integrates with the canonical ARC Redactor from security/redaction.py.
Never allow API keys, tokens, passwords, or private keys to appear in serialized cards.
"""

from __future__ import annotations

import re
from typing import Any

# Import the canonical ARC Redactor for consistent secret detection
# This ensures the same patterns are used everywhere in ARC
try:
    from ..security.redaction import (
        REDACT_PLACEHOLDER,
        SECRET_PATTERNS,
        redact_secrets as _redact_secrets,
    )

    HAS_CANONICAL_REDACTOR = True
except ImportError:
    HAS_CANONICAL_REDACTOR = False

    # Fallback patterns if the canonical redactor is not available
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
        ("password", re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*[\"']?.{4,}?[\"']?")),
        (
            "generic_secret",
            re.compile(
                r"(?i)((?:secret|token|access_token)\s*[:=]\s*['\"]?)([^\s'\",}\]]{8,})(['\"]?)"
            ),
        ),
    ]
    _SUBSTITUTION_TEMPLATES = {
        "password_url": r"\1[REDACTED]\2",
        "generic_secret": r"\1[REDACTED]\3",
    }
    REDACT_PLACEHOLDER = "[REDACTED]"

    def _redact_secrets(text: str) -> str:
        result = text
        for name, pattern in SECRET_PATTERNS:
            template = _SUBSTITUTION_TEMPLATES.get(name)
            if template is not None:
                result = pattern.sub(template, result)
            else:
                result = pattern.sub(REDACT_PLACEHOLDER, result)
        return result


def redact_card(card: Any) -> Any:
    """Redact secrets from a CapabilityCard dict before serialization.

    This ensures no API keys, tokens, passwords, or private keys can leak
    through serialized card files.
    """
    if hasattr(card, "model_dump"):
        data = card.model_dump()
    else:
        data = dict(card)

    return _redact_dict(data)


def _redact_dict(data: Any) -> Any:
    """Recursively redact secrets from a dict/list/str."""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            k_lower = k.lower()
            # Redact by key name
            if any(
                secret in k_lower
                for secret in ["key", "token", "password", "secret", "credential", "auth"]
            ):
                if isinstance(v, str) and v:
                    result[k] = REDACT_PLACEHOLDER
                else:
                    result[k] = v
            else:
                result[k] = _redact_dict(v)
        return result
    if isinstance(data, list):
        return [_redact_dict(item) for item in data]
    if isinstance(data, str):
        return _redact_secrets(data)
    return data


def is_safe_card(card: Any) -> bool:
    """Check if a CapabilityCard contains no detectable secrets.

    Returns True if no secret patterns are found in the card.
    """
    card_str = str(card) if not isinstance(card, str) else card
    if isinstance(card, dict):
        card_str = _redact_dict(card)
        card_str = str(card_str)

    return not any(pattern.search(card_str) for _, pattern in SECRET_PATTERNS)


def redact_string(text: str) -> str:
    """Redact secrets from a plain string.

    Convenience wrapper around the canonical _redact_secrets function.
    """
    return _redact_secrets(text)
