"""Sandbox policy, classification, and audit helpers."""

from __future__ import annotations

import json
import os
import platform
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..audit.chain import GENESIS, canonical_dumps, sha256_hex, verify


class CommandClassification(str, Enum):
    """Coarse command risk classes used by sandbox policy."""

    READ_ONLY = "read_only"
    WRITES_WORKSPACE = "writes_workspace"
    NETWORK = "network"
    INSTALL = "install"
    DESTRUCTIVE = "destructive"
    PRIVILEGED = "privileged"
    UNKNOWN = "unknown"


class SandboxPolicy(BaseModel):
    """Policy controlling sandbox command execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    name: str = "local-safe"
    workspace_root: Path = Field(default_factory=Path.cwd)
    allow_network: bool = False
    allow_install: bool = False
    allow_privileged: bool = False
    allow_unknown: bool = False
    timeout_seconds: int = 30
    max_output_bytes: int = 65_536
    env_allowlist: tuple[str, ...] = (
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "TERM",
        "TMPDIR",
        "VIRTUAL_ENV",
        "PYTHONPATH",
        "PYTHONWARNINGS",
    )


class SandboxDecision(BaseModel):
    """Allow/deny decision for a sandbox command."""

    allowed: bool
    classification: CommandClassification
    reason: str
    policy: str


class SandboxResult(BaseModel):
    """Stable JSON result for `arc sandbox run`."""

    command: list[str]
    cwd: str
    classification: CommandClassification
    decision: SandboxDecision
    provider: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    redaction_applied: bool = False
    audit_event: dict[str, Any]


READ_ONLY_COMMANDS = {
    "cat",
    "find",
    "git",
    "head",
    "ls",
    "pwd",
    "rg",
    "sed",
    "tail",
    "tree",
    "wc",
}
NETWORK_COMMANDS = {"curl", "wget", "ssh", "scp", "rsync", "nc", "telnet", "ping"}
INSTALL_COMMANDS = {"pip", "uv", "npm", "pnpm", "yarn", "brew", "apt", "apt-get", "dnf", "yum"}
DESTRUCTIVE_COMMANDS = {"rm", "rmdir", "mv", "dd", "mkfs", "truncate", "shred"}
PRIVILEGED_COMMANDS = {
    "sudo",
    "su",
    "doas",
    "chmod",
    "chown",
    "mount",
    "umount",
    "launchctl",
    "systemctl",
}
WRITE_SHELL_TOKENS = {">", ">>", "tee"}


def utc_now() -> str:
    """Return an RFC3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def classify_command(command: list[str]) -> CommandClassification:
    """Classify argv without executing it."""
    if not command:
        return CommandClassification.UNKNOWN
    exe = Path(command[0]).name
    args = command[1:]
    if exe in PRIVILEGED_COMMANDS:
        return CommandClassification.PRIVILEGED
    if exe in DESTRUCTIVE_COMMANDS:
        return CommandClassification.DESTRUCTIVE
    if exe in NETWORK_COMMANDS:
        return CommandClassification.NETWORK
    if exe in INSTALL_COMMANDS:
        install_markers = {"install", "add", "update", "upgrade", "sync"}
        if exe in {"brew", "apt", "apt-get", "dnf", "yum"} or install_markers.intersection(args):
            return CommandClassification.INSTALL
    if any(token in WRITE_SHELL_TOKENS for token in command):
        return CommandClassification.WRITES_WORKSPACE
    if exe == "python":
        code = " ".join(args)
        if "open(" in code and "w" in code:
            return CommandClassification.WRITES_WORKSPACE
        if "-c" in args and "print(" in code:
            return CommandClassification.READ_ONLY
    if exe in READ_ONLY_COMMANDS:
        if (
            exe == "git"
            and args
            and args[0] not in {"status", "diff", "log", "show", "branch", "rev-parse"}
        ):
            return CommandClassification.UNKNOWN
        return CommandClassification.READ_ONLY
    return CommandClassification.UNKNOWN


