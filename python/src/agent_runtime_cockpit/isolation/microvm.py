"""MicroVM provider preflight/doctor support.

Lima/Firecracker execution remains unproven and is intentionally unreachable from
the public provider until lifecycle, mount, network-off, teardown, and opt-in
integration proof are complete.
"""

from __future__ import annotations

import os
import platform
import json
import hashlib
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
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
from .subprocess import _BoundedPipeReader, redact_output


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


class CloudHypervisorNoNetworkConfig(BaseModel):
    """Design-proof Cloud Hypervisor argv with no guest NICs configured."""

    model_config = ConfigDict(frozen=True)

    api_socket: str
    kernel_path: str
    disk_path: str
    cmdline: str = "console=hvc0 root=/dev/vda1 rw"
    cpus: str = "boot=1"
    memory: str = "size=512M"
    strict_network_candidate: bool = True
    strict_network_proof: str = "not_proven"
    network_interfaces_configured: bool = False
    workspace_mount_strategy: str = "virtiofs_or_agent_pending"

    def to_cloud_hypervisor_argv(self) -> list[str]:
        """Return Cloud Hypervisor argv without --net options."""
        return [
            "cloud-hypervisor",
            "--api-socket",
            self.api_socket,
            "--cpus",
            self.cpus,
            "--memory",
            self.memory,
            "--kernel",
            self.kernel_path,
            "--cmdline",
            self.cmdline,
            "--disk",
            f"path={self.disk_path}",
        ]


class CloudHypervisorNoNetworkRunPlan(BaseModel):
    """Non-executing strict no-network proof plan for Cloud Hypervisor."""

    model_config = ConfigDict(frozen=True)

    command: list[str]
    proof_commands: list[list[str]]
    config: CloudHypervisorNoNetworkConfig
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
    public_execution_enabled: bool = False
    proof_blocker: str | None = None


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


class FirecrackerProofRunResult(BaseModel):
    """Private host-gated Firecracker proof runner result."""

    model_config = ConfigDict(frozen=True)

    command: list[str]
    instance_name: str
    temp_dir: str
    api_socket: str
    config_path: str
    result: IsolationResult
    lifecycle: list[str]
    no_default_route: bool = False
    network_failure: bool = False
    workspace_sentinel_readable: bool = False
    symlink_escape_blocked: bool = False
    teardown_attempted: bool = False
    network_interfaces_configured: bool = False
    public_execution_enabled: bool = False
    proof_blocker: str | None = None

    @property
    def network_proof_passed(self) -> bool:
        return self.no_default_route and self.network_failure


class FirecrackerGuestProof(BaseModel):
    """Proof-only guest marker results parsed from serial/stdout output."""

    model_config = ConfigDict(frozen=True)

    marker_seen: bool = False
    no_default_route: bool = False
    network_failure: bool = False
    sentinel_readable: bool = False
    symlink_escape_blocked: bool = False
    curl_available: bool = False
    workspace_mount_proven: bool = False
    raw: dict[str, str] = {}

    @property
    def network_proof_passed(self) -> bool:
        return self.no_default_route and self.network_failure and self.curl_available

    @property
    def workspace_proof_passed(self) -> bool:
        return (
            self.workspace_mount_proven and self.sentinel_readable and self.symlink_escape_blocked
        )


