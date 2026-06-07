"""CR-003: provider ``_map_error`` must redact secrets from exception text.

Provider SDK exceptions can embed API keys, bearer tokens, or response bodies
in ``str(exc)``. Both clients run the canonical ``security.redaction`` patterns
before wrapping the message, so secrets never reach logs/UI/audit.
"""

from __future__ import annotations

from agent_runtime_cockpit.providers.anthropic import AnthropicClient
from agent_runtime_cockpit.providers.base import RateLimitError
from agent_runtime_cockpit.providers.openai_compatible import OpenAICompatibleClient


def test_anthropic_map_error_redacts_api_key() -> None:
    secret = "sk-ant-SECRET1234567890abcdef"
    mapped = AnthropicClient._map_error(RuntimeError(f"call failed using {secret} oops"))
    msg = str(mapped)
    assert secret not in msg
    assert "[REDACTED]" in msg


def test_openai_map_error_redacts_api_key() -> None:
    secret = "sk-SECRET1234567890abcdefABCD"
    mapped = OpenAICompatibleClient._map_error(RuntimeError(f"call failed using {secret} oops"))
    msg = str(mapped)
    assert secret not in msg
    assert "[REDACTED]" in msg


def test_map_error_redaction_preserves_classification() -> None:
    """Redaction must not break error-type detection (rate/auth/etc.)."""
    secret = "sk-ant-ABCDEFGHIJ1234567890"
    mapped = OpenAICompatibleClient._map_error(
        RuntimeError(f"429 rate limit exceeded for {secret}")
    )
    assert isinstance(mapped, RateLimitError)
    assert secret not in str(mapped)
    assert "[REDACTED]" in str(mapped)
