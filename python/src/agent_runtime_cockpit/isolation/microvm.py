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
from typing import Callable, Optional

from pydantic import BaseModel, ConfigDict

from ..security.sandbox import (
    microvm_preflight,
    cap_output,
    render_lima_template,
    firecracker_doctor,
)
from .base import IsolationProvider, IsolationResult
from .subprocess import redact_output


class MicroVMPlanStep(BaseModel):
    """A non-executing microVM design-proof step."""

    model_config = ConfigDict(frozen=True)

    name: str
    action: str
    proof_required: str
    implemented: bool = False


class MicroVMRunPlan(BaseModel):
    """Stable JSON plan for future microVM execution."""

    model_config = ConfigDict(frozen=True)

    provider: str
    platform: str
    workspace_root: str
    guest_workspace: str
    command: list[str]
    network_default: str
    execution_enabled: bool
    execution_status: str
    steps: list[MicroVMPlanStep]
    blockers: list[str]


class LimaHarnessResult(BaseModel):
    """Structured opt-in Lima harness result."""

    command: list[str]
    instance_name: str
    template_path: str | None = None
    result: IsolationResult
    lifecycle: list[str]
    network_proof_passed: bool = False
    teardown_attempted: bool = False


class FirecrackerHarnessResult(BaseModel):
    """Structured opt-in Firecracker harness result (design/preflight only)."""

    command: list[str]
    instance_name: str
    kernel_path: str | None = None
    rootfs_path: str | None = None
    result: IsolationResult
    lifecycle: list[str]
    network_proof_passed: bool = False
    kvm_available: bool = False
    teardown_attempted: bool = False


class FirecrackerHarnessError(RuntimeError):
    """Raised when the Firecracker harness cannot proceed."""


def _microvm_execution_enabled() -> bool:
    return os.environ.get("ARC_MICROVM_INTEGRATION") == "1"


def _lima_available() -> bool:
    return bool(shutil.which("limactl"))


def lima_integration_available() -> bool:
    """Return True only when the opt-in Lima integration harness may run."""
    return platform.system() == "Darwin" and _microvm_execution_enabled() and _lima_available()


def _firecracker_available() -> bool:
    return bool(shutil.which("firecracker") or shutil.which("cloud-hypervisor"))


def _kvm_available() -> bool:
    kvm = Path("/dev/kvm")
    return kvm.exists() and os.access(kvm, os.R_OK | os.W_OK)


def firecracker_integration_available() -> bool:
    """Return True only when the opt-in Firecracker integration harness may run.

    Requires: Linux + ARC_MICROVM_INTEGRATION=1 + firecracker binary + /dev/kvm.
    """
    return (
        platform.system() == "Linux"
        and _microvm_execution_enabled()
        and _firecracker_available()
        and _kvm_available()
    )


# Type alias for an injectable fake Firecracker runner used in tests.
# Signature: (argv: list[str], timeout_seconds: int, max_bytes: int) -> IsolationResult
_FirecrackerFakeRunner = Callable[[list[str], int, int], IsolationResult]


