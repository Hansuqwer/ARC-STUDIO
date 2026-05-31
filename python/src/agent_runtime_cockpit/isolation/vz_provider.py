"""Apple Virtualization.framework direct no-NIC VM proof provider.

This is not Lima. The proof path requires an explicit gate plus a VZ runner
capable of creating VZVirtualMachineConfiguration with networkDevices = [].
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..security.sandbox import cap_output
from .base import IsolationResult
from .subprocess import _BoundedPipeReader, redact_output


VZ_PROOF_MARKER = "ARC_VZ_PROOF "
VZ_RESULT_MARKER = "ARC_VZ_RESULT "
VZ_MARKERS = [
    "booted",
    "no_guest_ethernet",
    "no_default_route",
    "network_tool_available",
    "network_failure",
    "workspace_mount_proven",
    "sentinel_readable",
    "symlink_escape_blocked",
]

_VZ_PROOF_ALIASES = {
    "booted": "booted",
    "no-guest-ethernet": "no_guest_ethernet",
    "no-default-route": "no_default_route",
    "wget-available": "network_tool_available",
    "network-failure": "network_failure",
    "workspace-mount": "workspace_mount_proven",
    "sentinel-read": "sentinel_readable",
    "symlink-escape-blocked": "symlink_escape_blocked",
}


class VZGuestProof(BaseModel):
    """Guest-emitted no-network/workspace proof markers."""

    model_config = ConfigDict(frozen=True)

    marker_seen: bool = False
    booted: bool = False
    no_guest_ethernet: bool = False
    no_default_route: bool = False
    network_tool_available: bool = False
    network_failure: bool = False
    workspace_mount_proven: bool = False
    sentinel_readable: bool = False
    symlink_escape_blocked: bool = False
    raw: dict[str, str] = Field(default_factory=dict)

    @property
    def network_proof_passed(self) -> bool:
        return (
            self.booted
            and self.no_guest_ethernet
            and self.no_default_route
            and self.network_tool_available
            and self.network_failure
        )

    @property
    def workspace_proof_passed(self) -> bool:
        return (
            self.workspace_mount_proven and self.sentinel_readable and self.symlink_escape_blocked
        )


class VZGuestCommandResult(BaseModel):
    """Guest-emitted command-result marker contract."""

    model_config = ConfigDict(frozen=True)

    marker_seen: bool = False
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    command_sha256: str | None = None
    raw: dict[str, str] = Field(default_factory=dict)


class VZProofResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    booted: bool = False
    command: list[str] = []
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    network_devices_configured: int = 0
    no_nic_configured: bool = False
    no_guest_ethernet: bool = False
    no_default_route: bool = False
    network_failure: bool = False
    network_tool_available: bool = False
    workspace_mount_proven: bool = False
    sentinel_readable: bool = False
    symlink_escape_blocked: bool = False
    command_result_seen: bool = False
    guest_exit_code: int | None = None
    guest_stdout: str = ""
    guest_stderr: str = ""
    teardown_attempted: bool = False
    teardown_ok: bool = False
    proof_markers: dict[str, str] = Field(default_factory=dict)
    proof: str = "not_run"
    blocker: str | None = None


class VZArtifactManifest(BaseModel):
    """Manifest for local Apple VZ proof artifacts."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    generator_version: str = "arc-vz-proof-v1"
    marker_contract_version: int = 1
    artifact: str = "arc-vz-proof"
    generated_at: str
    host_os: str
    host_arch: str
    public_execution_enabled: bool = False
    proof_only: bool = True
    no_downloads: bool = True
    network_devices_configured: int = 0
    networkDevices: list[object] = Field(default_factory=list)
    markers: list[str] = Field(default_factory=lambda: list(VZ_MARKERS))
    source_path: str
    source_sha256: str
    entitlements_path: str
    entitlements_sha256: str
    runner_path: str | None = None
    runner_sha256: str | None = None
    runner_built: bool = False
    runner_signed: bool = False
    kernel_path: str | None = None
    kernel_sha256: str | None = None
    kernel_source_path: str | None = None
    initrd_path: str | None = None
    initrd_sha256: str | None = None
    initrd_source_path: str | None = None
    tools: dict[str, str | None] = Field(default_factory=dict)
    build_status: str
    build_commands: list[list[str]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class VZArtifactReport(BaseModel):
    """Result of VZ proof artifact generation."""

    model_config = ConfigDict(frozen=True)

    manifest_path: str
    source_path: str
    entitlements_path: str
    runner_path: str | None = None
    kernel_path: str | None = None
    initrd_path: str | None = None
    runner_built: bool = False
    runner_signed: bool = False
    blockers: list[str] = Field(default_factory=list)
    manifest: VZArtifactManifest


class VZExecInitManifest(BaseModel):
    """Manifest for the reviewable ARC VZ guest init contract."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    generator_version: str = "arc-vz-exec-init-v1"
    marker_contract_version: int = 1
    artifact: str = "arc-vz-exec-init"
    generated_at: str
    host_os: str
    host_arch: str
    no_downloads: bool = True
    shell_string_execution: bool = False
    argv_transport: str = "ARC_VZ_COMMAND_ARGV_B64CSV"
    command_hash_marker: str = "ARC_VZ_RESULT command_sha256"
    python_runtime_included: bool = False
    markers: list[str] = Field(default_factory=lambda: list(VZ_MARKERS))
    init_path: str
    init_sha256: str
    guest_requirements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class VZExecInitReport(BaseModel):
    """Result of writing the ARC VZ guest init contract."""

    model_config = ConfigDict(frozen=True)

    manifest_path: str
    init_path: str
    blockers: list[str] = Field(default_factory=list)
    manifest: VZExecInitManifest


def vz_public_exec_gates(manifest_path: Path | None = None) -> dict[str, object]:
    """Return public macOS VZ execution gates without starting a VM."""
    manifest_env = os.environ.get("ARC_VZ_ARTIFACT_MANIFEST")
    resolved_manifest = manifest_path or (Path(manifest_env).expanduser() if manifest_env else None)
    blockers: list[str] = []
    manifest: VZArtifactManifest | None = None
    artifact_hashes: dict[str, str | None] = {}
    if platform.system() != "Darwin":
        blockers.append("macOS/Darwin required for Apple Virtualization.framework")
    gates = {
        "ARC_MICROVM_EXEC_ENABLED": os.environ.get("ARC_MICROVM_EXEC_ENABLED") == "1",
        "ARC_MICROVM_INTEGRATION": os.environ.get("ARC_MICROVM_INTEGRATION") == "1",
        "ARC_VZ_REAL_EXEC": os.environ.get("ARC_VZ_REAL_EXEC") == "1",
        "ARC_VZ_ARTIFACT_MANIFEST": bool(resolved_manifest),
    }
    for name, enabled in gates.items():
        if not enabled:
            blockers.append(
                f"{name}=1 required" if name != "ARC_VZ_ARTIFACT_MANIFEST" else f"{name} required"
            )
    manifest_valid = False
    codesign_valid = False
    if resolved_manifest:
        try:
            manifest = validate_vz_artifact_manifest(resolved_manifest.resolve())
            manifest_valid = True
        except Exception as exc:
            blockers.append(f"ARC_VZ_ARTIFACT_MANIFEST invalid: {exc}")
    if manifest:
        artifact_hashes = {
            "source_sha256": manifest.source_sha256,
            "entitlements_sha256": manifest.entitlements_sha256,
            "runner_sha256": manifest.runner_sha256,
            "kernel_sha256": manifest.kernel_sha256,
            "initrd_sha256": manifest.initrd_sha256,
        }
        if not manifest.runner_built:
            blockers.append("VZ runner was not built in manifest")
        if not manifest.runner_signed:
            blockers.append("VZ runner was not signed in manifest")
        if not manifest.runner_path or not _executable_file(Path(manifest.runner_path)):
            blockers.append("manifest VZ runner missing/not executable")
        if not manifest.kernel_path or not _readable_file(Path(manifest.kernel_path)):
            blockers.append("manifest VZ kernel missing/unreadable")
        if not manifest.initrd_path or not _readable_file(Path(manifest.initrd_path)):
            blockers.append("manifest VZ initrd missing/unreadable")
        if manifest.runner_path:
            codesign_valid = _codesign_verify(Path(manifest.runner_path))
            if not codesign_valid:
                blockers.append("VZ runner codesign verification failed")
    ready = not blockers
    return {
        "provider": "microvm",
        "microvm_provider": "vz",
        "platform": "macos" if platform.system() == "Darwin" else platform.system().lower(),
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "gates": gates,
        "manifest_path": str(resolved_manifest.resolve()) if resolved_manifest else None,
        "manifest_valid": manifest_valid,
        "runner_codesign_valid": codesign_valid,
        "artifact_hashes": artifact_hashes,
        "public_execution_enabled": ready,
        "networkDevices": [] if manifest_valid else None,
        "network_devices_configured": 0 if manifest_valid else None,
        "blockers": blockers,
    }


class VZPublicExecutionRunner:
    """Public macOS VZ runner behind explicit gates and proof markers."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        manifest_path: Path | None = None,
        max_bytes: int = 65_536,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.manifest_path = manifest_path
        self.max_bytes = max_bytes

    def run(
        self, command: list[str], *, cwd: Path | None = None, timeout_seconds: int = 300
    ) -> IsolationResult:
        if not command:
            raise ValueError("missing command")
        gates = vz_public_exec_gates(self.manifest_path)
        if not gates["ready"]:
            raise NotImplementedError(
                "macOS VZ microVM execution blocked: "
                + "; ".join(str(item) for item in gates["blockers"])
                + " (ADR-024)"
            )
        manifest = validate_vz_artifact_manifest(Path(str(gates["manifest_path"])))
        assert manifest.runner_path is not None
        assert manifest.kernel_path is not None
        assert manifest.initrd_path is not None
        resolved_cwd = (cwd or self.workspace_root).resolve()
        if (cwd and cwd.is_symlink()) or not resolved_cwd.is_relative_to(self.workspace_root):
            raise ValueError(f"cwd escapes workspace: {cwd}")
        return self._run_with_manifest(command, manifest, resolved_cwd, gates, timeout_seconds)

    def _run_with_manifest(
        self,
        command: list[str],
        manifest: VZArtifactManifest,
        cwd: Path,
        gates: dict[str, object],
        timeout_seconds: int,
    ) -> IsolationResult:
        start = time.monotonic()
        lifecycle = ["preflight", "workspace_markers"]
        lifecycle_errors: list[str] = []
        sentinel = self.workspace_root / ".arc-vz-sentinel"
        escape = self.workspace_root / ".arc-vz-escape"
        escape_target: Path | None = None
        created_sentinel = False
        created_escape = False
        proc: subprocess.Popen[bytes] | None = None
        try:
            if sentinel.exists() or escape.exists():
                raise ValueError(
                    "proof workspace marker path already exists; refusing to overwrite user files"
                )
            sentinel.write_text("arc-vz-proof\n", encoding="utf-8")
            created_sentinel = True
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix="arc-vz-host-secret-", delete=False
            ) as handle:
                handle.write("arc-vz-host-secret\n")
                escape_target = Path(handle.name)
            escape.symlink_to(escape_target)
            created_escape = True
            argv = [
                str(manifest.runner_path),
                "--kernel",
                str(manifest.kernel_path),
                "--initrd",
                str(manifest.initrd_path),
                "--workspace",
                str(self.workspace_root),
                "--command-sha256",
                _command_sha256(command),
                "--",
                *command,
            ]
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=_vz_runner_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            lifecycle.append("start_vm")
            assert proc.stdout is not None
            assert proc.stderr is not None
            capture_bytes = max(self.max_bytes, 65_536)
            stdout_reader = _BoundedPipeReader(proc.stdout, capture_bytes)
            stderr_reader = _BoundedPipeReader(proc.stderr, capture_bytes)
            stdout_reader.start()
            stderr_reader.start()
            killed = False
            kill_reason: str | None = None
            try:
                proc.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                killed = True
                kill_reason = "timeout"
                lifecycle.append("timeout")
                lifecycle_errors.append(
                    f"VZ proof runner timed out after {timeout_seconds} seconds"
                )
                _terminate_process_group(proc)
            except KeyboardInterrupt:
                killed = True
                kill_reason = "signal"
                lifecycle.append("interrupted")
                lifecycle_errors.append("VZ proof runner interrupted; teardown state unknown")
                _terminate_process_group(proc)
            stdout_reader.join()
            stderr_reader.join()
            stdout_raw = stdout_reader.text()
            stderr_raw = stderr_reader.text()
            return self._result_from_output(
                command=command,
                runner_exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout_raw=stdout_raw,
                stderr_raw=stderr_raw,
                duration_ms=int((time.monotonic() - start) * 1000),
                lifecycle=lifecycle,
                lifecycle_errors=lifecycle_errors,
                gates=gates,
                manifest=manifest,
                killed=killed,
                kill_reason=kill_reason,
                stdout_truncated=stdout_reader.truncated,
                stderr_truncated=stderr_reader.truncated,
            )
        except Exception as exc:
            lifecycle_errors.append(str(exc))
            return IsolationResult(
                exit_code=-1,
                stderr=redact_output(str(exc)),
                duration_ms=int((time.monotonic() - start) * 1000),
                provider="microvm",
                metadata=_vz_metadata(
                    lifecycle=lifecycle,
                    lifecycle_errors=lifecycle_errors,
                    gates=gates,
                    manifest=manifest,
                    proof=parse_vz_guest_proof(""),
                    teardown_attempted=False,
                    teardown_ok=False,
                ),
            )
        finally:
            _terminate_process_group(proc)
            if created_sentinel:
                sentinel.unlink(missing_ok=True)
            if created_escape:
                escape.unlink(missing_ok=True)
            if escape_target:
                escape_target.unlink(missing_ok=True)

    def _result_from_output(
        self,
        *,
        command: list[str],
        runner_exit_code: int,
        stdout_raw: str,
        stderr_raw: str,
        duration_ms: int,
        lifecycle: list[str],
        lifecycle_errors: list[str],
        gates: dict[str, object],
        manifest: VZArtifactManifest,
        killed: bool,
        kill_reason: str | None,
        stdout_truncated: bool,
        stderr_truncated: bool,
    ) -> IsolationResult:
        combined = f"{stdout_raw}\n{stderr_raw}"
        lower = combined.lower()
        proof = parse_vz_guest_proof(combined)
        guest_result = parse_vz_guest_command_result(combined)
        teardown_attempted = "arc_vz_teardown_attempted=1" in lower
        teardown_ok = "arc_vz_teardown_ok=1" in lower
        blockers = _vz_proof_blockers(
            runner_exit_code,
            proof,
            guest_result,
            teardown_attempted=teardown_attempted,
            teardown_ok=teardown_ok,
            expected_command_sha256=_command_sha256(command),
        )
        blockers.extend(lifecycle_errors)
        if proof.network_proof_passed:
            lifecycle.append("network_proof")
        else:
            lifecycle.append("network_proof_failed")
        if proof.workspace_proof_passed:
            lifecycle.append("workspace_proof")
        else:
            lifecycle.append("workspace_proof_failed")
        if guest_result.marker_seen:
            lifecycle.append("exec")
        else:
            lifecycle.append("exec_result_missing")
        lifecycle.append("teardown" if teardown_attempted else "teardown_unknown")
        if blockers:
            stdout, out_cap = cap_output(stdout_raw, self.max_bytes)
            stderr, err_cap = cap_output("; ".join(blockers) or stderr_raw, self.max_bytes)
            redacted_stdout = redact_output(stdout)
            redacted_stderr = redact_output(stderr)
            return IsolationResult(
                exit_code=-1,
                stdout=redacted_stdout,
                stderr=redacted_stderr,
                duration_ms=duration_ms,
                killed=killed,
                kill_reason=kill_reason,
                provider="microvm",
                stdout_truncated=stdout_truncated or out_cap,
                stderr_truncated=stderr_truncated or err_cap,
                redaction_applied=redacted_stdout != stdout or redacted_stderr != stderr,
                metadata=_vz_metadata(
                    lifecycle=lifecycle,
                    lifecycle_errors=blockers,
                    gates=gates,
                    manifest=manifest,
                    proof=proof,
                    teardown_attempted=teardown_attempted,
                    teardown_ok=teardown_ok,
                ),
            )
        stdout, out_cap = cap_output(guest_result.stdout, self.max_bytes)
        stderr, err_cap = cap_output(guest_result.stderr, self.max_bytes)
        redacted_stdout = redact_output(stdout)
        redacted_stderr = redact_output(stderr)
        return IsolationResult(
            exit_code=guest_result.exit_code,
            stdout=redacted_stdout,
            stderr=redacted_stderr,
            duration_ms=duration_ms,
            killed=killed,
            kill_reason=kill_reason,
            provider="microvm",
            stdout_truncated=stdout_truncated or out_cap,
            stderr_truncated=stderr_truncated or err_cap,
            redaction_applied=redacted_stdout != stdout or redacted_stderr != stderr,
            metadata=_vz_metadata(
                lifecycle=lifecycle,
                lifecycle_errors=[] if guest_result.exit_code == 0 else [guest_result.stderr],
                gates=gates,
                manifest=manifest,
                proof=proof,
                teardown_attempted=teardown_attempted,
                teardown_ok=teardown_ok,
            ),
        )


