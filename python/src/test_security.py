"""
Security Tests for ARC Studio Backend

Tests input validation, sanitization, and security controls.
"""

import pytest
from security_utils import (
    sanitize_prompt,
    validate_trace_id,
    validate_file_path,
    validate_backend,
    sanitize_error_message,
    validate_workspace_root,
    SecurityError
)
from pathlib import Path
import tempfile
import os


class TestPromptSanitization:
    """Tests for prompt sanitization"""
    
    def test_valid_prompt(self):
        """Valid prompts should pass through"""
        prompt = "Create a simple web application"
        assert sanitize_prompt(prompt) == prompt
    
    def test_empty_prompt(self):
        """Empty prompts should raise SecurityError"""
        with pytest.raises(SecurityError, match="must be a non-empty string"):
            sanitize_prompt("")
    
    def test_none_prompt(self):
        """None prompts should raise SecurityError"""
        with pytest.raises(SecurityError, match="must be a non-empty string"):
            sanitize_prompt(None)
    
    def test_command_injection_semicolon(self):
        """Prompts with semicolons should be rejected"""
        with pytest.raises(SecurityError, match="dangerous characters"):
            sanitize_prompt("test; rm -rf /")
    
    def test_command_injection_pipe(self):
        """Prompts with pipes should be rejected"""
        with pytest.raises(SecurityError, match="dangerous characters"):
            sanitize_prompt("test | cat /etc/passwd")
    
    def test_command_injection_backtick(self):
        """Prompts with backticks should be rejected"""
        with pytest.raises(SecurityError, match="dangerous characters"):
            sanitize_prompt("test `whoami`")
    
    def test_command_injection_dollar_paren(self):
        """Prompts with $() should be rejected"""
        with pytest.raises(SecurityError, match="dangerous characters"):
            sanitize_prompt("test $(whoami)")
    
    def test_command_injection_ampersand(self):
        """Prompts with & should be rejected"""
        with pytest.raises(SecurityError, match="dangerous characters"):
            sanitize_prompt("test & malicious_command")
    
    def test_null_byte_injection(self):
        """Prompts with null bytes should be sanitized"""
        prompt = "test\x00injection"
        sanitized = sanitize_prompt(prompt)
        assert "\x00" not in sanitized
    
    def test_control_characters(self):
        """Control characters should be removed"""
        prompt = "test\x01\x02\x03normal"
        sanitized = sanitize_prompt(prompt)
        assert sanitized == "testnormal"
    
    def test_max_length(self):
        """Prompts exceeding max length should be rejected"""
        long_prompt = "a" * 10001
        with pytest.raises(SecurityError, match="exceeds maximum length"):
            sanitize_prompt(long_prompt)
    
    def test_whitespace_trimming(self):
        """Leading/trailing whitespace should be trimmed"""
        prompt = "  test prompt  "
        assert sanitize_prompt(prompt) == "test prompt"


class TestTraceIdValidation:
    """Tests for trace ID validation"""
    
    def test_valid_trace_id(self):
        """Valid trace IDs should pass"""
        trace_id = "run-sg-abc123def456"
        assert validate_trace_id(trace_id) == trace_id
    
    def test_invalid_format(self):
        """Invalid format should be rejected"""
        with pytest.raises(SecurityError, match="Invalid trace ID format"):
            validate_trace_id("invalid-format")
    
    def test_path_traversal_dotdot(self):
        """Path traversal with .. should be rejected"""
        with pytest.raises(SecurityError, match="Invalid trace ID format"):
            validate_trace_id("run-sg-abc/../etc/passwd")
    
    def test_path_traversal_slash(self):
        """Path traversal with / should be rejected"""
        with pytest.raises(SecurityError, match="Invalid trace ID format"):
            validate_trace_id("run-sg-abc/../../etc/passwd")
    
    def test_path_traversal_backslash(self):
        """Path traversal with \\ should be rejected"""
        with pytest.raises(SecurityError, match="Invalid trace ID format"):
            validate_trace_id("run-sg-abc\\..\\etc\\passwd")
    
    def test_empty_trace_id(self):
        """Empty trace ID should be rejected"""
        with pytest.raises(SecurityError, match="must be a non-empty string"):
            validate_trace_id("")
    
    def test_uppercase_hex(self):
        """Uppercase hex should be rejected (format requires lowercase)"""
        with pytest.raises(SecurityError, match="Invalid trace ID format"):
            validate_trace_id("run-sg-ABC123")


