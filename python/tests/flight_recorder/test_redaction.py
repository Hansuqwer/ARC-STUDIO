"""Tests for flight_recorder.redaction — secrets MUST NOT appear in output.

These tests are the primary safety gate for the Flight Recorder.
Any failure here means a potential secret leak into persisted storage.
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.flight_recorder.redaction import (
    REDACT_PLACEHOLDER,
    _is_sensitive_key,
    is_safe,
    redact_payload,
    redact_string,
)


# ---------------------------------------------------------------------------
# Known secret patterns
# ---------------------------------------------------------------------------


KNOWN_SECRETS = [
    # Anthropic API key
    "sk-ant-api03-ABCDEFGHIJ1234567890XXXXXX",
    # OpenAI API key (>=20 chars)
    "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
    # AWS Access Key
    "AKIAIOSFODNN7EXAMPLE",
    # GitHub token
    "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
    # Bearer token
    "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
    # Private key header
    "-----BEGIN RSA PRIVATE KEY-----",
    # Password in assignment
    "password = my_super_secret_password",
]


class TestRedactString:
    @pytest.mark.parametrize("secret", KNOWN_SECRETS)
    def test_secret_is_redacted(self, secret: str):
        result = redact_string(secret)
        assert secret not in result, f"Secret was NOT redacted: {secret!r}"

    def test_safe_string_unchanged(self):
        text = "This is a perfectly safe string about workflows."
        result = redact_string(text)
        assert result == text

    def test_placeholder_present(self):
        result = redact_string("api_key = sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ123")
        assert "[REDACTED]" in result

    def test_url_password_redacted(self):
        url = "postgresql://user:my_secret_password@localhost:5432/db"
        result = redact_string(url)
        assert "my_secret_password" not in result

    def test_empty_string(self):
        assert redact_string("") == ""

    def test_no_false_positive_on_short_sk(self):
        # sk- followed by only 5 chars — should NOT trigger openai_key (needs >= 20)
        short = "sk-abc12"
        result = redact_string(short)
        assert result == short  # not redacted — too short

    def test_anthropic_before_openai(self):
        # sk-ant- must be caught by anthropic_key before openai_key swallows it
        secret = "sk-ant-api03-ABCDEFGHIJ123456"
        result = redact_string(secret)
        assert secret not in result


class TestIsSafe:
    @pytest.mark.parametrize("secret", KNOWN_SECRETS)
    def test_known_secret_not_safe(self, secret: str):
        assert is_safe(secret) is False, f"Expected is_safe=False for: {secret!r}"

    def test_safe_string(self):
        assert is_safe("Hello, world!") is True

    def test_empty_safe(self):
        assert is_safe("") is True


class TestRedactPayload:
    def test_api_key_in_dict(self):
        payload = {"api_key": "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ123"}
        clean, summary = redact_payload(payload)
        assert clean["api_key"] == REDACT_PLACEHOLDER
        assert summary.redact_applied is True

    def test_token_in_dict(self):
        payload = {"access_token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"}
        clean, summary = redact_payload(payload)
        assert clean["access_token"] == REDACT_PLACEHOLDER

    def test_password_in_dict(self):
        payload = {"password": "my_super_secret"}
        clean, summary = redact_payload(payload)
        assert clean["password"] == REDACT_PLACEHOLDER

    def test_nested_secret(self):
        payload = {"config": {"secret_key": "sk-ant-api03-ABCDEFGHIJ1234567890"}}
        clean, summary = redact_payload(payload)
        assert clean["config"]["secret_key"] == REDACT_PLACEHOLDER

    def test_list_values(self):
        payload = {"tokens": ["safe_value", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"]}
        clean, summary = redact_payload(payload)
        # The string inside the list should be cleaned by pattern matching
        assert "ghp_" not in str(clean["tokens"])

    def test_safe_dict_unchanged(self):
        payload = {"workflow": "my_workflow", "node_count": 5}
        clean, summary = redact_payload(payload)
        assert clean == payload
        assert summary.redact_applied is False

    def test_redact_secrets_false_returns_original(self):
        payload = {"api_key": "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ123"}
        clean, summary = redact_payload(payload, redact_secrets=False)
        assert clean == payload
        assert summary.redact_applied is False

    def test_returns_dict_always(self):
        clean, summary = redact_payload({})
        assert isinstance(clean, dict)

    def test_fields_redacted_list_populated(self):
        payload = {"token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"}
        clean, summary = redact_payload(payload)
        assert "token" in summary.fields_redacted

    def test_no_secret_in_output_json(self):
        """Integration: ensure no secret survives into JSON serialisation."""
        import json

        payload = {
            "api_key": "sk-proj-SUPERSECRETKEY12345678901234",
            "bearer": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.super_secret",
            "safe_field": "this is safe",
        }
        clean, _ = redact_payload(payload)
        serialised = json.dumps(clean)
        assert "sk-proj-SUPERSECRETKEY" not in serialised
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in serialised
        assert "this is safe" in serialised


class TestIsSensitiveKey:
    def test_known_sensitive_keys(self):
        for k in ["api_key", "token", "password", "secret", "bearer", "private_key"]:
            assert _is_sensitive_key(k), f"Expected {k!r} to be sensitive"

    def test_non_sensitive_keys(self):
        for k in ["workflow", "node_count", "run_id", "timestamp", "source"]:
            assert not _is_sensitive_key(k), f"Expected {k!r} to be NOT sensitive"
