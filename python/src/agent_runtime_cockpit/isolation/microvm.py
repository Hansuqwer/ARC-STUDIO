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
    build_microvm_audit_event,
    microvm_preflight,
    cap_output,
    render_lima_template,
    firecracker_doctor,
    check_workspace_escape,
    persist_sandbox_audit_event,
    utc_now,
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


class FirecrackerNoNetworkConfig(BaseModel):
    """Design-proof Firecracker config with no guest NICs configured."""

    model_config = ConfigDict(frozen=True)

    api_socket: str
    config_path: str
    kernel_image_path: str
    rootfs_path: str
    boot_args: str = "console=ttyS0 reboot=k panic=1 pci=off"
    vcpu_count: int = 1
    mem_size_mib: int = 256
    strict_network_candidate: bool = True
    strict_network_proof: str = "not_proven"
    network_interfaces_configured: bool = False

    def to_firecracker_config(self) -> dict[str, object]:
        """Return Firecracker config-file JSON without network interfaces."""
        return {
            "boot-source": {
                "kernel_image_path": self.kernel_image_path,
                "boot_args": self.boot_args,
            },
            "drives": [
                {
                    "drive_id": "rootfs",
                    "path_on_host": self.rootfs_path,
                    "is_root_device": True,
                    "is_read_only": False,
                }
            ],
            "machine-config": {
                "vcpu_count": self.vcpu_count,
                "mem_size_mib": self.mem_size_mib,
                "smt": False,
            },
        }


class FirecrackerNoNetworkRunPlan(BaseModel):
    """Non-executing strict no-network proof plan for Firecracker."""

    model_config = ConfigDict(frozen=True)

    command: list[str]
    proof_commands: list[list[str]]
    config: FirecrackerNoNetworkConfig
    teardown_actions: list[str]
    host_gates: list[str]
    execution_status: str = "design_proof_only"
    real_boot_attempted: bool = False


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
    strict_network_candidate: bool = True
    strict_network_proof: str = "not_proven"
    network_interfaces_configured: bool = False
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


