"""Docker isolation provider — container-based execution for untrusted workspaces."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import IsolationProvider, IsolationResult

log = logging.getLogger(__name__)


class DockerConfig(BaseModel):
    """Configuration for Docker isolation provider."""
    image: str = "python:3.12-slim"
    volumes: dict[str, dict[str, str]] = Field(default_factory=dict)
    network_disabled: bool = True
    mem_limit: str = "512m"
    cpu_quota: int = 50000
    environment: dict[str, str] = Field(default_factory=dict)


class DockerIsolationProvider(IsolationProvider):
    """Container-based isolation using Docker SDK.

    Detects OrbStack, Podman, Colima via DOCKER_HOST or daemon info.
    Falls back gracefully if Docker SDK is not installed or daemon unreachable.
    """

    def __init__(self, config: Optional[DockerConfig] = None) -> None:
        self.config = config or DockerConfig()
        self._client: Any = None
        self._runtime_info: Optional[dict[str, Any]] = None

    @property
    def provider_id(self) -> str:
        return "docker"

    async def health_check(self) -> bool:
        """Return True if Docker daemon is reachable."""
        try:
            client = self._get_client()
            if client is None:
                return False
            version = client.version()
            log.debug("Docker daemon reachable: %s", version.get("ServerVersion", "unknown"))
            return True
        except Exception as e:
            log.warning("Docker health check failed: %s", e)
            return False

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        """Execute a command inside a Docker container."""
        client = self._get_client()
        if client is None:
            return IsolationResult(
                exit_code=-1,
                stderr="Docker SDK not installed. Install with: pip install docker",
                provider=self.provider_id,
            )
        merged_env = {**self.config.environment, **(env or {})}
        start = time.monotonic()
        try:
            container = client.containers.run(
                image=self.config.image,
                command=command,
                working_dir=str(cwd) if cwd else "/workspace",
                environment=merged_env,
                volumes=self.config.volumes,
                network_disabled=self.config.network_disabled,
                mem_limit=self.config.mem_limit,
                cpu_quota=self.config.cpu_quota,
                detach=True,
                remove=True,
            )
            try:
                result = container.wait(timeout=timeout_seconds)
                exit_code = result.get("StatusCode", -1)
            except Exception:
                container.kill()
                duration = int((time.monotonic() - start) * 1000)
                return IsolationResult(
                    exit_code=-1, stdout="", stderr="container timeout",
                    duration_ms=duration, killed=True, kill_reason="timeout",
                    provider=self.provider_id,
                )
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=exit_code, stdout=logs, stderr="",
                duration_ms=duration, provider=self.provider_id,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            log.error("Docker execution failed: %s", e)
            return IsolationResult(
                exit_code=-1, stdout="", stderr=str(e),
                duration_ms=duration, provider=self.provider_id,
            )

    def detect_runtime(self) -> dict[str, Any]:
        """Detect which Docker-compatible runtime is available."""
        if self._runtime_info is not None:
            return self._runtime_info
        info: dict[str, Any] = {"available": False, "runtime": "unknown"}
        try:
            client = self._get_client()
            if client is None:
                info["error"] = "Docker SDK not installed"
                self._runtime_info = info
                return info
            version_info = client.version()
            info["available"] = True
            info["version"] = version_info.get("ServerVersion", "unknown")
            server = version_info.get("ServerVersion", "")
            if "orbstack" in server.lower():
                info["runtime"] = "orbstack"
            elif "podman" in server.lower():
                info["runtime"] = "podman"
            else:
                info["runtime"] = "docker"
        except Exception as e:
            info["error"] = str(e)
        self._runtime_info = info
        return info

    def describe(self) -> dict[str, object]:
        runtime = self.detect_runtime()
        return {
            "provider_id": self.provider_id,
            "available": runtime["available"],
            "runtime": runtime["runtime"],
            "version": runtime.get("version", ""),
            "image": self.config.image,
            "network_disabled": self.config.network_disabled,
            "mem_limit": self.config.mem_limit,
            "cpu_quota": self.config.cpu_quota,
        }

    def _get_client(self) -> Any:
        """Get Docker client, returning None if SDK not installed."""
        if self._client is not None:
            return self._client
        try:
            import docker
            self._client = docker.from_env()
            return self._client
        except ImportError:
            log.debug("Docker SDK not installed")
            return None
        except Exception as e:
            log.warning("Docker client init failed: %s", e)
            return None