def decide(command: list[str], policy: SandboxPolicy) -> SandboxDecision:
    """Evaluate a command under a sandbox policy."""
    classification = classify_command(command)
    if classification == CommandClassification.READ_ONLY:
        return SandboxDecision(
            allowed=True,
            classification=classification,
            reason="read-only command",
            policy=policy.name,
        )
    if classification == CommandClassification.WRITES_WORKSPACE:
        return SandboxDecision(
            allowed=True,
            classification=classification,
            reason="workspace writes allowed",
            policy=policy.name,
        )
    if classification == CommandClassification.NETWORK:
        return SandboxDecision(
            allowed=policy.allow_network,
            classification=classification,
            reason="network policy",
            policy=policy.name,
        )
    if classification == CommandClassification.INSTALL:
        return SandboxDecision(
            allowed=policy.allow_install,
            classification=classification,
            reason="install policy",
            policy=policy.name,
        )
    if classification == CommandClassification.PRIVILEGED:
        return SandboxDecision(
            allowed=policy.allow_privileged,
            classification=classification,
            reason="privileged policy",
            policy=policy.name,
        )
    if classification == CommandClassification.DESTRUCTIVE:
        return SandboxDecision(
            allowed=False,
            classification=classification,
            reason="destructive commands denied",
            policy=policy.name,
        )
    return SandboxDecision(
        allowed=policy.allow_unknown,
        classification=classification,
        reason="unknown command policy",
        policy=policy.name,
    )


def ensure_workspace_cwd(cwd: Path, workspace_root: Path) -> Path:
    """Resolve and verify cwd stays inside workspace and is not a symlink."""
    root = workspace_root.resolve()
    candidate = cwd.resolve()
    if cwd.is_symlink() or not candidate.is_relative_to(root):
        raise ValueError(f"cwd escapes workspace: {cwd}")
    return candidate


def cap_output(text: str, max_bytes: int) -> tuple[str, bool]:
    """Cap output by UTF-8 bytes while preserving valid text."""
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text, False
    return data[:max_bytes].decode("utf-8", errors="replace"), True


def build_audit_event(
    *,
    command: list[str],
    cwd: Path,
    decision: SandboxDecision,
    provider: str,
    started_at: str,
    ended_at: str,
    exit_code: int | None,
    stdout_truncated: bool,
    stderr_truncated: bool,
    redaction_applied: bool,
) -> dict[str, Any]:
    """Build a stable sandbox audit event payload."""
    return {
        "type": "SANDBOX_COMMAND" if decision.allowed else "SANDBOX_DENIED",
        "command": command,
        "cwd": str(cwd),
        "classification": decision.classification.value,
        "decision": decision.model_dump(mode="json"),
        "policy": decision.policy,
        "provider": provider,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "started_at": started_at,
        "ended_at": ended_at,
        "exit_code": exit_code,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "redaction_applied": redaction_applied,
    }


def microvm_preflight(system: str | None = None) -> dict[str, Any]:
    """Detect lightweight microVM runtime availability without executing workloads."""
    os_name = system or platform.system()
    if os_name == "Linux":
        binary = shutil.which("firecracker") or shutil.which("cloud-hypervisor")
        jailer = shutil.which("jailer")
        kvm = Path("/dev/kvm")
        kvm_exists = kvm.exists()
        kvm_rw = os.access(kvm, os.R_OK | os.W_OK) if kvm_exists else False
        kernel_cache = os.environ.get("ARC_FIRECRACKER_KERNEL")
        rootfs_cache = os.environ.get("ARC_FIRECRACKER_ROOTFS")
        cache_ready = bool(
            kernel_cache
            and Path(kernel_cache).exists()
            and rootfs_cache
            and Path(rootfs_cache).exists()
        )
        ready = bool(binary and jailer and kvm_exists and kvm_rw and cache_ready)
        status = "ready" if ready else "installed_not_configured" if binary else "unavailable"
        return {
            "provider": "microvm",
            "platform": "linux",
            "status": status,
            "binary": binary,
            "jailer": jailer,
            "kvm": kvm_exists,
            "kvm_rw": kvm_rw,
            "kernel_cache": kernel_cache,
            "rootfs_cache": rootfs_cache,
            "cache_ready": cache_ready,
        }
    if os_name == "Darwin":
        limactl = shutil.which("limactl")
        status = "installed_not_configured" if limactl else "unavailable"
        return {
            "provider": "microvm",
            "platform": "macos",
            "status": status,
            "binary": limactl,
            "runtime": "lima-vz",
        }
    return {
        "provider": "microvm",
        "platform": os_name.lower(),
        "status": "blocked",
        "reason": "Windows/unsupported platform skipped",
    }


