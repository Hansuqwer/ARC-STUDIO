"""Tests: Security — redaction, validation."""

import tempfile
from pathlib import Path

import pytest

from agent_runtime_cockpit.security.redaction import REDACT_PLACEHOLDER, Redactor
from agent_runtime_cockpit.security.validation import (
    validate_run_id,
    validate_workflow_id,
    validate_workspace_path,
)


class TestRedactor:
    def setup_method(self):
        self.r = Redactor()

    def test_redacts_api_key_pattern(self):
        text = 'api_key = "sk-abc123def456ghi789jkl012mno345"'
        result = self.r.redact_string(text)
        assert REDACT_PLACEHOLDER in result

    def test_redacts_openai_key(self):
        text = "token = sk-abcdefghijklmnopqrstuvwxyz123456"
        result = self.r.redact_string(text)
        assert REDACT_PLACEHOLDER in result

    def test_redacts_github_token(self):
        text = "auth = ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcde12"
        result = self.r.redact_string(text)
        assert REDACT_PLACEHOLDER in result

    def test_safe_text_unchanged(self):
        text = "This is a safe string with no secrets."
        result = self.r.redact_string(text)
        assert result == text

    def test_redact_dict_key_name(self):
        d = {"api_key": "my-secret-key-12345", "name": "test"}
        result = self.r.redact_dict(d)
        assert result["api_key"] == REDACT_PLACEHOLDER
        assert result["name"] == "test"

    def test_redact_nested_dict(self):
        d = {"config": {"password": "hunter2", "host": "localhost"}}
        result = self.r.redact_dict(d)
        assert result["config"]["password"] == REDACT_PLACEHOLDER
        assert result["config"]["host"] == "localhost"

    def test_is_safe_true_for_clean_text(self):
        assert self.r.is_safe("Hello world, no secrets here") is True

    def test_is_safe_false_for_key(self):
        assert self.r.is_safe("sk-" + "a" * 32) is False


class TestValidation:
    def test_valid_workspace_path(self):
        with tempfile.TemporaryDirectory() as td:
            result = validate_workspace_path(td)
            assert result.is_dir()

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_workspace_path("")

    def test_path_traversal_is_resolved_not_substring_rejected(self):
        """`..` is resolved away, not substring-rejected.

        Confinement to a workspace root is the caller's responsibility (via
        is_path_within_root); validate_workspace_path only normalizes + checks
        existence. A resolvable traversal target that exists is returned in
        canonical form.
        """
        result = validate_workspace_path("/tmp/../etc")
        assert result == Path("/etc").resolve()

    def test_nul_byte_rejected(self):
        with pytest.raises(ValueError, match="NUL"):
            validate_workspace_path("/tmp/evil\x00.txt")

    def test_nonexistent_path_raises(self):
        with pytest.raises(ValueError):
            validate_workspace_path("/nonexistent/path/xyz/abc")

    def test_valid_run_id(self):
        assert validate_run_id("run-abc-123") == "run-abc-123"

    def test_invalid_run_id(self):
        with pytest.raises(ValueError):
            validate_run_id("run/../../../etc/passwd")

    def test_valid_workflow_id(self):
        assert validate_workflow_id("wf-swarmgraph-001") == "wf-swarmgraph-001"

    def test_invalid_workflow_id_too_long(self):
        with pytest.raises(ValueError):
            validate_workflow_id("x" * 200)
