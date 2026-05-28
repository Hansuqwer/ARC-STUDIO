"""Docker isolation provider — container-based execution for untrusted workspaces.

Gated by ``ARC_ENABLE_CONTAINER_SANDBOX=1``.
"""

from __future__ import annotations

import gc
import logging
import os
import tempfile
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


# ---------------------------------------------------------------------------
# SubprocessContainerProvider — CLI subprocess-based container runner
# ---------------------------------------------------------------------------


class SubprocessContainerProvider(IsolationProvider):
    """Container isolation using docker/podman CLI subprocess (no SDK dep).

    Uses ``docker run`` or ``podman run`` via subprocess; avoids a hard
    dependency on the ``docker`` Python package.

    Gated by ``ARC_ENABLE_CONTAINER_SANDBOX=1``.
    """

    def __init__(
        self,
        image: str = "python:3.12-slim",
        workspace_root: Optional[Path] = None,
        max_output_bytes: int = 65_536,
        network_disabled: bool = True,
        mem_limit: str = "512m",
        runtime: Optional[str] = None,  # None = auto-detect
        read_write_workspace: bool = False,
        safe_env_keys: frozenset[str] | None = None,
    ) -> None:
        self._image = image
        self._workspace_root = workspace_root
        self._max_output_bytes = max_output_bytes
        self._network_disabled = network_disabled
        self._mem_limit = mem_limit
        self._runtime_override = runtime
        self._read_write_workspace = read_write_workspace
        self._safe_env_keys = safe_env_keys or DEFAULT_SAFE_ENV_KEYS

    @property
    def provider_id(self) -> str:
        return "container"

    async def health_check(self) -> bool:
        """Return True if container runtime binary is available and sandbox enabled."""
        if not container_sandbox_enabled():
            return False
        info = self.detect_runtime()
        if not info.get("available") or not info.get("binary"):
            return False
        from ..security.sandbox import _container_daemon_alive

        return _container_daemon_alive(str(info["binary"]))

    def detect_runtime(self) -> dict[str, Any]:
        """Detect which container runtime binary is available.

        Returns a dict with:
          - ``runtime``: "docker" | "podman" | "orbstack" | "colima" | "unavailable"
          - ``available``: bool
          - ``binary``: str | None
        """
        import shutil

        docker_bin = shutil.which("docker")
        podman_bin = shutil.which("podman")

        if self._runtime_override:
            binary = shutil.which(self._runtime_override)
            if not binary:
                return {"runtime": "unavailable", "available": False, "binary": None}
            return {"runtime": self._runtime_override, "available": True, "binary": binary}

        if docker_bin:
            # Sniff for OrbStack or Colima via DOCKER_HOST or docker context
            docker_host = os.environ.get("DOCKER_HOST", "")
            if "orbstack" in docker_host.lower():
                runtime_name = "orbstack"
            elif "colima" in docker_host.lower():
                runtime_name = "colima"
            else:
                runtime_name = "docker"
            return {"runtime": runtime_name, "available": True, "binary": docker_bin}

        if podman_bin:
            return {"runtime": "podman", "available": True, "binary": podman_bin}

        return {"runtime": "unavailable", "available": False, "binary": None}

    def _filter_env(self, extra_env: Optional[dict[str, str]] = None) -> list[str]:
        """Return filtered env as list of -e KEY=VAL args for docker run."""
        safe_keys = self._safe_env_keys
        result: list[str] = []
        for key in sorted(safe_keys):
            if key in os.environ and not _is_blocked_env_key(key):
                result.extend(["-e", f"{key}={os.environ[key]}"])
        if extra_env:
            for key, value in sorted(extra_env.items()):
                if key in safe_keys and not _is_blocked_env_key(key):
                    result.extend(["-e", f"{key}={value}"])
        return result

    def _map_cwd_to_container(self, cwd: Optional[Path]) -> str:
        """Map host cwd to its container equivalent under /workspace."""
        if not cwd or not self._workspace_root:
            return "/workspace"
        root = self._workspace_root.resolve()
        resolved = cwd.resolve()
        try:
            rel = resolved.relative_to(root)
            return f"/workspace/{rel}" if str(rel) != "." else "/workspace"
        except ValueError:
            return "/workspace"

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        """Execute a command inside a container via CLI subprocess."""
        import signal
        import subprocess as sp

        if not container_sandbox_enabled():
            return IsolationResult(
                exit_code=-1,
                stderr="Container sandbox disabled. Set ARC_ENABLE_CONTAINER_SANDBOX=1 to enable.",
                provider=self.provider_id,
            )

        if not command:
            raise ValueError("command must not be empty")

        # Workspace cwd guard
        if self._workspace_root and cwd:
            root = self._workspace_root.resolve()
            resolved = cwd.resolve()
            if cwd.is_symlink() or not resolved.is_relative_to(root):
                raise ValueError(f"cwd escapes workspace: {cwd}")

        info = self.detect_runtime()
        if not info.get("available"):
            return IsolationResult(
                exit_code=-1,
                stderr="No container runtime binary found (docker or podman required).",
                provider=self.provider_id,
            )

        binary: str = info["binary"]
        from ..security.sandbox import _container_daemon_alive

        if not _container_daemon_alive(binary):
            return IsolationResult(
                exit_code=-1,
                stderr="Container runtime daemon unavailable or not configured.",
                provider=self.provider_id,
            )

        # Build volume mount: workspace → /workspace
        volume_args: list[str] = []
        if self._workspace_root:
            mode = "rw" if self._read_write_workspace else "ro"
            volume_args = ["-v", f"{self._workspace_root.resolve()}:/workspace:{mode}"]

        container_cwd = self._map_cwd_to_container(cwd)
        env_args = self._filter_env(env)

        network_args = ["--network=none"] if self._network_disabled else []

        fd, cidfile_name = tempfile.mkstemp(prefix="arc-container-", suffix=".cid")
        os.close(fd)
        os.unlink(cidfile_name)
        cidfile_path = Path(cidfile_name)

        argv = (
            [binary, "run", "--rm"]
            + network_args
            + [
                "--cidfile",
                str(cidfile_path),
                f"-m{self._mem_limit}",
                "--cpus=0.5",
                "--security-opt=no-new-privileges:true",
                "--cap-drop=ALL",
                f"-w{container_cwd}",
            ]
            + volume_args
            + env_args
            + ["--", self._image]
            + command
        )

        start = time.monotonic()
        try:
            proc = sp.Popen(
                argv,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                start_new_session=True,
            )
        except FileNotFoundError:
            return IsolationResult(
                exit_code=-1,
                stderr=f"container runtime binary not found: {binary}",
                provider=self.provider_id,
            )

        killed = False
        kill_reason: Optional[str] = None

        assert proc.stdout is not None
        assert proc.stderr is not None

        from .subprocess import _BoundedPipeReader

        stdout_reader = _BoundedPipeReader(proc.stdout, self._max_output_bytes)
        stderr_reader = _BoundedPipeReader(proc.stderr, self._max_output_bytes)
        stdout_reader.start()
        stderr_reader.start()

        try:
            proc.wait(timeout=timeout_seconds)
        except sp.TimeoutExpired:
            killed = True
            kill_reason = "timeout"
            if cidfile_path.exists():
                cid = cidfile_path.read_text(encoding="utf-8").strip()
                if cid:
                    sp.run([binary, "kill", cid], check=False, capture_output=True, timeout=5)
            try:
                import os as _os

                _os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        finally:
            cidfile_path.unlink(missing_ok=True)

        stdout_reader.join()
        stderr_reader.join()

        duration = int((time.monotonic() - start) * 1000)
        stdout = stdout_reader.text()
        stderr = stderr_reader.text()
        stdout_truncated = stdout_reader.truncated
        stderr_truncated = stderr_reader.truncated

        redacted_stdout = redact_output(stdout)
        redacted_stderr = redact_output(stderr)
        redaction_applied = redacted_stdout != stdout or redacted_stderr != stderr

        return IsolationResult(
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=redacted_stdout,
            stderr=redacted_stderr,
            duration_ms=duration,
            pid=proc.pid,
            killed=killed,
            kill_reason=kill_reason,
            provider=self.provider_id,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            redaction_applied=redaction_applied,
        )

    def describe(self) -> dict[str, object]:
        info = self.detect_runtime()
        return {
            "provider_id": self.provider_id,
            "available": container_sandbox_enabled() and info.get("available", False),
            "runtime": info.get("runtime", "unavailable"),
            "binary": info.get("binary"),
            "image": self._image,
            "network_disabled": self._network_disabled,
            "mem_limit": self._mem_limit,
            "enabled": container_sandbox_enabled(),
        }