def stable_json(data: Any) -> str:
    """Dump stable JSON for docs/tests."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def sandbox_policy_store_path() -> Path:
    """Return the sandbox policy config path."""
    override = os.environ.get("ARC_SANDBOX_POLICY_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arc" / "sandbox-policies.json"


def resolve_sandbox_policy(
    name: str, workspace_root: Path, path: Path | None = None
) -> SandboxPolicy:
    """Resolve a built-in or JSON-configured sandbox policy."""
    if name == "local-safe":
        return SandboxPolicy(name=name, workspace_root=workspace_root)
    store_path = path or sandbox_policy_store_path()
    if not store_path.exists():
        raise KeyError(f"Sandbox policy not found: {name}")
    raw = json.loads(store_path.read_text(encoding="utf-8"))
    _validate_policy_config_shape(raw)
    for item in raw.get("policies", []):
        if item.get("name") == name:
            payload = {**item, "workspace_root": workspace_root}
            return SandboxPolicy.model_validate(payload)
    raise KeyError(f"Sandbox policy not found: {name}")


def list_sandbox_policies(workspace_root: Path, path: Path | None = None) -> list[SandboxPolicy]:
    """List built-in and configured sandbox policies."""
    policies = [SandboxPolicy(name="local-safe", workspace_root=workspace_root)]
    store_path = path or sandbox_policy_store_path()
    if not store_path.exists():
        return policies
    raw = json.loads(store_path.read_text(encoding="utf-8"))
    _validate_policy_config_shape(raw)
    for item in raw.get("policies", []):
        payload = {**item, "workspace_root": workspace_root}
        policies.append(SandboxPolicy.model_validate(payload))
    return policies


def validate_sandbox_policy_config(path: Path | None = None) -> dict[str, Any]:
    """Validate sandbox policy config and return a stable report."""
    store_path = path or sandbox_policy_store_path()
    if not store_path.exists():
        return {"ok": True, "path": str(store_path), "policies": [], "errors": []}
    try:
        raw = json.loads(store_path.read_text(encoding="utf-8"))
        shape_errors = _policy_config_shape_errors(raw)
        if shape_errors:
            return {
                "ok": False,
                "path": str(store_path),
                "policies": raw.get("policies", []) if isinstance(raw, dict) else [],
                "errors": shape_errors,
            }
        policies = raw.get("policies", [])
        errors: list[dict[str, Any]] = []
        names: set[str] = {"local-safe"}
        for index, item in enumerate(policies):
            try:
                policy = SandboxPolicy.model_validate({**item, "workspace_root": Path.cwd()})
                if policy.name in names:
                    errors.append(
                        {"index": index, "error": f"duplicate policy name: {policy.name}"}
                    )
                names.add(policy.name)
            except ValidationError as exc:
                errors.append({"index": index, "error": str(exc)})
        return {"ok": not errors, "path": str(store_path), "policies": policies, "errors": errors}
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "path": str(store_path),
            "policies": [],
            "errors": [{"error": str(exc)}],
        }


def _policy_config_shape_errors(raw: Any) -> list[dict[str, Any]]:
    """Return top-level sandbox policy config shape errors."""
    if not isinstance(raw, dict):
        return [{"error": "config must be a JSON object"}]
    allowed = {"version", "policies"}
    unknown = sorted(set(raw) - allowed)
    errors: list[dict[str, Any]] = []
    if unknown:
        errors.append({"error": f"unknown top-level fields: {', '.join(unknown)}"})
    if raw.get("version") != 1:
        errors.append({"error": "version must be 1"})
    if not isinstance(raw.get("policies"), list):
        errors.append({"error": "policies must be a list"})
    return errors


def _validate_policy_config_shape(raw: Any) -> None:
    errors = _policy_config_shape_errors(raw)
    if errors:
        raise ValueError(errors[0]["error"])


def sandbox_audit_dir() -> Path:
    """Return external sandbox audit directory."""
    override = os.environ.get("ARC_SANDBOX_AUDIT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arc" / "audit"


def persist_sandbox_audit_event(event: dict[str, Any], audit_dir: Path | None = None) -> Path:
    """Persist a sandbox audit event into the hash-chain audit store."""
    target_dir = audit_dir or sandbox_audit_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    chain_path = target_dir / "sandbox.audit.jsonl"
    events_path = target_dir / "sandbox.events.jsonl"
    with events_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    prev_hash = GENESIS
    seq = 0
    if chain_path.exists():
        lines = [
            json.loads(line)
            for line in chain_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if lines:
            prev_hash = str(lines[-1]["chain_hash"])
            seq = int(lines[-1]["seq"]) + 1
    event_hash = sha256_hex(canonical_dumps(event))
    chain_hash = sha256_hex(f"{prev_hash}:{event_hash}".encode("utf-8"))
    record = {
        "seq": seq,
        "ts": utc_now(),
        "event_hash": event_hash,
        "prev_hash": prev_hash,
        "chain_hash": chain_hash,
    }
    with chain_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, separators=(",", ":")) + "\n")
    return chain_path


def verify_sandbox_audit(audit_dir: Path | None = None) -> dict[str, Any]:
    """Verify sandbox audit chain against raw events."""
    target_dir = audit_dir or sandbox_audit_dir()
    chain_path = target_dir / "sandbox.audit.jsonl"
    events_path = target_dir / "sandbox.events.jsonl"
    if not chain_path.exists() or not events_path.exists():
        return {
            "ok": False,
            "chain": str(chain_path),
            "events": str(events_path),
            "reason": "sandbox audit files not found",
        }
    ok, reason = verify(chain_path, events_path)
    return {"ok": ok, "chain": str(chain_path), "events": str(events_path), "reason": reason}


def list_sandbox_audit_events(
    audit_dir: Path | None = None,
    *,
    allowed: bool | None = None,
    classification: str | None = None,
    provider: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List sandbox audit events with simple filters."""
    target_dir = audit_dir or sandbox_audit_dir()
    events_path = target_dir / "sandbox.events.jsonl"
    if not events_path.exists():
        return {"events": [], "path": str(events_path), "count": 0}
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if allowed is not None:
        events = [event for event in events if event.get("allowed") is allowed]
    if classification:
        events = [event for event in events if event.get("classification") == classification]
    if provider:
        events = [event for event in events if event.get("provider") == provider]
    if limit >= 0:
        events = events[-limit:]
    return {"events": events, "path": str(events_path), "count": len(events)}


def render_lima_template(workspace_root: Path, instance_name: str = "arc-sandbox") -> str:
    """Render an experimental Lima VZ template; gated by caller."""
    workspace = str(workspace_root.resolve())
    return f"""# ARC experimental Lima sandbox template. Execution not wired yet.
vmType: vz
images:
  - location: https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-$(arch).img
mounts:
  - location: {workspace}
    mountPoint: /workspace
    writable: true
networks: []
portForwards: []
provision:
  - mode: system
    script: |
      set -eu
      mkdir -p /workspace
message: "ARC experimental instance {instance_name}; network must be proven disabled before execution."
"""