class FirecrackerProofArtifactManifest(BaseModel):
    """Manifest for ARC-owned Firecracker proof rootfs/init artifacts."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    generator_version: str = "arc-firecracker-proof-v1"
    marker_contract_version: int = 1
    artifact: str = "arc-firecracker-proof-rootfs"
    generated_at: str = ""
    host_os: str = ""
    host_arch: str = ""
    init_path: str
    init_sha256: str
    rootfs_path: str | None = None
    rootfs_sha256: str | None = None
    markers: list[str]
    init_entrypoints: list[str] = []
    device_nodes: list[str] = []
    proof_commands: list[list[str]] = []
    network_interfaces_configured: bool = False
    rootfs_size_mib: int = 32
    tools: dict[str, str | None] = {}
    build_status: str
    blockers: list[str] = []


class FirecrackerProofArtifactReport(BaseModel):
    """Result of proof init/manifest generation and optional rootfs build."""

    model_config = ConfigDict(frozen=True)

    manifest_path: str
    init_path: str
    rootfs_path: str | None = None
    built_rootfs: bool = False
    blockers: list[str] = []
    manifest: FirecrackerProofArtifactManifest


FIRECRACKER_PROOF_MARKER = "ARC_FC_PROOF "
FIRECRACKER_PROOF_MARKERS = [
    "no_default_route",
    "network_failure",
    "curl_available",
    "sentinel_readable",
    "symlink_escape_blocked",
    "workspace_mount_proven",
]

FIRECRACKER_PROOF_MARKER_KEYS = {
    "no_default_route": "no-default-route",
    "network_failure": "network-failure",
    "curl_available": "curl-available",
    "sentinel_readable": "sentinel-read",
    "symlink_escape_blocked": "symlink-escape-blocked",
    "workspace_mount_proven": "workspace-mount-proven",
}

_FIRECRACKER_PROOF_ALIASES = {
    "no-default-route": "no_default_route",
    "network-failure": "network_failure",
    "curl-available": "curl_available",
    "sentinel-read": "sentinel_readable",
    "symlink-escape-blocked": "symlink_escape_blocked",
    "workspace-mount-proven": "workspace_mount_proven",
    "curl_failed": "network_failure",
}


def parse_firecracker_guest_proof(output: str) -> FirecrackerGuestProof:
    """Parse proof-only guest markers emitted by ARC rootfs/init agents."""
    raw: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith(FIRECRACKER_PROOF_MARKER):
            continue
        payload = line.removeprefix(FIRECRACKER_PROOF_MARKER).strip()
        if "=" not in payload:
            continue
        key, value = payload.split("=", 1)
        normalized_key = _FIRECRACKER_PROOF_ALIASES.get(key.strip(), key.strip())
        raw[normalized_key] = value.strip()
    return FirecrackerGuestProof(
        marker_seen=bool(raw),
        no_default_route=raw.get("no_default_route") == "1",
        network_failure=raw.get("network_failure") == "1",
        curl_available=raw.get("curl_available") == "1",
        sentinel_readable=raw.get("sentinel_readable") == "1",
        symlink_escape_blocked=raw.get("symlink_escape_blocked") == "1",
        workspace_mount_proven=raw.get("workspace_mount_proven") == "1",
        raw=raw,
    )


def render_firecracker_guest_proof_init() -> str:
    """Return proof-only init snippet expected inside a dedicated ARC rootfs."""
    return """#!/bin/sh
set +e
mount -t proc proc /proc 2>/dev/null || true
mount -t sysfs sysfs /sys 2>/dev/null || true
if ip route 2>/dev/null | grep -q '^default'; then
  echo 'ARC_FC_PROOF no-default-route=0'
else
  echo 'ARC_FC_PROOF no-default-route=1'
fi
CURL_BIN="$(command -v curl 2>/dev/null || true)"
if [ "$CURL_BIN" = "" ] && [ -x /bin/curl ]; then
  CURL_BIN=/bin/curl
fi
if [ "$CURL_BIN" = "" ] && [ -x /usr/bin/curl ]; then
  CURL_BIN=/usr/bin/curl
fi
if [ "$CURL_BIN" != "" ]; then
  echo 'ARC_FC_PROOF curl-available=1'
else
  echo 'ARC_FC_PROOF curl-available=0'
fi
if [ "$CURL_BIN" != "" ] && "$CURL_BIN" --connect-timeout 2 https://example.com >/tmp/arc-curl.out 2>/tmp/arc-curl.err; then
  echo 'ARC_FC_PROOF network-failure=0'
elif [ "$CURL_BIN" != "" ]; then
  echo 'ARC_FC_PROOF network-failure=1'
else
  echo 'ARC_FC_PROOF network-failure=0'
fi
if cat /workspace/arc-sentinel.txt >/dev/null 2>&1; then
  echo 'ARC_FC_PROOF sentinel-read=1'
  echo 'ARC_FC_PROOF workspace-mount-proven=1'
else
  echo 'ARC_FC_PROOF sentinel-read=0'
  echo 'ARC_FC_PROOF workspace-mount-proven=0'
fi
if cat /workspace/arc-host-escape-link >/tmp/arc-escape.out 2>/tmp/arc-escape.err; then
  echo 'ARC_FC_PROOF symlink-escape-blocked=0'
