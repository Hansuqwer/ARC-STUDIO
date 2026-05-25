"""Docker isolation provider — container-based execution for untrusted workspaces.

Gated by ``ARC_ENABLE_CONTAINER_SANDBOX=1``.
"""

from __future__ import annotations

import gc
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..security.sandbox import cap_output
from .base import IsolationProvider, IsolationResult
from .subprocess import (
    DEFAULT_SAFE_ENV_KEYS,
    _is_blocked_env_key,
    redact_output,
)

log = logging.getLogger(__name__)


class DockerConfig(BaseModel):
    """Configuration for Docker isolation provider."""

    image: str = "python:3.12-slim"
    volumes: dict[str, dict[str, str]] = Field(default_factory=dict)
    network_disabled: bool = True
    mem_limit: str = "512m"
    cpu_quota: int = 50000
    environment: dict[str, str] = Field(default_factory=dict)
    max_output_bytes: int = 65_536
    safe_env_keys: tuple[str, ...] = tuple(DEFAULT_SAFE_ENV_KEYS)


class DockerIsolationProvider(IsolationProvider):
    """Container-based isolation using Docker SDK.

    Detects OrbStack, Podman, Colima via DOCKER_HOST or daemon info.
    Falls back gracefully if Docker SDK is not installed or daemon unreachable.

    Hardening mirroring subprocess provider:
    - env allowlist + secret-key stripping
    - output redaction
    - bounded stdout/stderr capture
    - workspace cwd guard
    """

    def __init__(
        self,
        config: Optional[DockerConfig] = None,
        workspace_root: Optional[Path] = None,
    ) -> None:
        self.config = config or DockerConfig()
        self._client: Any = None
        self._runtime_info: Optional[dict[str, Any]] = None
        self._workspace_root = workspace_root

    @property
    def provider_id(self) -> str:
        return "docker"

    async def health_check(self) -> bool:
        """Return True if Docker daemon is reachable."""
        if not container_sandbox_enabled():
            return False
        try:
            client = self._get_client()
            if client is None:
                return False
            version = client.version()
            log.debug("Docker daemon reachable: %s", version.get("ServerVersion", "unknown"))
            return True
        except Exception as e:
            log.warning("Docker health check failed: %s", e)
            self.close()
            return False

    def _filter_env(self, extra_env: Optional[dict[str, str]] = None) -> dict[str, str]:
        """Filter env to allowlist + strip secrets, matching subprocess provider."""
        result: dict[str, str] = {}
        safe_keys = set(self.config.safe_env_keys)
        for key in safe_keys:
            if key in os.environ and not _is_blocked_env_key(key):
                result[key] = os.environ[key]
        if extra_env:
            for key, value in extra_env.items():
                if key in safe_keys and not _is_blocked_env_key(key):
                    result[key] = value
        return result

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        """Execute a command inside a Docker container."""
        if not container_sandbox_enabled():
            return IsolationResult(
                exit_code=-1,
                stderr="Container sandbox disabled. Set ARC_ENABLE_CONTAINER_SANDBOX=1 to enable.",
                provider=self.provider_id,
            )
        client = self._get_client()
        if client is None:
            return IsolationResult(
                exit_code=-1,
                stderr="Docker SDK not installed. Install with: pip install docker",
                provider=self.provider_id,
            )
        if self._workspace_root and cwd:
            root = self._workspace_root.resolve()
            resolved = cwd.resolve()
            if cwd.is_symlink() or not resolved.is_relative_to(root):
                raise ValueError(f"cwd escapes workspace: {cwd}")
        merged_env = {**self.config.environment, **self._filter_env(env)}
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
                try:
                    container.kill()
                except Exception:
                    pass
                duration = int((time.monotonic() - start) * 1000)
                return IsolationResult(
                    exit_code=-1,
                    stdout="",
                    stderr="container timeout",
                    duration_ms=duration,
                    killed=True,
                    kill_reason="timeout",
                    provider=self.provider_id,
                )
            max_bytes = self.config.max_output_bytes
            logs_raw = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            stdout, stdout_truncated = cap_output(logs_raw, max_bytes)
            redacted_stdout = redact_output(stdout)
            redaction_applied = redacted_stdout != stdout
            duration = int((time.monotonic() - start) * 1000)
            return IsolationResult(
                exit_code=exit_code,
                stdout=redacted_stdout,
                stderr="",
                duration_ms=duration,
                provider=self.provider_id,
                stdout_truncated=stdout_truncated,
                redaction_applied=redaction_applied,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            log.error("Docker execution failed: %s", e)
            return IsolationResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration,
                provider=self.provider_id,
            )

    def detect_runtime(self) -> dict[str, Any]:
        """Detect which Docker-compatible runtime is available."""
        if not container_sandbox_enabled():
            return {
                "available": False,
                "runtime": "disabled",
                "error": "ARC_ENABLE_CONTAINER_SANDBOX not set",
            }
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
            self.close()
        self._runtime_info = info
        return info

    def close(self) -> None:
        """Close cached Docker client sockets, if any."""
        client = self._client
        self._client = None
        close = getattr(client, "close", None)
        if callable(close):
            close()
        gc.collect()

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


def container_sandbox_enabled() -> bool:
    """Return True when container execution is explicitly enabled."""
    return os.environ.get("ARC_ENABLE_CONTAINER_SANDBOX") == "1"
