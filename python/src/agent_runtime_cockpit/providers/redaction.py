"""Shared provider error redaction + mapping helper.

Extracted from openai_compatible.py and anthropic.py (CR-050, slice 50 of 57).
Both providers had identical `_map_error` implementations using `redact_secrets`.
"""

from __future__ import annotations

from ..security.redaction import redact_secrets
from .base import AuthError, ModelError, NetworkError, RateLimitError, ValidationError


def map_provider_error(exc: Exception) -> Exception:
    """Map a provider SDK exception to an ARC ProviderError type.

    Redacts secrets from the exception message before mapping.
    Shared implementation for openai_compatible.py and anthropic.py.
    """
    name = type(exc).__name__.lower()
    text = redact_secrets(str(exc))

    if "rate" in name or "rate" in text.lower() or "429" in text:
        return RateLimitError(text)
    if "auth" in name or "401" in text or "api key" in text.lower():
        return AuthError(text)
    if "validation" in name or "400" in text:
        return ValidationError(text)
    if "connection" in name or "network" in name or "timeout" in name:
        return NetworkError(text)
    return ModelError(text)


__all__ = ["map_provider_error"]