else
  echo 'ARC_FC_PROOF symlink-escape-blocked=1'
fi
reboot -f 2>/dev/null || poweroff -f 2>/dev/null || halt -f
"""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(path: Path, manifest: FirecrackerProofArtifactManifest) -> None:
    path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _firecracker_init_safety_blockers(init_text: str) -> list[str]:
    blockers: list[str] = []
    forbidden = {
        "apk add": "package install command present",
        "apt-get": "package install command present",
        "apt ": "package install command present",
        "dnf ": "package install command present",
        "yum ": "package install command present",
        "pip install": "package install command present",
        "ARC_USER_ARGV": "user argv execution hook present",
        'exec "$@"': "user argv execution hook present",
        "ifconfig ": "network enablement command present",
        "ip link set": "network enablement command present",
        "udhcpc": "network enablement command present",
        "dhclient": "network enablement command present",
    }
    for needle, reason in forbidden.items():
        if needle in init_text:
            blockers.append(reason)
    return sorted(set(blockers))


def generate_firecracker_proof_artifacts(
    output_dir: Path,
    *,
    rootfs_path: Path | None = None,
    build_rootfs: bool | None = None,
    rootfs_size_mib: int = 32,
) -> FirecrackerProofArtifactReport:
    """Generate deterministic Firecracker proof init + manifest.

    Optional ext4 image creation is host-gated by ``ARC_FC_BUILD_PROOF_ROOTFS=1``
    and local tools. This never downloads images or runs privileged commands.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    init_path = output_dir / "arc-fc-proof-init.sh"
    manifest_path = output_dir / "rootfs-manifest.json"
    init_path.write_text(render_firecracker_guest_proof_init(), encoding="utf-8")
    init_path.chmod(0o755)

    blockers: list[str] = []
    init_text = init_path.read_text(encoding="utf-8")
    blockers.extend(_firecracker_init_safety_blockers(init_text))
    requested_build = (
        os.environ.get("ARC_FC_BUILD_PROOF_ROOTFS") == "1" if build_rootfs is None else build_rootfs
    )
    built_rootfs = False
    final_rootfs_path = rootfs_path or (output_dir / "arc-fc-proof-rootfs.ext4")
    rootfs_sha256: str | None = None

    if requested_build:
        tools = {
            "busybox": shutil.which("busybox"),
            "mkfs.ext4": shutil.which("mkfs.ext4"),
            "truncate": shutil.which("truncate"),
        }
        missing = [name for name, value in tools.items() if not value]
        if missing:
            blockers.extend(f"missing tool: {name}" for name in missing)
        else:
            root_dir = output_dir / "rootfs-tree"
            (root_dir / "bin").mkdir(parents=True, exist_ok=True)
            (root_dir / "sbin").mkdir(parents=True, exist_ok=True)
            (root_dir / "proc").mkdir(exist_ok=True)
            (root_dir / "sys").mkdir(exist_ok=True)
            (root_dir / "dev").mkdir(exist_ok=True)
            (root_dir / "tmp").mkdir(exist_ok=True)
            (root_dir / "workspace").mkdir(exist_ok=True)
            shutil.copy2(str(tools["busybox"]), root_dir / "bin" / "busybox")
            init_text = init_path.read_text(encoding="utf-8")
            (root_dir / "init").write_text(init_text, encoding="utf-8")
            (root_dir / "init").chmod(0o755)
            (root_dir / "sbin" / "init").write_text(init_text, encoding="utf-8")
            (root_dir / "sbin" / "init").chmod(0o755)
            (root_dir / "dev" / "console").touch(mode=0o600, exist_ok=True)
            (root_dir / "dev" / "null").touch(mode=0o666, exist_ok=True)
            required_applets = ("sh", "cat", "grep", "ip", "mount", "reboot", "poweroff", "halt")
            for applet in required_applets:
                link = root_dir / "bin" / applet
                if not link.exists():
                    link.symlink_to("busybox")
            subprocess.run(
                [str(tools["truncate"]), "-s", f"{rootfs_size_mib}M", str(final_rootfs_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [str(tools["mkfs.ext4"]), "-d", str(root_dir), "-F", str(final_rootfs_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            built_rootfs = True
            rootfs_sha256 = _sha256_file(final_rootfs_path)
    else:
        blockers.append("ARC_FC_BUILD_PROOF_ROOTFS=1 not set; generated init/manifest only")

    manifest = FirecrackerProofArtifactManifest(
        generated_at=_utc_now(),
        host_os=platform.system(),
        host_arch=platform.machine(),
        init_path=str(init_path),
        init_sha256=_sha256_file(init_path),
        rootfs_path=str(final_rootfs_path) if built_rootfs else None,
        rootfs_sha256=rootfs_sha256,
        markers=FIRECRACKER_PROOF_MARKERS,
        init_entrypoints=["/init", "/sbin/init"] if built_rootfs else ["arc-fc-proof-init.sh"],
        device_nodes=["/dev/console", "/dev/null"] if built_rootfs else [],
        proof_commands=[
            ["ip", "route"],
            ["curl", "--connect-timeout", "2", "https://example.com"],
            ["cat", "/workspace/arc-sentinel.txt"],
            ["cat", "/workspace/arc-host-escape-link"],
        ],
        network_interfaces_configured=False,
        rootfs_size_mib=rootfs_size_mib,
        tools={
            "busybox": shutil.which("busybox"),
            "mkfs.ext4": shutil.which("mkfs.ext4"),
            "truncate": shutil.which("truncate"),
            "curl": shutil.which("curl"),
        },
        build_status="built" if built_rootfs else "init_manifest_only",
        blockers=blockers,
    )
    _write_manifest(manifest_path, manifest)
    return FirecrackerProofArtifactReport(
        manifest_path=str(manifest_path),
        init_path=str(init_path),
        rootfs_path=str(final_rootfs_path) if built_rootfs else None,
        built_rootfs=built_rootfs,
        blockers=blockers,
        manifest=manifest,
    )


def validate_firecracker_proof_manifest(path: Path) -> FirecrackerProofArtifactManifest:
    """Validate proof manifest and marker init without mounting rootfs."""
    manifest = FirecrackerProofArtifactManifest.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    init_path = Path(manifest.init_path)
    if not init_path.exists():
        raise ValueError("proof init missing")
    if _sha256_file(init_path) != manifest.init_sha256:
        raise ValueError("proof init sha256 mismatch")
    init_text = init_path.read_text(encoding="utf-8")
    safety_blockers = _firecracker_init_safety_blockers(init_text)
    if safety_blockers:
        raise ValueError(f"proof init safety blockers: {', '.join(safety_blockers)}")
    if manifest.marker_contract_version != 1:
        raise ValueError("unsupported proof marker contract version")
    if set(manifest.markers) != set(FIRECRACKER_PROOF_MARKERS):
        raise ValueError("proof manifest marker list mismatch")
    if manifest.network_interfaces_configured:
        raise ValueError("proof manifest must not configure network interfaces")
    if not manifest.proof_commands:
        raise ValueError("proof manifest missing proof commands")
    for marker in FIRECRACKER_PROOF_MARKERS:
        hyphenated = FIRECRACKER_PROOF_MARKER_KEYS.get(marker, marker.replace("_", "-"))
        if (
            f"ARC_FC_PROOF {marker}=" not in init_text
            and f"ARC_FC_PROOF {hyphenated}=" not in init_text
        ):
            raise ValueError(f"proof init missing marker: {marker}")
    if "mount -t proc proc /proc" not in init_text:
        raise ValueError("proof init missing proc mount")
    if "mount -t sysfs sysfs /sys" not in init_text:
        raise ValueError("proof init missing sysfs mount")
    if manifest.build_status == "built":
        required_entrypoints = {"/init", "/sbin/init"}
        if not required_entrypoints.issubset(set(manifest.init_entrypoints)):
            raise ValueError("proof manifest missing init entrypoints")
        required_devices = {"/dev/console", "/dev/null"}
        if not required_devices.issubset(set(manifest.device_nodes)):
            raise ValueError("proof manifest missing device nodes")
    if manifest.rootfs_path:
        rootfs = Path(manifest.rootfs_path)
        if not rootfs.exists():
            raise ValueError("proof rootfs missing")
        if manifest.rootfs_sha256 and _sha256_file(rootfs) != manifest.rootfs_sha256:
            raise ValueError("proof rootfs sha256 mismatch")
    return manifest


def _firecracker_binary() -> str | None:
    binary = shutil.which("firecracker")
    return str(binary) if binary else None


def firecracker_proof_gates() -> dict[str, object]:
    """Return private Firecracker proof-runner gates; never starts a VM."""
    kernel = os.environ.get("ARC_FIRECRACKER_KERNEL")
    rootfs = os.environ.get("ARC_FIRECRACKER_ROOTFS")
    manifest_env = os.environ.get("ARC_FIRECRACKER_PROOF_ROOTFS_MANIFEST")
    kernel_path = Path(kernel) if kernel else None
    rootfs_path = Path(rootfs) if rootfs else None
    manifest_path = Path(manifest_env) if manifest_env else None
    kvm_path = Path("/dev/kvm")
    binary = _firecracker_binary()
    gates = {
        "linux": platform.system() == "Linux",
        "kvm_exists": kvm_path.exists(),
        "kvm_rw": kvm_path.exists() and os.access(kvm_path, os.R_OK | os.W_OK),
        "firecracker_binary": binary,
        "integration_gate": os.environ.get("ARC_MICROVM_INTEGRATION") == "1",
        "real_exec_gate": os.environ.get("ARC_FC_REAL_EXEC") == "1",
        "kernel_path": str(kernel_path) if kernel_path else None,
        "kernel_exists": bool(kernel_path and kernel_path.exists()),
        "rootfs_path": str(rootfs_path) if rootfs_path else None,
        "rootfs_exists": bool(rootfs_path and rootfs_path.exists()),
        "proof_manifest_path": str(manifest_path) if manifest_path else None,
        "proof_manifest_valid": False,
    }
    blockers: list[str] = []
    if not gates["linux"]:
        blockers.append("Linux required")
    if not gates["kvm_exists"]:
        blockers.append("/dev/kvm missing")
    elif not gates["kvm_rw"]:
        blockers.append("/dev/kvm not read/write accessible")
    if not binary:
        blockers.append("firecracker binary missing")
    if not gates["integration_gate"]:
        blockers.append("ARC_MICROVM_INTEGRATION=1 required")
    if not gates["real_exec_gate"]:
        blockers.append("ARC_FC_REAL_EXEC=1 required")
    if not gates["kernel_exists"]:
        blockers.append("ARC_FIRECRACKER_KERNEL missing/unreadable")
    if not gates["rootfs_exists"]:
        blockers.append("ARC_FIRECRACKER_ROOTFS missing/unreadable")
    if manifest_path:
        try:
            validate_firecracker_proof_manifest(manifest_path)
            gates["proof_manifest_valid"] = True
        except Exception as exc:
            blockers.append(f"ARC_FIRECRACKER_PROOF_ROOTFS_MANIFEST invalid: {exc}")
    gates["ready"] = not blockers
    gates["blockers"] = blockers
    return gates


def _terminate_process_group(proc: subprocess.Popen[str] | None) -> None:
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


def _run_firecracker_process(
    argv: list[str], *, timeout_seconds: int, max_bytes: int
) -> tuple[IsolationResult, subprocess.Popen[str] | None]:
    """Start Firecracker with process-group isolation and bounded pipe drain."""
    start = time.monotonic()
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout_raw, stderr_raw = proc.communicate(timeout=timeout_seconds)
            killed = False
            kill_reason = None
        except subprocess.TimeoutExpired:
            killed = True
            kill_reason = "timeout"
            _terminate_process_group(proc)
            stdout_raw, stderr_raw = proc.communicate()
        stdout, stdout_truncated = cap_output(stdout_raw or "", max_bytes)
        stderr, stderr_truncated = cap_output(stderr_raw or "", max_bytes)
        redacted_stdout = redact_output(stdout)
        redacted_stderr = redact_output(stderr)
        return (
            IsolationResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout=redacted_stdout,
                stderr=redacted_stderr,
                duration_ms=int((time.monotonic() - start) * 1000),
                pid=proc.pid,
                killed=killed,
                kill_reason=kill_reason,
                provider="microvm",
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
                redaction_applied=redacted_stdout != stdout or redacted_stderr != stderr,
            ),
            proc,
        )
    except Exception as exc:
        _terminate_process_group(proc)
        return (
            IsolationResult(
                exit_code=-1,
                stderr=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
                provider="microvm",
            ),
            proc,
        )


class FirecrackerProofRunner:
    """Private Linux/KVM host-gated Firecracker proof runner.

    This is a proof harness, not public microVM execution. It starts only when
    all proof gates are present. Guest command-channel proof remains blocked
    until ARC owns a rootfs/init/vsock/serial agent.
    """

    def __init__(
        self,
        *,
        workspace_root: Path,
        instance_name: str | None = None,
        max_bytes: int = 65_536,
    ) -> None:
        check_workspace_escape(workspace_root, workspace_root.parent)
        self.workspace_root = workspace_root.resolve()
        self.instance_name = instance_name or f"arc-fc-proof-{uuid.uuid4().hex[:12]}"
        self.max_bytes = max_bytes

    def run(self, command: list[str], *, timeout_seconds: int = 300) -> FirecrackerProofRunResult:
        if not command:
            raise ValueError("missing command")
        started_at = utc_now()
        gates = firecracker_proof_gates()
        if not gates["ready"]:
            message = "; ".join(gates["blockers"])
            result = self._blocked_result(command, message, started_at, utc_now())
            raise FirecrackerHarnessError(result.result.stderr)

        lifecycle: list[str] = ["preflight"]
        teardown_attempted = False
        proc: subprocess.Popen[str] | None = None
        result = IsolationResult(exit_code=-1, stderr="not started", provider="microvm")
        proof_blocker = "guest command channel requires ARC-owned rootfs/init/vsock/serial agent"
        with tempfile.TemporaryDirectory(prefix="arc-firecracker-proof-") as tmp:
            temp_dir = Path(tmp)
            api_socket = temp_dir / f"{self.instance_name}.socket"
            config_path = temp_dir / "firecracker.json"
            sentinel = self.workspace_root / "arc-sentinel.txt"
            escape = self.workspace_root / "arc-host-escape-link"
            created_escape = False
            if sentinel.exists() or escape.exists():
                reason = (
                    "proof workspace marker path already exists; refusing to overwrite user files"
                )
                blocked = self._blocked_result(command, reason, started_at, utc_now())
                raise FirecrackerHarnessError(blocked.result.stderr)
            sentinel.write_text("arc-firecracker-proof\n", encoding="utf-8")
            try:
                if not escape.exists():
                    escape.symlink_to(Path("/etc/passwd"))
                    created_escape = True
            except OSError:
                pass
            try:
                plan = build_firecracker_no_network_run_plan(
                    command,
                    kernel_path=Path(str(gates["kernel_path"])),
                    rootfs_path=Path(str(gates["rootfs_path"])),
                    work_dir=temp_dir,
                    instance_name=self.instance_name,
                )
                config_path.write_text(
                    json.dumps(plan.config.to_firecracker_config(), sort_keys=True),
                    encoding="utf-8",
                )
                lifecycle.append("create_config")
                argv = [
                    str(gates["firecracker_binary"]),
                    "--api-sock",
                    str(api_socket),
                    "--config-file",
                    str(config_path),
                ]
                result, proc = _run_firecracker_process(
                    argv, timeout_seconds=min(timeout_seconds, 30), max_bytes=self.max_bytes
                )
                lifecycle.append("start_vm")
                guest_proof = parse_firecracker_guest_proof(f"{result.stdout}\n{result.stderr}")
                proof_succeeded = (
                    guest_proof.network_proof_passed and guest_proof.workspace_proof_passed
                )
                if proof_succeeded:
                    lifecycle.append("guest_proof")
                    proof_blocker = None
                elif guest_proof.marker_seen:
                    lifecycle.append("guest_proof_failed")
                    proof_blocker = "guest proof markers did not satisfy network/workspace checks"
                else:
                    lifecycle.append("proof_blocked")
                teardown_attempted = True
                _terminate_process_group(proc)
                lifecycle.append("teardown")
                proof_exit_code = result.exit_code if proof_succeeded else -1
                harness_result = FirecrackerProofRunResult(
                    command=command,
                    instance_name=self.instance_name,
                    temp_dir=str(temp_dir),
                    api_socket=str(api_socket),
                    config_path=str(config_path),
                    result=IsolationResult(
                        exit_code=proof_exit_code,
                        stdout=result.stdout,
                        stderr=proof_blocker or result.stderr,
                        provider="microvm",
                        stdout_truncated=result.stdout_truncated,
                        stderr_truncated=result.stderr_truncated,
                        redaction_applied=result.redaction_applied,
                    ),
                    lifecycle=lifecycle,
                    no_default_route=guest_proof.no_default_route,
                    network_failure=guest_proof.network_failure,
                    workspace_sentinel_readable=guest_proof.sentinel_readable,
                    symlink_escape_blocked=guest_proof.symlink_escape_blocked,
                    teardown_attempted=True,
                    proof_blocker=proof_blocker,
                )
                self._persist_audit(
                    command=command,
                    lifecycle=lifecycle,
                    result=harness_result.result,
                    network_proof_passed=guest_proof.network_proof_passed,
                    teardown_attempted=teardown_attempted,
                    started_at=started_at,
                    ended_at=utc_now(),
                )
                return harness_result
            finally:
                sentinel.unlink(missing_ok=True)
                if created_escape:
                    escape.unlink(missing_ok=True)

    def _blocked_result(
        self, command: list[str], reason: str, started_at: str, ended_at: str
    ) -> FirecrackerProofRunResult:
        result = FirecrackerProofRunResult(
            command=command,
            instance_name=self.instance_name,
            temp_dir="",
            api_socket="",
            config_path="",
            result=IsolationResult(exit_code=-1, stderr=reason, provider="microvm"),
            lifecycle=["preflight"],
            teardown_attempted=False,
            proof_blocker=reason,
        )
        self._persist_audit(
            command=command,
            lifecycle=result.lifecycle,
            result=result.result,
            network_proof_passed=False,
            teardown_attempted=False,
            started_at=started_at,
            ended_at=ended_at,
        )
        return result

    def _persist_audit(
        self,
        *,
        command: list[str],
        lifecycle: list[str],
        result: IsolationResult,
        network_proof_passed: bool,
        teardown_attempted: bool,
        started_at: str,
        ended_at: str,
    ) -> None:
        event = build_microvm_audit_event(
            command=command,
            workspace_root=self.workspace_root,
            provider_runtime="firecracker",
            instance_name=self.instance_name,
            lifecycle=lifecycle,
            network_proof_passed=network_proof_passed,
            teardown_attempted=teardown_attempted,
            started_at=started_at,
            ended_at=ended_at,
            exit_code=result.exit_code,
            stdout_truncated=result.stdout_truncated,
            stderr_truncated=result.stderr_truncated,
            redaction_applied=result.redaction_applied,
        )
        persist_sandbox_audit_event(event)


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
    if normalized not in {"lima", "firecracker", "cloud-hypervisor"}:
        raise ValueError("provider must be lima, firecracker, or cloud-hypervisor")
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
            "strict network-off proof blocked: Lima default user-mode/slirp route is documented",
            "teardown proof missing",
            "opt-in integration test not passing on host runtime",
        ]
    elif normalized == "firecracker":
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
    else:
        steps = [
            MicroVMPlanStep(
                name="preflight",
                action="check cloud-hypervisor, /dev/kvm, kernel, disk image",
                proof_required="doctor reports ready without creating VM",
                implemented=True,
            ),
            MicroVMPlanStep(
                name="boot",
                action="boot cached kernel/disk with no --net options",
                proof_required="pinned image provenance and bounded boot timeout",
            ),
            MicroVMPlanStep(
                name="mount",
                action="attach workspace through virtiofs or guest-agent strategy",
                proof_required="symlink/hardlink escape proof",
            ),
            MicroVMPlanStep(
                name="network_proof",
                action="run ip route and curl failure probes before user argv",
                proof_required="guest has no default route and curl fails",
            ),
            MicroVMPlanStep(
                name="run",
                action="send argv to guest agent via vsock/serial channel",
                proof_required="stdout/stderr caps, env policy, exit-code propagation",
            ),
            MicroVMPlanStep(
                name="teardown",
                action="terminate Cloud Hypervisor process group and remove socket/temp dir",
                proof_required="cleanup happens on boot failure, run timeout, and interrupted host process",
            ),
        ]
        blockers = [
            "kernel/disk cache provenance missing",
            "guest command agent missing",
            "workspace mount strategy unproven",
            "network-off proof missing",
            "teardown proof missing",
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
            ["cat", "/workspace/arc-sentinel.txt"],
            ["cat", "/workspace/arc-host-escape-link"],
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


def build_cloud_hypervisor_no_network_run_plan(
    command: list[str],
    *,
    kernel_path: Path,
    disk_path: Path,
    work_dir: Path,
    instance_name: str | None = None,
) -> CloudHypervisorNoNetworkRunPlan:
    """Build a non-executing Cloud Hypervisor no-NIC proof plan."""
    if not command:
        raise ValueError("missing command")
    name = instance_name or f"arc-ch-{uuid.uuid4().hex[:12]}"
    config = CloudHypervisorNoNetworkConfig(
        api_socket=str(work_dir / f"{name}.sock"),
        kernel_path=str(kernel_path),
        disk_path=str(disk_path),
    )
    return CloudHypervisorNoNetworkRunPlan(
        command=command,
        proof_commands=[
            ["ip", "route"],
            ["curl", "--connect-timeout", "2", "https://example.com"],
            ["cat", "/workspace/arc-sentinel.txt"],
            ["cat", "/workspace/arc-host-escape-link"],
        ],
        config=config,
        teardown_actions=[
            "terminate cloud-hypervisor process group",
            "remove api socket",
            "remove temporary work directory",
        ],
        host_gates=[
            "Linux",
            "ARC_MICROVM_INTEGRATION=1",
            "ARC_CH_REAL_EXEC=1",
            "ARC_CLOUDHYPERVISOR_KERNEL",
            "ARC_CLOUDHYPERVISOR_DISK",
            "cloud-hypervisor binary",
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
    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        killed = False
        kill_reason: str | None = None
        assert proc.stdout is not None
        assert proc.stderr is not None
        stdout_reader = _BoundedPipeReader(proc.stdout, max_bytes)
        stderr_reader = _BoundedPipeReader(proc.stderr, max_bytes)
        stdout_reader.start()
        stderr_reader.start()
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
        stdout_reader.join()
        stderr_reader.join()
        stdout_raw = stdout_reader.text()
        stderr_raw = stderr_reader.text()
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
            stdout_truncated=stdout_reader.truncated,
            stderr_truncated=stderr_reader.truncated,
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
        proof_mode: str = "strict",
    ) -> LimaHarnessResult:
        """Run the gated Lima low-security developer harness lifecycle.

        ``proof_mode="mount"`` bypasses only the network gate so a developer can
        collect guest-side /workspace mount and symlink evidence on Lima, whose
        default networking is known network-present. It is not strict sandbox
        execution and is never wired to public microVM execution.
        """
        if require_gate and not lima_integration_available():
            raise RuntimeError("ARC_MICROVM_INTEGRATION=1, macOS, and limactl are required")
        if not command:
            raise ValueError("missing command")
        if proof_mode not in {"strict", "mount"}:
            raise ValueError("proof_mode must be 'strict' or 'mount'")
        tmp_path = self._write_template()
        network_proof_passed = False
        teardown_attempted = False
        result = IsolationResult(exit_code=-1, stderr="not started", provider="microvm")
        started_at = utc_now()
        try:
            start = self._limactl(
                ["start", "--tty=false", "--name", self.instance_name, str(tmp_path)],
                timeout_seconds,
            )
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
                if not network_proof_passed and proof_mode == "strict":
                    result = IsolationResult(
                        exit_code=-1,
                        stderr="network-off proof failed: guest has a default route",
                        provider="microvm",
                    )
                else:
                    if proof_mode == "mount" and not network_proof_passed:
                        self.lifecycle.append("mount_proof_network_bypass")
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
        return False

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
            "public_execution_enabled": False,
            "public_execution_status": "blocked",
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
        info.update(
            {
                "available": False,
                "public_execution_enabled": False,
                "public_execution_status": "blocked",
                "contract_doc": "docs/adr/ADR-024-microvm-public-execution-contract.md",
            }
        )
        if _microvm_execution_enabled() and _lima_available():
            info["execution"] = "gated_unproven"
            info["reason"] = (
                "ARC_MICROVM_INTEGRATION=1 is set and limactl is present, but public "
                "microVM execution remains disabled until ADR-024 prerequisites are met"
            )
        return info