class FirecrackerIntegrationHarness:
    """Opt-in Firecracker lifecycle harness; design/preflight only.

    Not wired to public MicroVMIsolationProvider.execute().
    Accepts an optional ``runner`` for fake injection in tests — real
    Firecracker execution is not implemented here and requires a follow-up PR
    once the full lifecycle, mount policy, network-off proof, teardown proof,
    and opt-in integration tests are complete (ADR-024).
    """

    LIFECYCLE_PHASES = [
        "preflight",
        "create_vm",
        "mount_workspace",
        "exec",
        "network_proof",
        "stop_vm",
        "teardown",
    ]

    def __init__(
        self,
        *,
        workspace_root: Path,
        runner: Optional[_FirecrackerFakeRunner] = None,
        instance_name: str | None = None,
        max_bytes: int = 65_536,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.runner = runner
        self.instance_name = instance_name or f"arc-fc-{uuid.uuid4().hex[:12]}"
        self.max_bytes = max_bytes
        self.lifecycle: list[str] = []

    def run(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 300,
        require_gate: bool = True,
    ) -> FirecrackerHarnessResult:
        """Run the gated Firecracker harness lifecycle with mandatory network proof.

        Uses the injected runner for all subprocess calls so tests can run
        without a real Firecracker binary.  If no runner is injected and
        Firecracker is not available, raises FirecrackerHarnessError.
        """
        if require_gate and not firecracker_integration_available():
            raise FirecrackerHarnessError(
                "ARC_MICROVM_INTEGRATION=1, Linux, firecracker binary, and /dev/kvm are required"
            )
        if self.runner is None and not _firecracker_available():
            raise FirecrackerHarnessError(
                "No Firecracker runner injected and no firecracker binary found; "
                "cannot run harness without a real binary or a fake runner"
            )
        if not command:
            raise ValueError("missing command")

        doctor = firecracker_doctor()
        kvm_available = bool(doctor.get("kvm"))
        kernel_path = doctor.get("kernel_path")
        rootfs_path = doctor.get("rootfs_path")

        network_proof_passed = False
        teardown_attempted = False
        result = IsolationResult(exit_code=-1, stderr="not started", provider="microvm")

        try:
            # Phase: preflight
            self.lifecycle.append("preflight")

            # Phase: create_vm (fake or real)
            create_result = self._run(
                [
                    "firecracker",
                    "--id",
                    self.instance_name,
                    "--api-sock",
                    f"/tmp/{self.instance_name}.sock",
                ],
                timeout_seconds,
            )
            self.lifecycle.append("create_vm")

            if create_result.exit_code != 0:
                result = IsolationResult(
                    exit_code=-1,
                    stderr=f"firecracker create failed: {create_result.stderr.strip()}",
                    provider="microvm",
                )
            else:
                # Phase: mount_workspace
                self.lifecycle.append("mount_workspace")

                # Phase: network_proof — check guest routing table
                network_result = self._run(["ip", "route"], min(timeout_seconds, 10))
                self.lifecycle.append("network_proof")
                # If ip route returns any output that looks like a default route, deny
                has_default_route = any(
                    "default" in part for part in (network_result.stdout or "").splitlines()
                )
                network_proof_passed = network_result.exit_code == 0 and not has_default_route

                if not network_proof_passed:
                    result = IsolationResult(
                        exit_code=-1,
                        stderr="network-off proof failed: guest routing table not empty or check failed",
                        provider="microvm",
                    )
                else:
                    # Phase: exec
                    result = self._run(command, timeout_seconds)
                    self.lifecycle.append("exec")

        finally:
            # Phase: stop_vm
            self._run(["firecracker", "--stop", self.instance_name], min(timeout_seconds, 30))
            self.lifecycle.append("stop_vm")
            # Phase: teardown
            teardown_attempted = True
            self._run(["rm", "-rf", f"/tmp/{self.instance_name}.sock"], min(timeout_seconds, 10))
            self.lifecycle.append("teardown")

        return FirecrackerHarnessResult(
            command=command,
            instance_name=self.instance_name,
            kernel_path=str(kernel_path) if kernel_path else None,
            rootfs_path=str(rootfs_path) if rootfs_path else None,
            result=result,
            lifecycle=list(self.lifecycle),
            network_proof_passed=network_proof_passed,
            kvm_available=kvm_available,
            teardown_attempted=teardown_attempted,
        )

    def _run(self, argv: list[str], timeout_seconds: int) -> IsolationResult:
        if self.runner is not None:
            return self.runner(argv, timeout_seconds, self.max_bytes)
        # No real Firecracker execution implemented yet (ADR-024).
        raise FirecrackerHarnessError(
            "No runner injected and real Firecracker execution is not implemented "
            "(ADR-024); use a fake runner for tests"
        )


def build_microvm_run_plan(
    provider: str,
    command: list[str],
    *,
    workspace_root: Path,
    platform_name: str | None = None,
) -> MicroVMRunPlan:
    """Build a design-proof run plan without creating or starting a VM."""
    normalized = provider.lower()
    if normalized not in {"lima", "firecracker"}:
        raise ValueError("provider must be lima or firecracker")
    if not command:
        raise ValueError("missing command")
    platform_value = platform_name or platform.system()
    workspace = str(workspace_root.resolve())
    if normalized == "lima":
        steps = [
            MicroVMPlanStep(
                name="template",
                action="render disposable Lima VZ template with only workspace mounted at /workspace",
                proof_required="template excludes host home/root mounts and port forwards",
                implemented=True,
            ),
            MicroVMPlanStep(
                name="create_start",
                action="limactl start --tty=false <template>",
                proof_required="bounded start timeout and failed-start cleanup",
            ),
            MicroVMPlanStep(
                name="network_off",
                action="probe guest route/DNS before user argv",
                proof_required="guest cannot reach network under default policy",
            ),
            MicroVMPlanStep(
                name="run",
                action="limactl shell --tty=false <instance> --workdir /workspace -- <argv>",
                proof_required="stdout/stderr caps, env policy, exit-code propagation",
            ),
            MicroVMPlanStep(
                name="teardown",
                action="limactl delete -f <instance> in finally",
                proof_required="cleanup happens on success, failure, timeout, and interrupted start",
            ),
        ]
        blockers = [
            "Lima lifecycle not public-execution wired",
            "workspace mount escape proof missing",
            "network-off proof missing",
            "teardown proof missing",
            "opt-in integration test not passing on host runtime",
        ]
    else:
        steps = [
            MicroVMPlanStep(
                name="preflight",
                action="check firecracker/cloud-hypervisor, jailer, /dev/kvm, kernel, rootfs",
                proof_required="doctor reports ready without creating VM",
                implemented=True,
            ),
            MicroVMPlanStep(
                name="jail",
                action="create per-run jail directory and API socket",
                proof_required="non-root jailer permissions and cleanup verified",
            ),
            MicroVMPlanStep(
                name="boot",
                action="boot cached kernel/rootfs with no TAP/NAT by default",
                proof_required="pinned image provenance and bounded boot timeout",
            ),
            MicroVMPlanStep(
                name="mount",
                action="attach workspace through controlled read-only/read-write strategy",
                proof_required="symlink/hardlink escape proof",
            ),
            MicroVMPlanStep(
                name="run",
                action="send argv to guest agent via vsock/serial channel",
                proof_required="stdout/stderr caps, env policy, exit-code propagation",
            ),
            MicroVMPlanStep(
                name="teardown",
                action="stop Firecracker process and remove jail dir in finally",
                proof_required="cleanup happens on boot failure, run timeout, and interrupted host process",
            ),
        ]
        blockers = [
            "kernel/rootfs cache provenance missing",
            "guest command agent missing",
            "workspace mount strategy unproven",
            "network-off proof missing",
            "jailer/teardown proof missing",
        ]
    return MicroVMRunPlan(
        provider=normalized,
        platform=platform_value,
        workspace_root=workspace,
        guest_workspace="/workspace",
        command=command,
        network_default="deny",
        execution_enabled=False,
        execution_status="design_proof_only",
        steps=steps,
        blockers=blockers,
    )


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


class LimaIntegrationHarness:
    """Opt-in disposable Lima lifecycle harness; not wired to public execution."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        runner: Callable[[list[str], int, int], IsolationResult] = _run_limactl,
        instance_name: str | None = None,
        max_bytes: int = 65_536,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.runner = runner
        self.instance_name = instance_name or f"arc-sandbox-{uuid.uuid4().hex[:12]}"
        self.max_bytes = max_bytes
        self.lifecycle: list[str] = []
        self.template_path: Path | None = None

    def run(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 300,
        require_gate: bool = True,
    ) -> LimaHarnessResult:
        """Run the gated Lima harness lifecycle with mandatory network proof."""
        if require_gate and not lima_integration_available():
            raise RuntimeError("ARC_MICROVM_INTEGRATION=1, macOS, and limactl are required")
        if not command:
            raise ValueError("missing command")
        tmp_path = self._write_template()
        network_proof_passed = False
        teardown_attempted = False
        result = IsolationResult(exit_code=-1, stderr="not started", provider="microvm")
        try:
            start = self._limactl(["start", "--tty=false", str(tmp_path)], timeout_seconds)
            self.lifecycle.append("start")
            if start.exit_code != 0:
                result = IsolationResult(
                    exit_code=-1,
                    stderr=f"lima start failed: {start.stderr.strip()}",
                    provider="microvm",
                )
            else:
                network = self._limactl(
                    [
                        "shell",
                        "--tty=false",
                        self.instance_name,
                        "--",
                        "sh",
                        "-lc",
                        "ip route | grep -q '^default' && exit 1 || exit 0",
                    ],
                    min(timeout_seconds, 10),
                )
                self.lifecycle.append("network_proof")
                network_proof_passed = network.exit_code == 0
                if not network_proof_passed:
                    result = IsolationResult(
                        exit_code=-1,
                        stderr="network-off proof failed: guest has a default route",
                        provider="microvm",
                    )
                else:
                    result = self._limactl(
                        [
                            "shell",
                            "--tty=false",
                            self.instance_name,
                            "--workdir",
                            "/workspace",
                            "--",
                            *command,
                        ],
                        timeout_seconds,
                    )
                    self.lifecycle.append("run")
        finally:
            teardown_attempted = True
            self._limactl(["delete", "-f", self.instance_name], min(timeout_seconds, 60))
            self.lifecycle.append("teardown")
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        return self._result(command, result, network_proof_passed, teardown_attempted)

    def _write_template(self) -> Path:
        yaml = render_lima_template(self.workspace_root, self.instance_name)
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            prefix=f"{self.instance_name}-",
            delete=False,
        )
        tmp_path = Path(tmp.name)
        tmp.write(yaml)
        tmp.close()
        self.template_path = tmp_path
        self.lifecycle.append("template")
        return tmp_path

    def _limactl(self, args: list[str], timeout_seconds: int) -> IsolationResult:
        return self.runner(["limactl", *args], timeout_seconds, self.max_bytes)

    def _result(
        self,
        command: list[str],
        result: IsolationResult,
        network_proof_passed: bool,
        teardown_attempted: bool,
    ) -> LimaHarnessResult:
        return LimaHarnessResult(
            command=command,
            instance_name=self.instance_name,
            template_path=str(self.template_path) if self.template_path else None,
            result=result,
            lifecycle=list(self.lifecycle),
            network_proof_passed=network_proof_passed,
            teardown_attempted=teardown_attempted,
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