class TestFilePathValidation:
    """Tests for file path validation"""
    
    def test_valid_path_within_workspace(self):
        """Valid paths within workspace should pass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_file_path(".arc/traces/test.jsonl", tmpdir)
            # Use Path.resolve() for comparison to handle macOS symlink (/var -> /private/var)
            assert str(result).startswith(str(Path(tmpdir).resolve()))
    
    def test_path_traversal_outside_workspace(self):
        """Paths outside workspace should be rejected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="outside workspace boundaries"):
                validate_file_path("../../etc/passwd", tmpdir)
    
    def test_absolute_path_outside_workspace(self):
        """Absolute paths outside workspace should be rejected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="outside workspace boundaries"):
                validate_file_path("/etc/passwd", tmpdir)
    
    def test_null_byte_in_path(self):
        """Paths with null bytes should be rejected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="null bytes"):
                validate_file_path("test\x00.txt", tmpdir)
    
    def test_empty_path(self):
        """Empty paths should be rejected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="must be a non-empty string"):
                validate_file_path("", tmpdir)


class TestBackendValidation:
    """Tests for backend validation"""
    
    def test_valid_backends(self):
        """Valid backends should pass"""
        assert validate_backend("gateway") == "gateway"
        assert validate_backend("local") == "local"
        assert validate_backend("remote") == "remote"
    
    def test_case_insensitive(self):
        """Backend validation should be case-insensitive"""
        assert validate_backend("GATEWAY") == "gateway"
        assert validate_backend("Local") == "local"
    
    def test_invalid_backend(self):
        """Invalid backends should be rejected"""
        with pytest.raises(SecurityError, match="Invalid backend"):
            validate_backend("malicious")
    
    def test_empty_backend(self):
        """Empty backend should be rejected"""
        with pytest.raises(SecurityError, match="must be a non-empty string"):
            validate_backend("")


class TestErrorSanitization:
    """Tests for error message sanitization"""
    
    def test_file_not_found_error(self):
        """File not found errors should be sanitized"""
        error = FileNotFoundError("No such file: /secret/path/file.txt")
        assert sanitize_error_message(error) == "Resource not found"
    
    def test_permission_error(self):
        """Permission errors should be sanitized"""
        error = PermissionError("Permission denied: /secret/path")
        assert sanitize_error_message(error) == "Permission denied"
    
    def test_timeout_error(self):
        """Timeout errors should be sanitized"""
        error = TimeoutError("Connection timeout to internal.server.local")
        assert sanitize_error_message(error) == "Operation timed out"
    
    def test_security_error_preserved(self):
        """SecurityError messages should be preserved (user-facing)"""
        error = SecurityError("Invalid trace ID format")
        assert sanitize_error_message(error) == "Invalid trace ID format"
    
    def test_generic_error(self):
        """Generic errors should get generic message"""
        error = Exception("Internal database connection failed at 192.168.1.1")
        assert sanitize_error_message(error) == "An error occurred while processing your request"


class TestWorkspaceValidation:
    """Tests for workspace root validation"""
    
    def test_valid_workspace(self):
        """Valid workspace paths should pass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_workspace_root(tmpdir)
            assert result.is_absolute()
    
    def test_relative_workspace(self):
        """Relative paths should be resolved to absolute"""
        result = validate_workspace_root(".")
        assert result.is_absolute()
    
    def test_empty_workspace(self):
        """Empty workspace should be rejected"""
        with pytest.raises(SecurityError, match="Invalid workspace root"):
            validate_workspace_root("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
