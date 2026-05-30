"""Tests: Isolation providers — none and subprocess."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_runtime_cockpit.isolation import (
    NoneIsolationProvider,
    SubprocessIsolationProvider,
)


class TestNoneIsolationProvider:
    """Direct subprocess execution (no isolation)."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        provider = NoneIsolationProvider()
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_execute_success(self):
        provider = NoneIsolationProvider()
        result = await provider.execute(["echo", "hello world"])
        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.provider == "none"

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        provider = NoneIsolationProvider()
        result = await provider.execute(["sh", "-c", "exit 42"])
        assert result.exit_code == 42

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self):
        provider = NoneIsolationProvider()
        result = await provider.execute(
            ["pwd"],
            cwd=Path("/tmp"),
        )
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        provider = NoneIsolationProvider()
        result = await provider.execute(
            ["sleep", "10"],
            timeout_seconds=1,
        )
        assert result.killed is True
        assert result.kill_reason == "timeout"

    @pytest.mark.asyncio
    async def test_execute_with_env(self):
        provider = NoneIsolationProvider(safe_env_keys=frozenset({"PATH", "CUSTOM_VAR"}))
        result = await provider.execute(
            ["sh", "-c", "echo $CUSTOM_VAR"],
            env={"CUSTOM_VAR": "pass-through"},
        )
        assert result.exit_code == 0
        assert "pass-through" in result.stdout

    def test_provider_id(self):
        provider = NoneIsolationProvider()
        assert provider.provider_id == "none"

    def test_describe(self):
        provider = NoneIsolationProvider()
        desc = provider.describe()
        assert desc["provider_id"] == "none"
        assert desc["available"] is True
        assert desc["security_posture"] == "diagnostics_only_no_isolation"
        assert desc["user_selectable"] is False

    @pytest.mark.asyncio
    async def test_execute_strips_secret_env(self):
        provider = NoneIsolationProvider(safe_env_keys=frozenset({"PATH", "SECRET_KEY"}))
        result = await provider.execute(
            ["sh", "-c", "printf %s ${SECRET_KEY:-missing}"],
            env={"SECRET_KEY": "should-not-pass", "PATH": os.environ.get("PATH", "/usr/bin")},
        )
        assert result.stdout == "missing"

    @pytest.mark.asyncio
    async def test_execute_caps_output(self):
        provider = NoneIsolationProvider(max_output_bytes=8)
        result = await provider.execute(["sh", "-c", "printf %s xxxxxxxxxxxxxxxxxxxx"])
        assert result.stdout == "xxxxxxxx"
        assert result.stdout_truncated is True