class VZNoNetworkProof:
    """Proves a macOS VZ VM can boot with zero configured NICs."""

    def __init__(
        self,
        *,
        kernel_path: Path | None = None,
        initrd_path: Path | None = None,
        runner_path: Path | None = None,
    ) -> None:
        self.kernel_path = kernel_path or _env_path("ARC_VZ_KERNEL")
        self.initrd_path = initrd_path or _env_path("ARC_VZ_INITRD")
        self.runner_path = runner_path or _env_path("ARC_VZ_RUNNER")

    def preflight(self) -> dict[str, object]:
        system = platform.system()
        version = platform.mac_ver()[0]
        pyobjc = _pyobjc_available()
        runner_exists = bool(self.runner_path and self.runner_path.exists())
        runner_executable = _executable_file(self.runner_path)
        kernel_exists = bool(self.kernel_path and self.kernel_path.exists())
        kernel_readable = _readable_file(self.kernel_path)
        initrd_exists = bool(self.initrd_path and self.initrd_path.exists())
        initrd_readable = _readable_file(self.initrd_path)
        gate = os.environ.get("ARC_VZ_PROOF") == "1"
        blockers: list[str] = []
        if system != "Darwin":
            blockers.append("Apple Virtualization.framework requires macOS")
        if not _macos_at_least(version, 13):
            blockers.append("macOS 13+ required")
        if not runner_executable:
            blockers.append("ARC_VZ_RUNNER missing/not executable")
        if pyobjc and not runner_executable:
            blockers.append("pyobjc runner path is not implemented; use executable ARC_VZ_RUNNER")
        if not kernel_readable:
            blockers.append("ARC_VZ_KERNEL missing/unreadable")
        if not initrd_readable:
            blockers.append("ARC_VZ_INITRD missing/unreadable")
        if not gate:
            blockers.append("ARC_VZ_PROOF=1 not set")
        ready = not blockers
        return {
            "provider": "vz_no_nic",
            "platform": "macos" if system == "Darwin" else system.lower(),
            "status": "ready" if ready else "blocked" if system == "Darwin" else "unavailable",
            "runtime": "apple-virtualization-framework",
            "public_execution_enabled": False,
            "network_devices_configured": 0,
            "networkDevices": [],
            "strict_network_candidate": True,
            "strict_no_network_proof": "not_proven",
            "proof_status": "ready_to_attempt" if ready else "not_ready",
            "preflight_ready": ready,
            "gate": gate,
            "macos_version": version,
            "pyobjc_available": pyobjc,
            "pyobjc_runner_implemented": False,
            "swiftc": shutil.which("swiftc"),
            "runner": str(self.runner_path) if self.runner_path else None,
            "runner_exists": runner_exists,
            "runner_executable": runner_executable,
            "kernel": str(self.kernel_path) if self.kernel_path else None,
            "kernel_exists": kernel_exists,
            "kernel_readable": kernel_readable,
            "initrd": str(self.initrd_path) if self.initrd_path else None,
            "initrd_exists": initrd_exists,
            "initrd_readable": initrd_readable,
            "blockers": blockers,
        }

    async def run_proof(self, workspace: Path, command: list[str]) -> VZProofResult:
        status = self.preflight()
        if status["status"] != "ready":
            return VZProofResult(
                available=False,
                command=command,
                network_devices_configured=0,
                no_nic_configured=True,
                blocker="; ".join(str(x) for x in status["blockers"]),
            )
        if not self.runner_path:
            return VZProofResult(
                available=False,
                command=command,
                network_devices_configured=0,
                no_nic_configured=True,
                blocker="pyobjc runner not implemented; set ARC_VZ_RUNNER",
            )
        assert self.kernel_path is not None
        assert self.initrd_path is not None
        resolved_workspace = workspace.resolve()
        sentinel = resolved_workspace / ".arc-vz-sentinel"
        escape = resolved_workspace / ".arc-vz-escape"
        escape_target: Path | None = None
        created_sentinel = False
        created_escape = False
        if not resolved_workspace.is_dir():
            return VZProofResult(
                available=False,
                command=command,
                network_devices_configured=0,
                no_nic_configured=True,
                blocker="workspace missing/not directory",
            )
        if sentinel.exists() or escape.exists():
            return VZProofResult(
                available=False,
                command=command,
                network_devices_configured=0,
                no_nic_configured=True,
                blocker="proof workspace marker path already exists; refusing to overwrite user files",
            )
        try:
            sentinel.write_text("arc-vz-proof\n", encoding="utf-8")
            created_sentinel = True
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix="arc-vz-host-secret-",
                delete=False,
            ) as handle:
                handle.write("arc-vz-host-secret\n")
                escape_target = Path(handle.name)
            if escape_target.resolve().is_relative_to(resolved_workspace):
                return VZProofResult(
                    available=False,
                    command=command,
                    network_devices_configured=0,
                    no_nic_configured=True,
                    blocker="proof escape target unexpectedly inside workspace",
                )
            escape.symlink_to(escape_target)
            created_escape = True
            proc = subprocess.run(
                [
                    str(self.runner_path),
                    "--kernel",
                    str(self.kernel_path),
                    "--initrd",
                    str(self.initrd_path),
                    "--workspace",
                    str(resolved_workspace),
                    "--",
                    *command,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=int(os.environ.get("ARC_VZ_TIMEOUT_SECONDS", "120")),
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _timeout_stream_to_text(exc.output)
            stderr = _timeout_stream_to_text(exc.stderr)
            proof = parse_vz_guest_proof(f"{stdout}\n{stderr}")
            guest_result = parse_vz_guest_command_result(f"{stdout}\n{stderr}")
            combined = f"{stdout}\n{stderr}".lower()
            teardown_attempted = "arc_vz_teardown_attempted=1" in combined
            teardown_ok = "arc_vz_teardown_ok=1" in combined
            return VZProofResult(
                available=True,
                booted=proof.booted,
                command=command,
                stdout=stdout,
                stderr=stderr,
                network_devices_configured=0,
                no_nic_configured=True,
                no_guest_ethernet=proof.no_guest_ethernet,
                no_default_route=proof.no_default_route,
                network_failure=proof.network_failure,
                network_tool_available=proof.network_tool_available,
                workspace_mount_proven=proof.workspace_mount_proven,
                sentinel_readable=proof.sentinel_readable,
                symlink_escape_blocked=proof.symlink_escape_blocked,
                command_result_seen=guest_result.marker_seen,
                guest_exit_code=guest_result.exit_code if guest_result.marker_seen else None,
                guest_stdout=guest_result.stdout,
                guest_stderr=guest_result.stderr,
                teardown_attempted=teardown_attempted,
                teardown_ok=teardown_ok,
                proof_markers=proof.raw,
                proof="failed",
                blocker=f"VZ proof runner timed out after {exc.timeout} seconds",
            )
        except OSError as exc:
            return VZProofResult(
                available=False,
                command=command,
                network_devices_configured=0,
                no_nic_configured=True,
                blocker=f"workspace proof marker setup failed: {exc}",
            )
        finally:
            if created_sentinel:
                sentinel.unlink(missing_ok=True)
            if created_escape:
                escape.unlink(missing_ok=True)
            if escape_target:
                escape_target.unlink(missing_ok=True)
        combined = f"{proc.stdout}\n{proc.stderr}".lower()
        proof = parse_vz_guest_proof(f"{proc.stdout}\n{proc.stderr}")
        guest_result = parse_vz_guest_command_result(f"{proc.stdout}\n{proc.stderr}")
        teardown_attempted = "arc_vz_teardown_attempted=1" in combined
        teardown_ok = "arc_vz_teardown_ok=1" in combined
        blockers = _vz_proof_blockers(
            proc.returncode,
            proof,
            guest_result,
            teardown_attempted=teardown_attempted,
            teardown_ok=teardown_ok,
        )
        return VZProofResult(
            available=True,
            booted=proof.booted,
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            network_devices_configured=0,
            no_nic_configured=True,
            no_guest_ethernet=proof.no_guest_ethernet,
            no_default_route=proof.no_default_route,
            network_failure=proof.network_failure,
            network_tool_available=proof.network_tool_available,
            workspace_mount_proven=proof.workspace_mount_proven,
            sentinel_readable=proof.sentinel_readable,
            symlink_escape_blocked=proof.symlink_escape_blocked,
            command_result_seen=guest_result.marker_seen,
            guest_exit_code=guest_result.exit_code if guest_result.marker_seen else None,
            guest_stdout=guest_result.stdout,
            guest_stderr=guest_result.stderr,
            teardown_attempted=teardown_attempted,
            teardown_ok=teardown_ok,
            proof_markers=proof.raw,
            proof="proven" if not blockers else "failed",
            blocker="; ".join(blockers) if blockers else None,
        )


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _codesign_verify(path: Path) -> bool:
    if platform.system() != "Darwin":
        return False
    codesign = shutil.which("codesign")
    if not codesign:
        return False
    try:
        result = subprocess.run(
            [codesign, "--verify", "--strict", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except Exception:
        return False
    return result.returncode == 0


def _vz_runner_env() -> dict[str, str]:
    allowed = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR"}
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _terminate_process_group(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass


def _vz_metadata(
    *,
    lifecycle: list[str],
    lifecycle_errors: list[str],
    gates: dict[str, object],
    manifest: VZArtifactManifest,
    proof: VZGuestProof,
    teardown_attempted: bool,
    teardown_ok: bool,
) -> dict[str, object]:
    return {
        "microvm_provider": "vz",
        "platform": "macos",
        "lifecycle": lifecycle,
        "lifecycle_errors": lifecycle_errors,
        "network_proof_passed": proof.network_proof_passed,
        "workspace_proof_passed": proof.workspace_proof_passed,
        "proof_markers": proof.raw,
        "teardown_attempted": teardown_attempted,
        "teardown_ok": teardown_ok,
        "gate": "ARC_MICROVM_EXEC_ENABLED=1,ARC_MICROVM_INTEGRATION=1,ARC_VZ_REAL_EXEC=1",
        "gates": gates.get("gates", {}),
        "artifact_manifest_path": gates.get("manifest_path"),
        "artifact_hashes": gates.get("artifact_hashes", {}),
        "runner_codesign_valid": gates.get("runner_codesign_valid", False),
        "network_devices_configured": 0,
        "networkDevices": [],
        "public_execution_enabled": True,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _command_sha256(command: list[str]) -> str:
    payload = json.dumps(command, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _copy_required_file(
    source: Path | None, destination: Path, label: str
) -> tuple[str | None, str | None, str | None]:
    if source is None:
        return None, None, f"{label} missing/not provided"
    resolved = source.expanduser().resolve()
    if not _readable_file(resolved):
        return None, None, f"{label} missing/unreadable"
    shutil.copy2(resolved, destination)
    return str(destination), _sha256_file(destination), None


def generate_vz_proof_artifacts(
    output_dir: Path,
    *,
    kernel_path: Path | None = None,
    initrd_path: Path | None = None,
    build_runner: bool = False,
    source_path: Path | None = None,
    entitlements_path: Path | None = None,
) -> VZArtifactReport:
    """Generate local VZ proof artifacts and provenance; never boots a VM."""
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_root = _repo_root()
    source_input = source_path or repo_root / "tools" / "arc-vz-runner.swift"
    entitlements_input = entitlements_path or repo_root / "tools" / "arc-vz-runner.entitlements"
    source_copy = output_dir / "arc-vz-runner.swift"
    entitlements_copy = output_dir / "arc-vz-runner.entitlements"
    runner_path = output_dir / "arc-vz-runner"
    manifest_path = output_dir / "vz-artifacts-manifest.json"
    blockers: list[str] = []

    source_artifact, source_sha, blocker = _copy_required_file(
        source_input, source_copy, "VZ runner source"
    )
    if blocker:
        blockers.append(blocker)
        source_artifact = str(source_copy)
        source_sha = ""
    entitlements_artifact, entitlements_sha, blocker = _copy_required_file(
        entitlements_input, entitlements_copy, "VZ runner entitlements"
    )
    if blocker:
        blockers.append(blocker)
        entitlements_artifact = str(entitlements_copy)
        entitlements_sha = ""

    kernel_source = kernel_path or _env_path("ARC_VZ_KERNEL")
    initrd_source = initrd_path or _env_path("ARC_VZ_INITRD")
    kernel_artifact, kernel_sha, blocker = _copy_required_file(
        kernel_source, output_dir / "arc-vz-kernel", "ARC_VZ_KERNEL"
    )
    if blocker:
        blockers.append(blocker)
    initrd_artifact, initrd_sha, blocker = _copy_required_file(
        initrd_source, output_dir / "arc-vz-initrd.gz", "ARC_VZ_INITRD"
    )
    if blocker:
        blockers.append(blocker)

    tools = {
        "swiftc": shutil.which("swiftc"),
        "codesign": shutil.which("codesign"),
    }
    build_commands: list[list[str]] = []
    runner_built = False
    runner_signed = False
    runner_sha: str | None = None
    if not build_runner:
        blockers.append("--build-runner not set; copied source/entitlements only")
    elif platform.system() != "Darwin":
        blockers.append("VZ runner build requires macOS")
    elif not source_sha or not entitlements_sha:
        blockers.append("VZ runner build requires source and entitlements artifacts")
    elif not tools["swiftc"]:
        blockers.append("missing tool: swiftc")
    elif not tools["codesign"]:
        blockers.append("missing tool: codesign")
    else:
        swiftc_cmd = [str(tools["swiftc"]), str(source_copy), "-o", str(runner_path)]
        build_commands.append(swiftc_cmd)
        compile_proc = subprocess.run(
            swiftc_cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if compile_proc.returncode != 0:
            blockers.append(
                f"swiftc failed: {compile_proc.stderr.strip() or compile_proc.stdout.strip()}"
            )
        else:
            runner_built = True
            sign_cmd = [
                str(tools["codesign"]),
                "--force",
                "--sign",
                "-",
                "--entitlements",
                str(entitlements_copy),
                str(runner_path),
            ]
            build_commands.append(sign_cmd)
            sign_proc = subprocess.run(
                sign_cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if sign_proc.returncode != 0:
                blockers.append(
                    f"codesign failed: {sign_proc.stderr.strip() or sign_proc.stdout.strip()}"
                )
            else:
                runner_signed = True
            if runner_path.exists():
                runner_sha = _sha256_file(runner_path)

    if runner_built and runner_signed and kernel_artifact and initrd_artifact and not blockers:
        build_status = "runner_inputs_pinned"
    elif runner_built:
        build_status = "runner_built_with_blockers"
    else:
        build_status = "source_manifest_only"
    manifest = VZArtifactManifest(
        generated_at=_utc_now(),
        host_os=platform.system(),
        host_arch=platform.machine(),
        source_path=str(source_artifact),
        source_sha256=source_sha or "",
        entitlements_path=str(entitlements_artifact),
        entitlements_sha256=entitlements_sha or "",
        runner_path=str(runner_path) if runner_built else None,
        runner_sha256=runner_sha,
        runner_built=runner_built,
        runner_signed=runner_signed,
        kernel_path=kernel_artifact,
        kernel_sha256=kernel_sha,
        kernel_source_path=str(kernel_source.expanduser().resolve()) if kernel_source else None,
        initrd_path=initrd_artifact,
        initrd_sha256=initrd_sha,
        initrd_source_path=str(initrd_source.expanduser().resolve()) if initrd_source else None,
        tools=tools,
        build_status=build_status,
        build_commands=build_commands,
        blockers=blockers,
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return VZArtifactReport(
        manifest_path=str(manifest_path),
        source_path=str(source_artifact),
        entitlements_path=str(entitlements_artifact),
        runner_path=str(runner_path) if runner_built else None,
        kernel_path=kernel_artifact,
        initrd_path=initrd_artifact,
        runner_built=runner_built,
        runner_signed=runner_signed,
        blockers=blockers,
        manifest=manifest,
    )


def render_vz_exec_init() -> str:
    """Return the reviewable ARC VZ init contract for guest-available argv execution."""
    return """#!/bin/sh
set +e
BB=/usr/bin/busybox
PATH=/usr/bin:/bin:/sbin:/usr/sbin
echo ARC_VZ_PROOF booted=1
$BB mount -t proc proc /proc 2>/dev/null || true
$BB mount -t sysfs sysfs /sys 2>/dev/null || true
$BB mkdir -p /workspace /tmp
if $BB grep -Eq "(^|[[:space:]])(eth|ens|enp|wlan)[0-9a-z]*:" /proc/net/dev 2>/dev/null; then echo ARC_VZ_PROOF no-guest-ethernet=0; else echo ARC_VZ_PROOF no-guest-ethernet=1; fi
if $BB grep -q "00000000" /proc/net/route 2>/dev/null; then echo ARC_VZ_PROOF no-default-route=0; else echo ARC_VZ_PROOF no-default-route=1; fi
if [ -x /usr/bin/wget ]; then echo ARC_VZ_PROOF wget-available=1; else echo ARC_VZ_PROOF wget-available=0; fi
if /usr/bin/wget -T 2 -O /tmp/arc-vz-net http://192.0.2.1/ 2>/tmp/arc-vz-wget.err; then echo ARC_VZ_PROOF network-failure=0; else echo ARC_VZ_PROOF network-failure=1; fi
if $BB mount -t virtiofs workspace /workspace 2>/tmp/arc-vz-mount.err; then echo ARC_VZ_PROOF workspace-mount=1; else echo ARC_VZ_PROOF workspace-mount=0; fi
if [ -r /workspace/.arc-vz-sentinel ]; then echo ARC_VZ_PROOF sentinel-read=1; else echo ARC_VZ_PROOF sentinel-read=0; fi
if [ -r /workspace/.arc-vz-escape ]; then echo ARC_VZ_PROOF symlink-escape-blocked=0; else echo ARC_VZ_PROOF symlink-escape-blocked=1; fi
cd /workspace 2>/tmp/arc-vz-cd.err || true
ARGV_B64CSV=""
COMMAND_SHA256=""
for arg in $(cat /proc/cmdline); do
  case "$arg" in
    ARC_VZ_COMMAND_ARGV_B64CSV=*) ARGV_B64CSV=${arg#ARC_VZ_COMMAND_ARGV_B64CSV=} ;;
    ARC_VZ_COMMAND_SHA256=*) COMMAND_SHA256=${arg#ARC_VZ_COMMAND_SHA256=} ;;
  esac
done
set --
REST="$ARGV_B64CSV"
while [ -n "$REST" ]; do
  case "$REST" in
    *,*) PART=${REST%%,*}; REST=${REST#*,} ;;
    *) PART=$REST; REST="" ;;
  esac
  DECODED=$(printf '%s' "$PART" | /usr/bin/base64 -d 2>/tmp/arc-vz-decode.err || true)
  set -- "$@" "$DECODED"
done
if [ "$#" -eq 0 ] || [ -z "$1" ]; then
  echo ARC_VZ_RESULT exit_code=127
  echo ARC_VZ_RESULT stdout=
  echo ARC_VZ_RESULT stderr=missing-command
  echo ARC_VZ_RESULT command_sha256="$COMMAND_SHA256"
else
  "$@" >/tmp/arc-vz-cmd.out 2>/tmp/arc-vz-cmd.err
  RC=$?
  OUT=$(tr '\n' ' ' </tmp/arc-vz-cmd.out | head -c 8192)
  ERR=$(tr '\n' ' ' </tmp/arc-vz-cmd.err | head -c 8192)
  echo ARC_VZ_RESULT exit_code=$RC
  echo ARC_VZ_RESULT stdout=$OUT
  echo ARC_VZ_RESULT stderr=$ERR
  echo ARC_VZ_RESULT command_sha256="$COMMAND_SHA256"
fi
$BB sync || true
$BB reboot -f || $BB poweroff -f || $BB halt -f || true
"""


def generate_vz_exec_init_artifacts(output_dir: Path) -> VZExecInitReport:
    """Write the ARC VZ exec init contract; does not build an initrd or download assets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    init_path = output_dir / "arc-vz-exec-init.sh"
    manifest_path = output_dir / "vz-exec-init-manifest.json"
    init_path.write_text(render_vz_exec_init(), encoding="utf-8")
    init_path.chmod(0o755)
    manifest = VZExecInitManifest(
        generated_at=_utc_now(),
        host_os=platform.system(),
        host_arch=platform.machine(),
        init_path=str(init_path),
        init_sha256=_sha256_file(init_path),
        guest_requirements=[
            "Linux initramfs with /init wired to this script",
            "/usr/bin/busybox",
            "/usr/bin/base64",
            "/usr/bin/wget for network-failure proof",
            "virtiofs workspace tag mounted as /workspace",
            "requested argv binary/runtime present inside the guest",
        ],
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return VZExecInitReport(
        manifest_path=str(manifest_path),
        init_path=str(init_path),
        blockers=[],
        manifest=manifest,
    )


def validate_vz_exec_init_manifest(path: Path) -> VZExecInitManifest:
    """Validate the ARC VZ exec-init contract without building or booting a VM."""
    manifest = VZExecInitManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if manifest.marker_contract_version != 1:
        raise ValueError("unsupported VZ exec init marker contract version")
    if manifest.no_downloads is not True:
        raise ValueError("VZ exec init artifacts must not use downloads")
    if manifest.shell_string_execution:
        raise ValueError("VZ exec init must not use shell-string command execution")
    if manifest.python_runtime_included:
        raise ValueError("VZ exec init manifest must not claim bundled Python runtime")
    if set(manifest.markers) != set(VZ_MARKERS):
        raise ValueError("VZ exec init marker list mismatch")
    init_path = Path(manifest.init_path)
    if not init_path.exists() or _sha256_file(init_path) != manifest.init_sha256:
        raise ValueError("VZ exec init sha256 mismatch")
    init_text = init_path.read_text(encoding="utf-8")
    required = [
        "ARC_VZ_COMMAND_ARGV_B64CSV",
        "ARC_VZ_COMMAND_SHA256",
        "ARC_VZ_RESULT command_sha256",
        '"$@" >/tmp/arc-vz-cmd.out',
        "ARC_VZ_PROOF network-failure",
        "ARC_VZ_PROOF symlink-escape-blocked",
    ]
    for token in required:
        if token not in init_text:
            raise ValueError(f"VZ exec init missing contract token: {token}")
    forbidden = ["eval ", "sh -c", "ash -c", "bash -c"]
    for token in forbidden:
        if token in init_text:
            raise ValueError(f"VZ exec init contains forbidden shell execution token: {token}")
    return manifest


def validate_vz_artifact_manifest(path: Path) -> VZArtifactManifest:
    """Validate VZ artifact provenance without booting a VM."""
    manifest = VZArtifactManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if manifest.marker_contract_version != 1:
        raise ValueError("unsupported VZ marker contract version")
    if set(manifest.markers) != set(VZ_MARKERS):
        raise ValueError("VZ manifest marker list mismatch")
    if manifest.public_execution_enabled:
        raise ValueError("VZ artifacts must not enable public execution")
    if not manifest.proof_only:
        raise ValueError("VZ artifacts must remain proof-only")
    if not manifest.no_downloads:
        raise ValueError("VZ artifacts must not use downloads")
    if manifest.network_devices_configured != 0 or manifest.networkDevices:
        raise ValueError("VZ artifacts must configure zero network devices")
    source = Path(manifest.source_path)
    if not source.exists() or _sha256_file(source) != manifest.source_sha256:
        raise ValueError("VZ runner source sha256 mismatch")
    source_text = source.read_text(encoding="utf-8")
    if "config.networkDevices = []" not in source_text:
        raise ValueError("VZ runner source missing no-NIC configuration")
    if "VZVirtioNetworkDeviceConfiguration" in source_text:
        raise ValueError("VZ runner source configures network device type")
    if (
        "ARC_VZ_TEARDOWN_ATTEMPTED=1" not in source_text
        or "ARC_VZ_TEARDOWN_OK=1" not in source_text
    ):
        raise ValueError("VZ runner source missing teardown markers")
    if "--command-sha256" not in source_text or "ARC_VZ_COMMAND_SHA256" not in source_text:
        raise ValueError("VZ runner source missing command hash contract")
    if "ARC_VZ_COMMAND_ARGV_B64CSV" not in source_text:
        raise ValueError("VZ runner source missing argv transport contract")
    entitlements = Path(manifest.entitlements_path)
    if not entitlements.exists() or _sha256_file(entitlements) != manifest.entitlements_sha256:
        raise ValueError("VZ entitlements sha256 mismatch")
    if "com.apple.security.virtualization" not in entitlements.read_text(encoding="utf-8"):
        raise ValueError("VZ entitlements missing virtualization entitlement")
    if manifest.runner_path:
        runner = Path(manifest.runner_path)
        if not runner.exists() or _sha256_file(runner) != manifest.runner_sha256:
            raise ValueError("VZ runner sha256 mismatch")
    if manifest.kernel_path:
        kernel = Path(manifest.kernel_path)
        if not kernel.exists() or _sha256_file(kernel) != manifest.kernel_sha256:
            raise ValueError("VZ kernel sha256 mismatch")
    if manifest.initrd_path:
        initrd = Path(manifest.initrd_path)
        if not initrd.exists() or _sha256_file(initrd) != manifest.initrd_sha256:
            raise ValueError("VZ initrd sha256 mismatch")
    return manifest


def _timeout_stream_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def parse_vz_guest_proof(output: str) -> VZGuestProof:
    """Parse guest proof markers emitted by the ARC VZ initrd."""
    raw: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith(VZ_PROOF_MARKER):
            continue
        payload = line.removeprefix(VZ_PROOF_MARKER).strip()
        if "=" not in payload:
            continue
        key, value = payload.split("=", 1)
        normalized_key = _VZ_PROOF_ALIASES.get(key.strip(), key.strip().replace("-", "_"))
        raw[normalized_key] = value.strip()
    return VZGuestProof(
        marker_seen=bool(raw),
        booted=raw.get("booted") == "1",
        no_guest_ethernet=raw.get("no_guest_ethernet") == "1",
        no_default_route=raw.get("no_default_route") == "1",
        network_tool_available=raw.get("network_tool_available") == "1",
        network_failure=raw.get("network_failure") == "1",
        workspace_mount_proven=raw.get("workspace_mount_proven") == "1",
        sentinel_readable=raw.get("sentinel_readable") == "1",
        symlink_escape_blocked=raw.get("symlink_escape_blocked") == "1",
        raw=raw,
    )


def parse_vz_guest_command_result(output: str) -> VZGuestCommandResult:
    """Parse command-result markers emitted by the ARC VZ initrd."""
    raw: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith(VZ_RESULT_MARKER):
            continue
        payload = line.removeprefix(VZ_RESULT_MARKER).strip()
        if "=" not in payload:
            continue
        key, value = payload.split("=", 1)
        raw[key.strip()] = value.strip()
    try:
        exit_code = int(raw.get("exit_code", "-1"))
    except ValueError:
        exit_code = -1
    return VZGuestCommandResult(
        marker_seen=bool(raw),
        exit_code=exit_code,
        stdout=raw.get("stdout", ""),
        stderr=raw.get("stderr", ""),
        command_sha256=raw.get("command_sha256") or raw.get("command-sha256"),
        raw=raw,
    )


def _vz_proof_blockers(
    runner_exit_code: int,
    proof: VZGuestProof,
    guest_result: VZGuestCommandResult,
    *,
    teardown_attempted: bool,
    teardown_ok: bool,
    expected_command_sha256: str | None = None,
) -> list[str]:
    blockers: list[str] = []
    if runner_exit_code != 0:
        blockers.append(f"runner exit code {runner_exit_code}")
    if not proof.marker_seen:
        blockers.append("guest proof markers missing")
    if not proof.network_proof_passed:
        blockers.append(
            "network proof failed: booted, no guest ethernet, no default route, "
            "network tool, and failed network probe markers required"
        )
    if not proof.workspace_proof_passed:
        blockers.append(
            "workspace proof failed: workspace mount, sentinel read, and symlink escape markers required"
        )
    if not guest_result.marker_seen:
        blockers.append("guest command result markers missing")
    if expected_command_sha256 and guest_result.command_sha256 != expected_command_sha256:
        blockers.append("guest command result did not prove requested argv hash")
    if not teardown_attempted:
        blockers.append("teardown marker missing")
    elif not teardown_ok:
        blockers.append("teardown did not report ok")
    return blockers


def _pyobjc_available() -> bool:
    try:
        __import__("Virtualization")
    except Exception:
        return False
    return True


def _readable_file(path: Path | None) -> bool:
    return bool(path and path.is_file() and os.access(path, os.R_OK))


def _executable_file(path: Path | None) -> bool:
    return bool(path and path.is_file() and os.access(path, os.X_OK))


def _macos_at_least(version: str, major: int) -> bool:
    try:
        return int((version or "0").split(".")[0]) >= major
    except ValueError:
        return False