def firecracker_real_exec_available() -> bool:
    """Return True only when the host-gated real Firecracker proof may run."""
    return (
        firecracker_integration_available()
        and os.environ.get("ARC_FC_REAL_EXEC") == "1"
        and bool(os.environ.get("ARC_FIRECRACKER_KERNEL"))
        and bool(os.environ.get("ARC_FIRECRACKER_ROOTFS"))
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
        # Check before resolving: reject workspace_root symlinks pointing outside parent.
        check_workspace_escape(workspace_root, workspace_root.parent)
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
        started_at = utc_now()
        if require_gate and not firecracker_integration_available():
            result = FirecrackerHarnessResult(
                command=command,
                instance_name=self.instance_name,
                result=IsolationResult(
                    exit_code=-1,
                    stderr=(
                        "ARC_MICROVM_INTEGRATION=1, Linux, firecracker binary, "
                        "and /dev/kvm are required"
                    ),
                    provider="microvm",
                ),
                lifecycle=["preflight"],
            )
            self._persist_audit_event(result, started_at, utc_now())
            raise FirecrackerHarnessError(result.result.stderr)
        if self.runner is None and not firecracker_real_exec_available():
            result = FirecrackerHarnessResult(
                command=command,
                instance_name=self.instance_name,
                result=IsolationResult(
                    exit_code=-1,
                    stderr=(
                        "real Firecracker run is blocked until ARC_MICROVM_INTEGRATION=1, "
                        "ARC_FC_REAL_EXEC=1, Linux, /dev/kvm, firecracker, kernel, and rootfs "
                        "are present; public microVM execution remains disabled (ADR-024)"
                    ),
                    provider="microvm",
                ),
                lifecycle=["preflight"],
            )
            self._persist_audit_event(result, started_at, utc_now())
            raise FirecrackerHarnessError(result.result.stderr)
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

        harness_result = FirecrackerHarnessResult(
            command=command,
            instance_name=self.instance_name,
            kernel_path=str(kernel_path) if kernel_path else None,
            rootfs_path=str(rootfs_path) if rootfs_path else None,
            result=result,
            lifecycle=list(self.lifecycle),
            network_proof_passed=network_proof_passed,
            strict_network_candidate=True,
            strict_network_proof="host_gated" if self.runner is None else "not_proven",
            network_interfaces_configured=False,
            kvm_available=kvm_available,
            teardown_attempted=teardown_attempted,
        )
        self._persist_audit_event(harness_result, started_at, utc_now())
        return harness_result

    def _run(self, argv: list[str], timeout_seconds: int) -> IsolationResult:
        if self.runner is not None:
            return self.runner(argv, timeout_seconds, self.max_bytes)
        # No real Firecracker execution implemented yet (ADR-024).
        raise FirecrackerHarnessError(
            "No runner injected and real Firecracker execution is not implemented "
            "(ADR-024); use a fake runner for tests"
        )

    def _persist_audit_event(
        self, result: FirecrackerHarnessResult, started_at: str, ended_at: str
    ) -> None:
        event = build_microvm_audit_event(
            command=result.command,
            workspace_root=self.workspace_root,
            provider_runtime="firecracker",
            instance_name=result.instance_name,
            lifecycle=result.lifecycle,
            network_proof_passed=result.network_proof_passed,
            teardown_attempted=result.teardown_attempted,
            started_at=started_at,
            ended_at=ended_at,
            exit_code=result.result.exit_code,
            stdout_truncated=result.result.stdout_truncated,
            stderr_truncated=result.result.stderr_truncated,
            redaction_applied=result.result.redaction_applied,
        )
        persist_sandbox_audit_event(event)


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


def build_firecracker_no_network_run_plan(
    command: list[str],
    *,
    kernel_path: Path,
    rootfs_path: Path,
    work_dir: Path,
    instance_name: str | None = None,
) -> FirecrackerNoNetworkRunPlan:
    """Build a non-executing Firecracker no-NIC proof plan."""
    if not command:
        raise ValueError("missing command")
    name = instance_name or f"arc-fc-{uuid.uuid4().hex[:12]}"
    api_socket = work_dir / f"{name}.socket"
    config_path = work_dir / f"{name}.json"
    config = FirecrackerNoNetworkConfig(
        api_socket=str(api_socket),
        config_path=str(config_path),
        kernel_image_path=str(kernel_path),
        rootfs_path=str(rootfs_path),
    )
    return FirecrackerNoNetworkRunPlan(
        command=command,
        proof_commands=[
            ["ip", "route"],
            ["curl", "--connect-timeout", "2", "https://example.com"],
        ],
        config=config,
        teardown_actions=[
            "terminate firecracker process group",
            "remove api socket",
            "remove temporary work directory",
        ],
        host_gates=[
            "Linux",
            "ARC_MICROVM_INTEGRATION=1",
            "ARC_FC_REAL_EXEC=1",
            "ARC_FIRECRACKER_KERNEL",
            "ARC_FIRECRACKER_ROOTFS",
            "firecracker binary",
            "/dev/kvm read/write",
        ],
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
    """Opt-in disposable Lima lifecycle harness; not wired to public execution.

    Network isolation note (2026-05-26):
      Lima 2.x always provides a default user-mode slirp network (192.168.5.0/24)
      to the guest. There is no known Lima 2.1.0 template config to fully disable
      this. The network_proof step checks for a default route — on a real Lima VM
      this check will report the slirp route exists (network_proof_passed=False).
      This is a KNOWN LIMITATION: full network-off is not achievable with Lima 2.x
      default config. P2 (network-off proof) in ADR-024 remains blocked until a
      Lima config that disables the slirp interface is found or Lima adds support.
      See docs/research/sandbox-and-microvm.md Step 1–5 research notes.
    """

    def __init__(
        self,
        *,
        workspace_root: Path,
        runner: Optional[Callable[[list[str], int, int], IsolationResult]] = None,
        instance_name: str | None = None,
        max_bytes: int = 65_536,
    ) -> None:
        # Check before resolving: if workspace_root is a symlink pointing outside
        # its own parent, reject immediately.
        check_workspace_escape(workspace_root, workspace_root.parent)
        self.workspace_root = workspace_root.resolve()
        # runner=None → use the real _run_limactl binary; inject a fake for tests.
        self.runner = runner if runner is not None else _run_limactl
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
        started_at = utc_now()
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
        harness_result = self._result(command, result, network_proof_passed, teardown_attempted)
        self._persist_audit_event(harness_result, started_at, utc_now())
        return harness_result

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

    def _persist_audit_event(
        self, result: LimaHarnessResult, started_at: str, ended_at: str
    ) -> None:
        event = build_microvm_audit_event(
            command=result.command,
            workspace_root=self.workspace_root,
            provider_runtime="lima",
            instance_name=result.instance_name,
            lifecycle=result.lifecycle,
            network_proof_passed=result.network_proof_passed,
            teardown_attempted=result.teardown_attempted,
            started_at=started_at,
            ended_at=ended_at,
            exit_code=result.result.exit_code,
            stdout_truncated=result.result.stdout_truncated,
            stderr_truncated=result.result.stderr_truncated,
            redaction_applied=result.result.redaction_applied,
        )
        persist_sandbox_audit_event(event)


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

    Public execution (execute()) always raises NotImplementedError until all
    prerequisites in ADR-024 (docs/adr/ADR-024-microvm-public-execution-contract.md)
    are satisfied and ARC_MICROVM_EXEC_ENABLED=1 is set.

    Use doctor/preflight/harness surfaces instead.
    """

    @property
    def provider_id(self) -> str:
        return "microvm"

    @property
    def name(self) -> str:
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
            "microVM execution not yet available — prerequisites P1–P7 in "
            "docs/adr/ADR-024-microvm-public-execution-contract.md must be satisfied "
            "and ARC_MICROVM_EXEC_ENABLED=1 must be set before this path is enabled "
            f"(platform={platform.system()})"
        )

    def status(self) -> dict[str, object]:
        """Return structured status dict for truth-guard checks and CLI output."""
        return {
            "available": False,
            "reason": "execution_not_implemented",
            "contract_doc": "docs/adr/ADR-024-microvm-public-execution-contract.md",
            "strict_network_isolation": False,
            "lima_security_posture": "low_security_network_present",
            "lima_harness": lima_integration_available(),
            "firecracker_harness": firecracker_integration_available(),
            "unblock_gate": "ARC_MICROVM_EXEC_ENABLED=1 (not yet honored)",
        }

    def describe(self) -> dict[str, object]:
        info = microvm_preflight()
        if _microvm_execution_enabled() and _lima_available():
            info["execution"] = "gated_unproven"
            info["reason"] = (
                "ARC_MICROVM_INTEGRATION=1 is set and limactl is present, but public "
                "microVM execution remains disabled until ADR-024 prerequisites are met"
            )
        return info
