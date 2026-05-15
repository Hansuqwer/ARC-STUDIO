"""Tests for Docker isolation provider."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime_cockpit.isolation.docker_provider import (
    DockerConfig,
    DockerIsolationProvider,
)


def _make_mock_client(version_str="24.0.0"):
    """Create a mock Docker client."""
    mock_client = MagicMock()
    mock_client.version.return_value = {"ServerVersion": version_str}
    return mock_client


@pytest.mark.asyncio
async def test_docker_health_check_unavailable():
    """Docker health check returns False when daemon unreachable."""
    mock_client = MagicMock()
    mock_client.version.side_effect = Exception("daemon not reachable")
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        healthy = await provider.health_check()
        assert healthy is False


@pytest.mark.asyncio
async def test_docker_health_check_sdk_missing():
    """Docker health check returns False when SDK not installed."""
    provider = DockerIsolationProvider()
    provider._client = None
    with patch.object(DockerIsolationProvider, "_get_client", return_value=None):
        healthy = await provider.health_check()
        assert healthy is False


@pytest.mark.asyncio
async def test_docker_health_check_available():
    """Docker health check returns True when daemon reachable."""
    mock_client = _make_mock_client()
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        healthy = await provider.health_check()
        assert healthy is True


def test_docker_detect_runtime_docker():
    """Docker detect_runtime identifies standard Docker."""
    mock_client = _make_mock_client("24.0.0")
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        info = provider.detect_runtime()
        assert info["available"] is True
        assert info["runtime"] == "docker"


def test_docker_detect_runtime_orbstack():
    """Docker detect_runtime identifies OrbStack."""
    mock_client = _make_mock_client("orbstack-1.0.0")
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        info = provider.detect_runtime()
        assert info["available"] is True
        assert info["runtime"] == "orbstack"


def test_docker_detect_runtime_podman():
    """Docker detect_runtime identifies Podman."""
    mock_client = _make_mock_client("podman-5.0.0")
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        info = provider.detect_runtime()
        assert info["available"] is True
        assert info["runtime"] == "podman"


def test_docker_detect_runtime_sdk_missing():
    """Docker detect_runtime reports error when SDK missing."""
    with patch.object(DockerIsolationProvider, "_get_client", return_value=None):
        provider = DockerIsolationProvider()
        info = provider.detect_runtime()
        assert info["available"] is False
        assert "error" in info


@pytest.mark.asyncio
async def test_docker_execute_success():
    """Docker execute returns result on success."""
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"hello world\n"
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        result = await provider.execute(["echo", "hello"])
        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.provider == "docker"


@pytest.mark.asyncio
async def test_docker_execute_timeout():
    """Docker execute kills container on timeout."""
    mock_container = MagicMock()
    mock_container.wait.side_effect = Exception("timeout")
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        result = await provider.execute(["sleep", "100"], timeout_seconds=1)
        assert result.exit_code == -1
        assert result.killed is True
        assert result.kill_reason == "timeout"
        mock_container.kill.assert_called_once()


@pytest.mark.asyncio
async def test_docker_execute_sdk_missing():
    """Docker execute returns error when SDK missing."""
    with patch.object(DockerIsolationProvider, "_get_client", return_value=None):
        provider = DockerIsolationProvider()
        result = await provider.execute(["echo", "hello"])
        assert result.exit_code == -1
        assert "not installed" in result.stderr


def test_docker_describe():
    """Docker describe returns provider info."""
    mock_client = _make_mock_client("24.0.0")
    with patch.object(DockerIsolationProvider, "_get_client", return_value=mock_client):
        provider = DockerIsolationProvider()
        desc = provider.describe()
        assert desc["provider_id"] == "docker"
        assert desc["available"] is True
        assert "image" in desc


def test_docker_config_defaults():
    """DockerConfig has sensible defaults."""
    config = DockerConfig()
    assert config.image == "python:3.12-slim"
    assert config.network_disabled is True
    assert config.mem_limit == "512m"
    assert config.cpu_quota == 50000


def test_docker_config_custom():
    """DockerConfig accepts custom values."""
    config = DockerConfig(
        image="python:3.11-slim",
        network_disabled=False,
        mem_limit="1g",
        cpu_quota=100000,
    )
    assert config.image == "python:3.11-slim"
    assert config.network_disabled is False
    assert config.mem_limit == "1g"
    assert config.cpu_quota == 100000
