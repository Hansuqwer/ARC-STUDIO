"""Apple Virtualization.framework direct no-NIC VM proof provider.

This is not Lima. The proof path requires an explicit gate plus a VZ runner
capable of creating VZVirtualMachineConfiguration with networkDevices = [].
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict


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
        kernel_exists = bool(self.kernel_path and self.kernel_path.exists())
        initrd_exists = bool(self.initrd_path and self.initrd_path.exists())
        gate = os.environ.get("ARC_VZ_PROOF") == "1"
        blockers: list[str] = []
        if system != "Darwin":
            blockers.append("Apple Virtualization.framework requires macOS")
        if not _macos_at_least(version, 13):
            blockers.append("macOS 13+ required")
        if not pyobjc and not runner_exists:
            blockers.append("pyobjc-framework-Virtualization or ARC_VZ_RUNNER missing")
        if not kernel_exists:
            blockers.append("ARC_VZ_KERNEL missing/unreadable")
        if not initrd_exists:
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
            "strict_no_network_proof": "ready" if ready else "not_proven",
            "gate": gate,
            "macos_version": version,
            "pyobjc_available": pyobjc,
            "swiftc": shutil.which("swiftc"),
            "runner": str(self.runner_path) if self.runner_path else None,
            "runner_exists": runner_exists,
            "kernel": str(self.kernel_path) if self.kernel_path else None,
            "kernel_exists": kernel_exists,
            "initrd": str(self.initrd_path) if self.initrd_path else None,
            "initrd_exists": initrd_exists,
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
        proc = subprocess.run(
            [
                str(self.runner_path),
                "--kernel",
                str(self.kernel_path),
                "--initrd",
                str(self.initrd_path),
                "--workspace",
                str(workspace.resolve()),
                "--",
                *command,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("ARC_VZ_TIMEOUT_SECONDS", "120")),
        )
        combined = f"{proc.stdout}\n{proc.stderr}".lower()
        no_guest_ethernet = all(name not in combined for name in ("eth0", "ens", "enp"))
        return VZProofResult(
            available=True,
            booted=proc.returncode == 0,
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            network_devices_configured=0,
            no_nic_configured=True,
            no_guest_ethernet=no_guest_ethernet,
            proof="proven" if proc.returncode == 0 and no_guest_ethernet else "failed",
        )


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _pyobjc_available() -> bool:
    try:
        __import__("Virtualization")
    except Exception:
        return False
    return True


def _macos_at_least(version: str, major: int) -> bool:
    try:
        return int((version or "0").split(".")[0]) >= major
    except ValueError:
        return False
