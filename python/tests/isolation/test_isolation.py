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
        provider = NoneIsolationProvider()
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

    def test_filter_env_blocks_secrets(self):
        provider = SubprocessIsolationProvider()
        filtered = provider.filter_env(
            extra_env={"SECRET_KEY": "should-be-blocked", "PATH": "/usr/bin"},
        )
        assert "SECRET_KEY" not in filtered
        assert "PATH" in filtered

    def test_filter_env_allows_arc_vars(self):
        """ARC_* prefixed vars are allowed through."""
        provider = SubprocessIsolationProvider(
            safe_env_keys=frozenset({"PATH", "ARC_SOME_VAR"}),
        )
        filtered = provider.filter_env(
            extra_env={"ARC_SOME_VAR": "allowed", "SECRET": "blocked"},
        )
        assert "ARC_SOME_VAR" in filtered
        assert "SECRET" not in filtered

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
