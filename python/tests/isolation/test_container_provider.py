"""Tests for SubprocessContainerProvider and container_preflight."""

from __future__ import annotations

import subprocess
from io import BytesIO
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.isolation.docker_provider import (
    SubprocessContainerProvider,
    container_sandbox_enabled,
)
from agent_runtime_cockpit.security.sandbox import container_preflight


# ---------------------------------------------------------------------------
# 1. container_sandbox_enabled() returns False when env not set
# ---------------------------------------------------------------------------
def test_container_sandbox_enabled_false_by_default(monkeypatch):
    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)
    assert container_sandbox_enabled() is False


# ---------------------------------------------------------------------------
# 2. container_sandbox_enabled() returns True when ARC_ENABLE_CONTAINER_SANDBOX=1
# ---------------------------------------------------------------------------
def test_container_sandbox_enabled_true_when_set(monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")
    assert container_sandbox_enabled() is True


# ---------------------------------------------------------------------------
# 3. health_check() returns False when container sandbox disabled
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_check_false_when_sandbox_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)
    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    result = await provider.health_check()
    assert result is False


# ---------------------------------------------------------------------------
# 4. health_check() returns False when no docker/podman binary
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_check_false_when_no_binary(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")
    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    with patch.object(
        SubprocessContainerProvider,
        "detect_runtime",
        return_value={"runtime": "unavailable", "available": False, "binary": None},
    ):
        result = await provider.health_check()
    assert result is False


# ---------------------------------------------------------------------------
# 5. execute() returns blocked result when sandbox disabled
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_returns_blocked_when_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)
    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    result = await provider.execute(["echo", "hi"], cwd=tmp_path)
    assert result.exit_code == -1
    assert "disabled" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 6. execute() success path with monkeypatched docker binary
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_success_path(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")

    # Build a fake Popen that immediately exits 0 with known output
    class FakeProc:
        returncode = 0
        pid = 12345

        def __init__(self):
            self.stdout = BytesIO(b"hello world\n")
            self.stderr = BytesIO(b"")

        def wait(self, timeout=None):
            return 0

    fake_runtime = {"runtime": "docker", "available": True, "binary": "/usr/bin/docker"}

    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    with (
        patch.object(SubprocessContainerProvider, "detect_runtime", return_value=fake_runtime),
        patch("subprocess.Popen", return_value=FakeProc()),
    ):
        result = await provider.execute(["echo", "hello"], cwd=tmp_path)

    assert result.exit_code == 0
    assert result.provider == "container"
    assert "hello world" in result.stdout


# ---------------------------------------------------------------------------
# 7. execute() with timeout returns killed=True
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_timeout_sets_killed(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")

    fake_runtime = {"runtime": "docker", "available": True, "binary": "/usr/bin/docker"}

    class FakeProc:
        returncode = -9
        pid = 99999

        def __init__(self):
            self.stdout = BytesIO(b"")
            self.stderr = BytesIO(b"")

        def wait(self, timeout=None):
            if timeout is not None and timeout <= 1:
                raise subprocess.TimeoutExpired(cmd="docker", timeout=timeout)
            return -9

    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    with (
        patch.object(SubprocessContainerProvider, "detect_runtime", return_value=fake_runtime),
        patch("subprocess.Popen", return_value=FakeProc()),
        patch("os.killpg"),
    ):
        result = await provider.execute(["sleep", "100"], cwd=tmp_path, timeout_seconds=1)

    assert result.killed is True
    assert result.kill_reason == "timeout"


# ---------------------------------------------------------------------------
# 8. execute() strips secret env vars
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_strips_secret_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secretsecretsecretsecretsecretsecret")

    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    env_args = provider._filter_env({"OPENAI_API_KEY": "sk-another-secret"})
    # Secret key must not appear in any -e KEY=VAL pair
    joined = " ".join(env_args)
    assert "OPENAI_API_KEY" not in joined
    assert "sk-" not in joined


# ---------------------------------------------------------------------------
# 9. execute() truncates output at max_output_bytes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_truncates_output(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")

    big_output = b"x" * 200_000

    class FakeProc:
        returncode = 0
        pid = 11111

        def __init__(self):
            self.stdout = BytesIO(big_output)
            self.stderr = BytesIO(b"")

        def wait(self, timeout=None):
            return 0

    fake_runtime = {"runtime": "docker", "available": True, "binary": "/usr/bin/docker"}
    provider = SubprocessContainerProvider(workspace_root=tmp_path, max_output_bytes=1024)
    with (
        patch.object(SubprocessContainerProvider, "detect_runtime", return_value=fake_runtime),
        patch("subprocess.Popen", return_value=FakeProc()),
    ):
        result = await provider.execute(["cat", "bigfile"], cwd=tmp_path)

    assert result.stdout_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 1024


# ---------------------------------------------------------------------------
# 10. execute() redacts API keys in output
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_redacts_api_key_in_output(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_ENABLE_CONTAINER_SANDBOX", "1")

    output_with_secret = b"token: sk-abcdefghijklmnopqrstuvwxyz123456\n"

    class FakeProc:
        returncode = 0
        pid = 22222

        def __init__(self):
            self.stdout = BytesIO(output_with_secret)
            self.stderr = BytesIO(b"")

        def wait(self, timeout=None):
            return 0

    fake_runtime = {"runtime": "docker", "available": True, "binary": "/usr/bin/docker"}
    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    with (
        patch.object(SubprocessContainerProvider, "detect_runtime", return_value=fake_runtime),
        patch("subprocess.Popen", return_value=FakeProc()),
    ):
        result = await provider.execute(["cat", "secrets.txt"], cwd=tmp_path)

    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result.stdout
    assert result.redaction_applied is True


# ---------------------------------------------------------------------------
# 11. detect_runtime() returns unavailable when no binary
# ---------------------------------------------------------------------------
def test_detect_runtime_unavailable_when_no_binary(monkeypatch, tmp_path):
    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    with patch("shutil.which", return_value=None):
        info = provider.detect_runtime()
    assert info["available"] is False
    assert info["runtime"] == "unavailable"
    assert info["binary"] is None


# ---------------------------------------------------------------------------
# 12. describe() returns dict with provider_id=container
# ---------------------------------------------------------------------------
def test_describe_returns_container_provider_id(monkeypatch, tmp_path):
    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)
    provider = SubprocessContainerProvider(workspace_root=tmp_path)
    desc = provider.describe()
    assert desc["provider_id"] == "container"
    assert "runtime" in desc
    assert "image" in desc


# ---------------------------------------------------------------------------
# 13. container_preflight() returns unavailable when binary missing and sandbox disabled
# ---------------------------------------------------------------------------
def test_container_preflight_unavailable_no_binary_no_env(monkeypatch):
    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)
    with patch("shutil.which", return_value=None):
        result = container_preflight()
    assert result["provider"] == "container"
    assert result["status"] == "unavailable"
    assert result["enabled"] is False
    assert result["binary"] is None
    assert len(result["blockers"]) >= 2


# ---------------------------------------------------------------------------
# 14. container_preflight() returns disabled when binary present but sandbox disabled
# ---------------------------------------------------------------------------
def test_container_preflight_disabled_when_binary_present_but_not_enabled(monkeypatch):
    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)

    def fake_which(name):
        if name == "docker":
            return "/usr/local/bin/docker"
        return None

    with patch("shutil.which", side_effect=fake_which):
        result = container_preflight()

    assert result["status"] == "disabled"
    assert result["enabled"] is False
    assert result["binary"] == "/usr/local/bin/docker"
    assert result["runtime"] == "docker"
    # Should still list the missing env var as a blocker
    assert any("ARC_ENABLE_CONTAINER_SANDBOX" in b for b in result["blockers"])


# ---------------------------------------------------------------------------
# 15. _build_provider("container", ...) returns SubprocessContainerProvider
# ---------------------------------------------------------------------------
def test_build_provider_returns_subprocess_container_provider(tmp_path):
    from agent_runtime_cockpit.cli.sandbox import _build_provider
    from agent_runtime_cockpit.isolation.docker_provider import SubprocessContainerProvider
    from agent_runtime_cockpit.security.sandbox import SandboxPolicy

    policy = SandboxPolicy(name="local-safe", workspace_root=tmp_path)
    provider = _build_provider("container", policy, tmp_path)
    assert isinstance(provider, SubprocessContainerProvider)
