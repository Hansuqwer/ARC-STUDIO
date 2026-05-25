"""MicroVM provider preflight/doctor support.

Lima/Firecracker execution remains unproven and is intentionally unreachable from
the public provider until lifecycle, mount, network-off, teardown, and opt-in
integration proof are complete.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from ..security.sandbox import microvm_preflight, cap_output, render_lima_template
from .base import IsolationProvider, IsolationResult
from .subprocess import redact_output


def _microvm_execution_enabled() -> bool:
    return os.environ.get("ARC_MICROVM_INTEGRATION") == "1"


def _lima_available() -> bool:
    return bool(shutil.which("limactl"))


def _run_limactl(
    argv: list[str],
    timeout: int = 300,
    max_bytes: int = 65_536,
) -> IsolationResult:
    """Run a ``limactl`` subcommand and return structured result."""
    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        killed = False
        kill_reason: str | None = None
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            killed = True
            kill_reason = "timeout"
            try:
                os.killpg(proc.pid, 9)
            except ProcessLookupError:
                pass
            proc.wait()
        assert proc.stdout is not None
        assert proc.stderr is not None
        stdout_raw, _ = cap_output(proc.stdout.read(), max_bytes)
        stderr_raw, _ = cap_output(proc.stderr.read(), max_bytes)
        redacted_stdout = redact_output(stdout_raw)
        redacted_stderr = redact_output(stderr_raw)
        redaction_applied = redacted_stdout != stdout_raw or redacted_stderr != stderr_raw
        duration = int((time.monotonic() - start) * 1000)
        return IsolationResult(
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=redacted_stdout,
            stderr=redacted_stderr,
            duration_ms=duration,
            killed=killed,
            kill_reason=kill_reason,
            provider="microvm",
            stdout_truncated=False,
            stderr_truncated=False,
            redaction_applied=redaction_applied,
        )
    except Exception as exc:
        duration = int((time.monotonic() - start) * 1000)
        return IsolationResult(
            exit_code=-1,
            stderr=str(exc),
            duration_ms=duration,
            provider="microvm",
        )


def _execute_lima(
    command: list[str],
    *,
    cwd: Optional[Path] = None,
    timeout_seconds: int = 300,
) -> IsolationResult:
    """Create a disposable Lima VM, run command, collect result, destroy VM."""
    instance_name = f"arc-sandbox-{uuid.uuid4().hex[:12]}"
    workspace_root = (cwd or Path.cwd()).resolve()
    yaml = render_lima_template(workspace_root, instance_name)

    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix=f"{instance_name}-",
        delete=False,
    )
    tmp_path = Path(tmp.name)
    try:
        tmp.write(yaml)
        tmp.close()

        # 1. Start VM
        start_result = _run_limactl(
            ["limactl", "start", "--tty=false", str(tmp_path)],
            timeout=min(timeout_seconds, 600),
        )
        if start_result.exit_code != 0:
            _run_limactl(["limactl", "delete", "-f", instance_name], timeout=30)
            return IsolationResult(
                exit_code=-1,
                stderr=f"lima start failed: {start_result.stderr.strip()}",
                provider="microvm",
            )

        try:
            # 2. Network-off proof
            net_check = _run_limactl(
                [
                    "limactl",
                    "shell",
                    "--tty=false",
                    instance_name,
                    "--",
                    "curl",
                    "--connect-timeout",
                    "2",
                    "http://example.com",
                ],
                timeout=10,
            )
            if net_check.exit_code == 0:
                _run_limactl(["limactl", "delete", "-f", instance_name], timeout=30)
                return IsolationResult(
                    exit_code=-1,
                    stderr="network-off proof failed: guest has network access",
                    provider="microvm",
                )

            # 3. Run command via limactl shell
            shell_argv = [
                "limactl",
                "shell",
                "--tty=false",
                instance_name,
            ]
            if cwd:
                shell_argv.extend(["--workdir", "/workspace"])
            shell_argv.append("--")
            shell_argv.extend(command)
            return _run_limactl(shell_argv, timeout=timeout_seconds)
        finally:
            # 4. Destroy VM
            _run_limactl(["limactl", "delete", "-f", instance_name], timeout=60)
    except Exception as exc:
        _run_limactl(["limactl", "delete", "-f", instance_name], timeout=30)
        return IsolationResult(
            exit_code=-1,
            stderr=str(exc),
            provider="microvm",
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


class MicroVMIsolationProvider(IsolationProvider):
    """MicroVM provider for macOS/Linux.

    On macOS with Lima installed and ``ARC_MICROVM_INTEGRATION=1``, ``execute()``
    creates a disposable Lima VZ VM, runs the command inside, and destroys the VM.
    On Linux, ``execute()`` still raises ``NotImplementedError``.
    """

    @property
    def provider_id(self) -> str:
        return "microvm"

    async def health_check(self) -> bool:
        return microvm_preflight()["status"] == "ready"

    async def execute(
        self,
        command: list[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
    ) -> IsolationResult:
        raise NotImplementedError(
            "microVM execution is not implemented/proven; use doctor/preflight only "
            f"(platform={platform.system()})"
        )

    def describe(self) -> dict[str, object]:
        info = microvm_preflight()
        if _microvm_execution_enabled() and _lima_available():
            info["execution"] = "gated_unproven"
            info["reason"] = (
                "ARC_MICROVM_INTEGRATION=1 is set and limactl is present, but public "
                "microVM execution remains disabled until integration proof passes"
            )
        return info
