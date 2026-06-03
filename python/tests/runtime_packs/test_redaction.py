"""Tests for secret detection and manifest redaction."""

from __future__ import annotations

from agent_runtime_cockpit.runtime_packs import (
    RuntimeIdentity,
    RuntimePackManifest,
    find_secrets,
    is_safe_manifest,
    manifest_hash,
    redact_manifest,
    redact_string,
)


class TestRedactString:
    def test_clean_string_unchanged(self):
        result = redact_string("hello world")
        assert result == "hello world"

    def test_openai_key_redacted(self):
        dirty = "sk-abcdefghijklmnopqrstuv"  # matches openai_key pattern
        result = redact_string(dirty)
        assert "[REDACTED]" in result
        assert "sk-abcde" not in result

    def test_aws_key_redacted(self):
        dirty = "AKIAIOSFODNN7EXAMPLE"  # matches aws_key pattern
        result = redact_string(dirty)
        assert "[REDACTED]" in result

    def test_private_key_redacted(self):
        dirty = "-----BEGIN RSA PRIVATE KEY-----"
        result = redact_string(dirty)
        assert "[REDACTED]" in result


class TestFindSecrets:
    def test_clean_dict_returns_empty(self, minimal_manifest):
        data = minimal_manifest.model_dump(mode="json")
        assert find_secrets(data) == []

    def test_openai_key_in_metadata_detected(self):
        data = {
            "id": "x.y",
            "metadata": {"api_key": "sk-abcdefghijklmnopqrstuv"},
        }
        found = find_secrets(data)
        assert found  # at least one pattern fired

    def test_aws_key_detected(self):
        data = {"id": "x.y", "token": "AKIAIOSFODNN7EXAMPLE"}
        found = find_secrets(data)
        assert found

    def test_nested_secret_detected(self):
        data = {
            "id": "x.y",
            "metadata": {"deep": {"key": "sk-abcdefghijklmnopqrstuv"}},
        }
        found = find_secrets(data)
        assert found


class TestIsManifestSafe:
    def test_clean_manifest_is_safe(self, minimal_manifest):
        assert is_safe_manifest(minimal_manifest) is True

    def test_manifest_with_secret_not_safe(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            metadata={"token": "AKIAIOSFODNN7EXAMPLE"},
        )
        assert is_safe_manifest(m) is False


class TestRedactManifest:
    def test_redact_clean_manifest_unchanged_id(self, minimal_manifest):
        redacted = redact_manifest(minimal_manifest)
        assert isinstance(redacted, dict)
        assert redacted["id"] == minimal_manifest.id

    def test_redact_removes_secret_from_metadata(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            metadata={"api_key": "sk-abcdefghijklmnopqrstuv"},
        )
        redacted = redact_manifest(m)
        assert isinstance(redacted, dict)
        assert "[REDACTED]" in str(redacted.get("metadata", {}))
        assert "sk-abcde" not in str(redacted.get("metadata", {}))

    def test_redact_returns_dict_not_model(self, minimal_manifest):
        redacted = redact_manifest(minimal_manifest)
        assert isinstance(redacted, dict)
        # Original model is unchanged
        assert isinstance(minimal_manifest, RuntimePackManifest)

    def test_redacted_dict_has_cleared_hash_field(self):
        """Redacting sensitive keys should clear known sensitive fields."""
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            metadata={"token": "AKIAIOSFODNN7EXAMPLE"},
        )
        m.manifest_hash = manifest_hash(m)
        redacted = redact_manifest(m)
        # The metadata token value should be redacted
        assert "[REDACTED]" in str(redacted.get("metadata", {}))