class TestSubprocessIsolationProvider:
    """Subprocess with env filtering."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        provider = SubprocessIsolationProvider()
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_execute_success(self):
        provider = SubprocessIsolationProvider()
        result = await provider.execute(["echo", "hello"])
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.provider == "subprocess"

    def test_filter_env_blocks_secret_key(self):
        provider = SubprocessIsolationProvider()
        filtered = provider.filter_env(
            extra_env={"SECRET_KEY": "should-be-blocked", "PATH": "/usr/bin"},
        )
        assert "SECRET_KEY" not in filtered
        assert "PATH" in filtered

    def test_filter_env_allows_explicitly_allowlisted_arc_vars(self):
        provider = SubprocessIsolationProvider(
            safe_env_keys=frozenset({"PATH", "ARC_SOME_VAR"}),
        )
        filtered = provider.filter_env(
            extra_env={"ARC_SOME_VAR": "allowed", "SECRET": "blocked"},
        )
        assert "ARC_SOME_VAR" in filtered
        assert "SECRET" not in filtered

    def test_filter_env_blocks_unlisted_arc_secrets(self):
        provider = SubprocessIsolationProvider(
            safe_env_keys=frozenset({"PATH"}),
        )
        filtered = provider.filter_env(
            extra_env={"ARC_HMAC_KEY": "should-be-blocked", "PATH": "/usr/bin"},
        )
        assert "ARC_HMAC_KEY" not in filtered

    def test_filter_env_respects_safe_keys(self):
        provider = SubprocessIsolationProvider(
            safe_env_keys=frozenset({"PATH", "HOME"}),
        )
        filtered = provider.filter_env(
            extra_env={"PATH": "/custom", "HOME": "/home/user", "SECRET": "x"},
        )
        assert filtered.get("PATH") == "/custom"
        assert filtered.get("HOME") == "/home/user"
        assert "SECRET" not in filtered

    @pytest.mark.asyncio
    async def test_execute_filters_env(self):
        """Subprocess should not see blocked env vars."""
        provider = SubprocessIsolationProvider()
        result = await provider.execute(
            ["sh", "-c", "echo SECRET=$SECRET_KEY"],
            env={"SECRET_KEY": "should-be-filtered", "PATH": os.environ.get("PATH", "/usr/bin")},
        )
        assert result.exit_code == 0
        assert "should-be-filtered" not in result.stdout

    def test_provider_id(self):
        provider = SubprocessIsolationProvider()
        assert provider.provider_id == "subprocess"

    def test_describe(self):
        provider = SubprocessIsolationProvider()
        desc = provider.describe()
        assert desc["provider_id"] == "subprocess"
        assert desc["available"] is True

    def test_filter_env_blocks_api_keys(self):
        """Blocked patterns prevent *_API_KEY vars from passing through."""
        from agent_runtime_cockpit.isolation.subprocess import _is_blocked_env_key

        assert _is_blocked_env_key("OPENAI_API_KEY") is True
        assert _is_blocked_env_key("ANTHROPIC_API_KEY") is True
        assert _is_blocked_env_key("MY_API_KEY") is True
        assert _is_blocked_env_key("PATH") is False

    def test_filter_env_blocks_tokens(self):
        """Blocked patterns prevent *_TOKEN vars from passing through."""
        from agent_runtime_cockpit.isolation.subprocess import _is_blocked_env_key

        assert _is_blocked_env_key("GITHUB_TOKEN") is True
        assert _is_blocked_env_key("AUTH_TOKEN") is True
        assert _is_blocked_env_key("HOME") is False

    def test_filter_env_blocks_secrets(self):
        """Blocked patterns prevent *_SECRET vars from passing through."""
        from agent_runtime_cockpit.isolation.subprocess import _is_blocked_env_key

        assert _is_blocked_env_key("CLIENT_SECRET") is True
        assert _is_blocked_env_key("AWS_SECRET_ACCESS_KEY") is True
        assert _is_blocked_env_key("LANG") is False

    def test_filter_env_blocks_aws_prefix(self):
        """Blocked patterns prevent AWS_* vars from passing through."""
        from agent_runtime_cockpit.isolation.subprocess import _is_blocked_env_key

        assert _is_blocked_env_key("AWS_ACCESS_KEY_ID") is True
        assert _is_blocked_env_key("AWS_DEFAULT_REGION") is True

    def test_output_redaction_openai_key(self):
        """Output redaction removes OpenAI API keys."""
        from agent_runtime_cockpit.isolation.subprocess import redact_output

        text = "Using key sk-abc123def456ghi789jkl012mno345pqr678 for API"
        result = redact_output(text)
        assert "sk-abc123def456ghi789jkl012mno345pqr678" not in result
        assert "[REDACTED]" in result

    def test_output_redaction_anthropic_key(self):
        """Output redaction removes Anthropic API keys."""
        from agent_runtime_cockpit.isolation.subprocess import redact_output

        text = "ANTHROPIC_API_KEY=sk-ant-api03-abc123def456ghi789jkl"
        result = redact_output(text)
        assert "sk-ant-api03" not in result
        assert "[REDACTED]" in result

    def test_output_redaction_bearer_token(self):
        """Output redaction removes bearer tokens."""
        from agent_runtime_cockpit.isolation.subprocess import redact_output

        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123"
        result = redact_output(text)
        assert "eyJhbGci" not in result
        assert "[REDACTED]" in result

    def test_output_redaction_password_url(self):
        """Output redaction removes passwords from URLs."""
        from agent_runtime_cockpit.isolation.subprocess import redact_output

        text = "postgresql://admin:supersecret@localhost:5432/db"
        result = redact_output(text)
        assert "supersecret" not in result
        assert "[REDACTED]" in result

    def test_output_redaction_no_secrets(self):
        """Output without secrets is unchanged."""
        from agent_runtime_cockpit.isolation.subprocess import redact_output

        text = "Hello world, this is normal output"
        result = redact_output(text)
        assert result == text

    @pytest.mark.asyncio
    async def test_execute_redacts_output(self):
        """Subprocess output is redacted by default."""
        provider = SubprocessIsolationProvider()
        result = await provider.execute(
            ["sh", "-c", "echo 'key=sk-abc123def456ghi789jkl012mno345pqr678'"],
        )
        assert result.exit_code == 0
        assert "sk-abc123def456ghi789jkl012mno345pqr678" not in result.stdout
        assert "[REDACTED]" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_no_redaction_when_disabled(self):
        """Subprocess output is not redacted when redact_output=False."""
        provider = SubprocessIsolationProvider(redact_output=False)
        result = await provider.execute(
            ["sh", "-c", "echo 'key=sk-abc123def456ghi789jkl012mno345pqr678'"],
        )
        assert result.exit_code == 0
        assert "sk-abc123def456ghi789jkl012mno345pqr678" in result.stdout
