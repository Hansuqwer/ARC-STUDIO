"""Apple Virtualization.framework direct no-NIC VM proof provider.

This is not Lima. The proof path requires an explicit gate plus a VZ runner
capable of creating VZVirtualMachineConfiguration with networkDevices = [].
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


VZ_PROOF_MARKER = "ARC_VZ_PROOF "
VZ_RESULT_MARKER = "ARC_VZ_RESULT "

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
        raw=raw,
    )


def _vz_proof_blockers(
    runner_exit_code: int,
    proof: VZGuestProof,
    guest_result: VZGuestCommandResult,
    *,
    teardown_attempted: bool,
    teardown_ok: bool,
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
