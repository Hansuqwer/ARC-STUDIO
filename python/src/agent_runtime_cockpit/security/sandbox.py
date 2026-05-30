"""Sandbox policy, classification, and audit helpers."""

from __future__ import annotations

import ast
import json
import os
import platform
import subprocess
import shutil
import stat
import uuid
from datetime import datetime, timedelta, timezone
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
    interactive_approval: bool = False
    network_approval_required: bool = True
    install_approval_required: bool = True
    unknown_approval_required: bool = True
    approval_ttl_seconds: int = 86_400
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
    approval_required: bool = False
    approved: bool = False


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


class SandboxApproval(BaseModel):
    """Persisted non-interactive sandbox approval."""

    token: str = ""
    token_hash: str = ""
    policy: str
    workspace_root: str
    classification: CommandClassification
    command_hash: str
    created_at: str
    expires_at: str | None = None


class SandboxApprovalStore(BaseModel):
    """Stable JSON approval-store envelope."""

    version: Literal[1] = 1
    approvals: list[SandboxApproval] = Field(default_factory=list)


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
INSTALL_COMMANDS = {
    "pip",
    "pip3",
    "uv",
    "npm",
    "pnpm",
    "yarn",
    "brew",
    "apt",
    "apt-get",
    "dnf",
    "yum",
}
SAFE_CI_PACKAGE_SCRIPTS = {"build", "check", "check:pr", "lint", "test", "typecheck"}
SAFE_CI_UV_TOOLS = {"pytest", "ruff", "mypy"}
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
SHELL_COMMANDS = {"sh", "bash", "zsh"}
INTERPRETERS = {"python", "python3", "node", "ruby", "perl"}
WRITE_COMMANDS = {"touch", "mkdir", "ln", "cp", "tee", "unzip", "install"}
GIT_DESTRUCTIVE_SUBCOMMANDS = {"branch", "clean", "checkout", "restore", "rm", "switch", "worktree"}
GIT_NETWORK_SUBCOMMANDS = {"clone", "fetch", "pull", "push", "remote", "submodule"}
GIT_HARD_RESET = {"reset", "--hard"}
GIT_CHECKOUT_FORCE = {"checkout", "--"}
PACKAGE_MANAGER_MODULES = {"pip"}
NETWORK_HINTS = {"socket", "requests", "urllib", "http.client", "subprocess", "os.system"}
NODE_NETWORK_HINTS = {"http", "https", "net", "dgram", "fetch", "axios", "node-fetch"}
RUBY_NETWORK_HINTS = {"socket", "net/http", "open-uri", "httparty", "faraday"}
PERL_NETWORK_HINTS = {"LWP", "HTTP::Tiny", "IO::Socket", "Net::HTTP", "Mojo::UserAgent"}
SHELL_NETWORK_HINTS = {"curl", "wget", "nc", "ssh", "scp", "rsync", "ping"}
SHELL_PRIVILEGED_HINTS = {"sudo", "su ", "doas", "chmod", "chown", "mount", "umount"}
SHELL_DESTRUCTIVE_HINTS = {"rm ", "rm -", "rmdir", "dd ", "mkfs", "truncate", "shred"}
WRITE_HINTS = {"open", "write_text", "write_bytes", "Path("}


class SandboxPathViolation(ValueError):
    """Raised when command path intent escapes the workspace."""


WRITE_PATH_OPTIONS = {
    "-o",
    "--output",
    "--output-document",
    "--outfile",
    "--out",
    "--dest",
    "--destination",
}
READ_PATH_OPTIONS = {"-f", "--file", "--files-from", "--exclude-from", "--include-from"}
WRITE_PATH_PREFIXES = {
    "--output=",
    "--output-document=",
    "--outfile=",
    "--out=",
    "--dest=",
    "--destination=",
    "of=",
}


def utc_now() -> str:
    """Return an RFC3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now_plus(seconds: int) -> str:
    """Return an RFC3339 UTC timestamp seconds from now."""
    return (
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
    )


def classify_command(command: list[str]) -> CommandClassification:
    """Classify argv without executing it."""
    if not command:
        return CommandClassification.UNKNOWN
    exe = Path(command[0]).name
    args = command[1:]
    if exe in PRIVILEGED_COMMANDS:
        return CommandClassification.PRIVILEGED
    if exe == "git":
        if args and args[0] in GIT_NETWORK_SUBCOMMANDS:
            return CommandClassification.NETWORK
        if args and args[0] in {"clean", "rm", "worktree"}:
            return CommandClassification.DESTRUCTIVE
        if args[:1] == ["reset"] and "--hard" in args:
            return CommandClassification.DESTRUCTIVE
        if args[:1] == ["checkout"] and ("--" in args or "-f" in args or "--force" in args):
            return CommandClassification.DESTRUCTIVE
        if args[:1] == ["restore"] and ({"--worktree", "--staged"} & set(args)):
            return CommandClassification.DESTRUCTIVE
        if args[:1] == ["switch"] and ("-f" in args or "--force" in args):
            return CommandClassification.DESTRUCTIVE
        if args[:1] == ["branch"] and ("-D" in args or "--delete" in args):
            return CommandClassification.DESTRUCTIVE
    if exe == "find":
        if "-delete" in args or ("-exec" in args and any(Path(a).name == "rm" for a in args)):
            return CommandClassification.DESTRUCTIVE
        if "-exec" in args:
            return CommandClassification.UNKNOWN
    if exe == "sed" and any(a == "-i" or a.startswith("-i") for a in args):
        return CommandClassification.WRITES_WORKSPACE
    if exe == "tar" and any(a == "--overwrite" or a.startswith("--overwrite=") for a in args):
        return CommandClassification.DESTRUCTIVE
    if exe == "rsync":
        return CommandClassification.NETWORK
    if exe in DESTRUCTIVE_COMMANDS:
        return CommandClassification.DESTRUCTIVE
    if exe in NETWORK_COMMANDS:
        return CommandClassification.NETWORK
    if exe in INSTALL_COMMANDS:
        install_markers = {"i", "install", "add", "update", "upgrade", "sync"}
        if exe in {"brew", "apt", "apt-get", "dnf", "yum"} or install_markers.intersection(args):
            return CommandClassification.INSTALL
        if exe in {"npm", "pnpm", "yarn"} and args:
            script = args[0]
            if script in {"run", "exec"} and len(args) > 1:
                script = args[1]
            if script in SAFE_CI_PACKAGE_SCRIPTS or script.startswith("test:"):
                return CommandClassification.WRITES_WORKSPACE
        if exe == "uv" and len(args) >= 2 and args[0] == "run" and args[1] in SAFE_CI_UV_TOOLS:
            return CommandClassification.WRITES_WORKSPACE
    if exe == "install":
        return CommandClassification.INSTALL
    if exe in WRITE_COMMANDS:
        return CommandClassification.WRITES_WORKSPACE
    if any(token in WRITE_SHELL_TOKENS for token in command):
        return CommandClassification.WRITES_WORKSPACE
    if exe in {"python", "python3"}:
        if len(args) >= 2 and args[0] == "-m" and args[1] in PACKAGE_MANAGER_MODULES:
            return CommandClassification.INSTALL
        if len(args) >= 4 and args[:3] == ["-m", "uv", "pip"] and args[3] in {"install", "sync"}:
            return CommandClassification.INSTALL
        code = " ".join(args)
        if any(hint in code for hint in NETWORK_HINTS):
            return CommandClassification.NETWORK
        if any(hint in code for hint in WRITE_HINTS) and (
            any(mode in code for mode in ("'w'", '"w"', "'a'", '"a"', "'wb'", '"wb"'))
            or "write_text" in code
            or "write_bytes" in code
        ):
            return CommandClassification.WRITES_WORKSPACE
        if "-c" in args and "print(" in code:
            return CommandClassification.READ_ONLY
        if "-c" in args:
            return CommandClassification.UNKNOWN
    if exe in {"node", "ruby", "perl"} and any(a in {"-e", "-c"} for a in args):
        code = " ".join(args)
        if exe == "node" and any(hint in code for hint in NODE_NETWORK_HINTS):
            return CommandClassification.NETWORK
        if exe == "ruby" and any(hint in code for hint in RUBY_NETWORK_HINTS):
            return CommandClassification.NETWORK
        if exe == "perl" and any(hint in code for hint in PERL_NETWORK_HINTS):
            return CommandClassification.NETWORK
        if any(hint in code for hint in NETWORK_HINTS):
            return CommandClassification.NETWORK
        return CommandClassification.UNKNOWN
    if exe in SHELL_COMMANDS and any(arg in {"-c", "-lc"} for arg in args):
        code = " ".join(args)
        if any(hint in code for hint in SHELL_PRIVILEGED_HINTS):
            return CommandClassification.PRIVILEGED
        if any(hint in code for hint in SHELL_DESTRUCTIVE_HINTS):
            return CommandClassification.DESTRUCTIVE
        if any(hint in code for hint in SHELL_NETWORK_HINTS):
            return CommandClassification.NETWORK
        if any(hint in code for hint in NETWORK_HINTS):
            return CommandClassification.NETWORK
        return CommandClassification.UNKNOWN
    if exe in READ_ONLY_COMMANDS:
        if (
            exe == "git"
            and args
            and args[0] not in {"status", "diff", "log", "show", "branch", "rev-parse"}
        ):
            return CommandClassification.UNKNOWN
        return CommandClassification.READ_ONLY
    return CommandClassification.UNKNOWN


def validate_command_paths(command: list[str], policy: SandboxPolicy) -> None:
    """Deny path intents that escape the workspace before execution."""
    if not command:
        return
    classification = classify_command(command)
    root = policy.workspace_root.resolve()
    exe = Path(command[0]).name
    paths = _extract_path_intents(command)
    if _requires_static_path_proof(command, classification, policy):
        raise SandboxPathViolation("dynamic shell/interpreter command cannot be safely approved")
    for path in paths:
        if _is_write_path_intent(path) and not _path_within_workspace(
            _write_path_value(path), root
        ):
            raise SandboxPathViolation(f"write path escapes workspace: {_write_path_value(path)}")
    if classification == CommandClassification.READ_ONLY:
        for path in paths:
            value = _path_value(path)
            if not _path_within_workspace(value, root):
                raise SandboxPathViolation(f"read path escapes workspace: {value}")
        return
    if classification != CommandClassification.WRITES_WORKSPACE:
        return
    if exe in INTERPRETERS and not paths:
        raise SandboxPathViolation("write-capable interpreter lacks statically validated path")
    for path in paths:
        value = _path_value(path)
        if not _path_within_workspace(value, root):
            raise SandboxPathViolation(f"write path escapes workspace: {value}")


def _requires_static_path_proof(
    command: list[str], classification: CommandClassification, policy: SandboxPolicy
) -> bool:
    exe = Path(command[0]).name if command else ""
    if classification != CommandClassification.UNKNOWN or policy.allow_unknown:
        return False
    if exe in SHELL_COMMANDS:
        return any(arg in {"-c", "-lc"} for arg in command[1:])
    return exe in INTERPRETERS or exe in {"node", "ruby", "perl"}


def _path_value(path: str) -> str:
    return path[6:] if path.startswith("write:") else path


def _write_path_value(path: str) -> str:
    return path[6:]


def _is_write_path_intent(path: str) -> bool:
    return path.startswith("write:")


def _path_within_workspace(path: str, root: Path) -> bool:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        return False
    if candidate.exists() and candidate.is_symlink():
        return False
    return resolved.is_relative_to(root)


def _extract_path_intents(command: list[str]) -> list[str]:
    exe = Path(command[0]).name if command else ""
    args = command[1:]
    paths: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in WRITE_PATH_OPTIONS | READ_PATH_OPTIONS and i + 1 < len(args):
            paths.append(("write:" if arg in WRITE_PATH_OPTIONS else "") + args[i + 1])
            i += 2
            continue
        for opt in WRITE_PATH_OPTIONS | READ_PATH_OPTIONS:
            prefix = opt + "="
            if arg.startswith(prefix):
                paths.append(("write:" if opt in WRITE_PATH_OPTIONS else "") + arg[len(prefix) :])
                break
        for prefix in WRITE_PATH_PREFIXES:
            if arg.startswith(prefix):
                paths.append("write:" + arg[len(prefix) :])
                break
        i += 1
    if exe in {"python", "python3"} and "-c" in args:
        idx = args.index("-c")
        if idx + 1 < len(args):
            paths.extend(_extract_python_code_paths(args[idx + 1]))
    if exe in {"tee", "truncate"}:
        paths.extend("write:" + a for a in args if not a.startswith("-"))
    if exe == "dd":
        paths.extend("write:" + a[3:] for a in args if a.startswith("of="))
    if exe in {"cp", "mv"} and len([a for a in args if not a.startswith("-")]) >= 2:
        paths.append("write:" + [a for a in args if not a.startswith("-")][-1])
    if exe == "tar":
        paths.extend(a for a in args if a.endswith((".tar", ".tgz", ".zip")))
        if "-C" in args:
            idx = args.index("-C")
            if idx + 1 < len(args):
                paths.append("write:" + args[idx + 1])
    if exe == "zip":
        paths.extend(a for a in args if a.endswith((".tar", ".tgz", ".zip")))
    if exe == "unzip":
        paths.extend(a for a in args if a.endswith((".tar", ".tgz", ".zip")))
        if "-d" in args:
            idx = args.index("-d")
            if idx + 1 < len(args):
                paths.append("write:" + args[idx + 1])
    if exe == "ln" and len([a for a in args if not a.startswith("-")]) >= 2:
        paths.append("write:" + [a for a in args if not a.startswith("-")][-1])
    if exe in {"touch", "mkdir"}:
        paths.extend("write:" + a for a in args if not a.startswith("-"))
    if exe == "install":
        if "-d" in args:
            paths.extend("write:" + a for a in args if not a.startswith("-"))
        elif len([a for a in args if not a.startswith("-")]) >= 2:
            paths.append("write:" + [a for a in args if not a.startswith("-")][-1])
    if exe in READ_ONLY_COMMANDS:
        paths.extend(
            a for a in args if a and not a.startswith("-") and not _looks_like_git_revision(a)
        )
    return paths


def _looks_like_git_revision(value: str) -> bool:
    return ":" in value or value in {"HEAD", "FETCH_HEAD", "ORIG_HEAD"}


def _extract_python_code_paths(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    paths: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in {"open", "write_text", "write_bytes"} and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    paths.append("write:" + first.value)
            if name in {"write_text", "write_bytes"} and isinstance(func, ast.Attribute):
                target = func.value
                if (
                    isinstance(target, ast.Call)
                    and getattr(target.func, "id", "") == "Path"
                    and target.args
                ):
                    first = target.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        paths.append("write:" + first.value)
    return paths


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
        allowed = policy.allow_network
        approval_required = policy.network_approval_required and not policy.allow_network
        return SandboxDecision(
            allowed=allowed,
            classification=classification,
            reason="network policy",
            policy=policy.name,
            approval_required=approval_required,
        )
    if classification == CommandClassification.INSTALL:
        allowed = policy.allow_install
        approval_required = policy.install_approval_required and not policy.allow_install
        return SandboxDecision(
            allowed=allowed,
            classification=classification,
            reason="install policy",
            policy=policy.name,
            approval_required=approval_required,
        )
    if classification == CommandClassification.PRIVILEGED:
        # Privileged commands are always denied by default and cannot be approved
        return SandboxDecision(
            allowed=False,
            classification=classification,
            reason="privileged commands denied",
            policy=policy.name,
        )
    if classification == CommandClassification.DESTRUCTIVE:
        # Destructive commands are always denied and cannot be approved
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
        approval_required=policy.unknown_approval_required and not policy.allow_unknown,
    )


def approve_decision(
    decision: SandboxDecision, reason: str = "interactive approval"
) -> SandboxDecision:
    """Return an approved copy for categories allowed by interactive UX.

    Note: Destructive and privileged commands can never be approved.
    """
    # Never allow approval for destructive or privileged commands
    if decision.classification in {
        CommandClassification.DESTRUCTIVE,
        CommandClassification.PRIVILEGED,
    }:
        return decision
    if decision.classification not in {
        CommandClassification.NETWORK,
        CommandClassification.INSTALL,
        CommandClassification.UNKNOWN,
    }:
        return decision
    return SandboxDecision(
        allowed=True,
        classification=decision.classification,
        reason=reason,
        policy=decision.policy,
        approval_required=True,
        approved=True,
    )


def sandbox_approval_store_path() -> Path:
    """Return the non-interactive approval store path."""
    override = os.environ.get("ARC_SANDBOX_APPROVAL_STORE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arc" / "approvals.json"


def approval_command_hash(command: list[str]) -> str:
    """Return stable command digest for approval scoping."""
    return sha256_hex(canonical_dumps(command))


def approval_token_hash(token: str) -> str:
    """Return stable token digest for approval storage."""
    return sha256_hex(canonical_dumps({"token": token, "purpose": "sandbox-approval"}))


def approval_is_expired(approval: SandboxApproval, now: str | None = None) -> bool:
    """Return True when an approval TTL has elapsed."""
    if not approval.expires_at:
        return False
    return approval.expires_at <= (now or utc_now())


def _approval_matches(
    approval: SandboxApproval,
    *,
    token: str,
    policy: SandboxPolicy,
    decision: SandboxDecision,
    command: list[str],
) -> bool:
    return (
        (approval.token_hash == approval_token_hash(token) or approval.token == token)
        and approval.policy == policy.name
        and approval.workspace_root == str(policy.workspace_root.resolve())
        and approval.classification == decision.classification
        and approval.command_hash == approval_command_hash(command)
        and not approval_is_expired(approval)
    )


def load_sandbox_approval_store(path: Path | None = None) -> SandboxApprovalStore:
    """Load approvals; missing file means empty store."""
    store_path = path or sandbox_approval_store_path()
    if not store_path.exists():
        return SandboxApprovalStore()
    return SandboxApprovalStore.model_validate(json.loads(store_path.read_text(encoding="utf-8")))


def save_sandbox_approval_store(store: SandboxApprovalStore, path: Path | None = None) -> Path:
    """Persist approvals with stable JSON."""
    store_path = path or sandbox_approval_store_path()
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(store.model_dump_json(indent=2) + "\n", encoding="utf-8")
    try:
        store_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return store_path


def approve_command_token(
    *,
    token: str,
    command: list[str],
    policy: SandboxPolicy,
    path: Path | None = None,
) -> SandboxApproval:
    """Persist scoped approval for a token and command."""
    decision = decide(command, policy)
    approved = approve_decision(decision, reason="approval token")
    if not approved.allowed or not approved.approved:
        raise ValueError(f"classification cannot be approved: {decision.classification.value}")
    store = load_sandbox_approval_store(path)
    approval = SandboxApproval(
        token="",
        token_hash=approval_token_hash(token),
        policy=policy.name,
        workspace_root=str(policy.workspace_root.resolve()),
        classification=decision.classification,
        command_hash=approval_command_hash(command),
        created_at=utc_now(),
        expires_at=utc_now_plus(policy.approval_ttl_seconds),
    )
    store.approvals = [
        item
        for item in store.approvals
        if not _approval_matches(
            item, token=token, policy=policy, decision=decision, command=command
        )
    ]
    store.approvals.append(approval)
    save_sandbox_approval_store(store, path)
    return approval


def revoke_approval_token(token: str, path: Path | None = None) -> dict[str, Any]:
    """Remove all approvals for a token."""
    store = load_sandbox_approval_store(path)
    before = len(store.approvals)
    token_hash = approval_token_hash(token)
    store.approvals = [
        approval
        for approval in store.approvals
        if approval.token != token and approval.token_hash != token_hash
    ]
    save_sandbox_approval_store(store, path)
    return {"revoked": before - len(store.approvals), "remaining": len(store.approvals)}


def prune_expired_approvals(path: Path | None = None) -> dict[str, Any]:
    """Remove all expired approvals from the store."""
    store = load_sandbox_approval_store(path)
    before = len(store.approvals)
    now = utc_now()
    store.approvals = [a for a in store.approvals if not approval_is_expired(a, now)]
    save_sandbox_approval_store(store, path)
    return {"pruned": before - len(store.approvals), "remaining": len(store.approvals)}


def approve_decision_with_token(
    *,
    token: str | None,
    command: list[str],
    policy: SandboxPolicy,
    decision: SandboxDecision,
    path: Path | None = None,
) -> SandboxDecision:
    """Apply matching persisted approval without prompting."""
    if not token or decision.allowed or not decision.approval_required:
        return decision
    store = load_sandbox_approval_store(path)
    if any(
        _approval_matches(item, token=token, policy=policy, decision=decision, command=command)
        for item in store.approvals
    ):
        return approve_decision(decision, reason="approval token")
    return decision


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
    truncated = data[:max_bytes].decode("utf-8", errors="replace")
    # The replacement character may exceed max_bytes when re-encoded;
    # strip it if needed.
    while truncated and len(truncated.encode("utf-8")) > max_bytes:
        truncated = truncated[:-1]
    return truncated, True


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
    audit_id = f"sandbox-{uuid.uuid4().hex}"
    return {
        "audit_id": audit_id,
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


def _duration_ms_from_iso(started_at: str, ended_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, int((end - start).total_seconds() * 1000))


def _normalize_microvm_platform(system_name: str | None = None) -> str:
    os_name = system_name or platform.system()
    if os_name == "Darwin":
        return "macos"
    if os_name == "Linux":
        return "linux"
    if os_name == "Windows":
        return "windows"
    return os_name.lower()


def _default_microvm_provider(platform_name: str) -> str:
    if platform_name == "macos":
        return "lima"
    if platform_name == "linux":
        return "firecracker"
    return "unsupported"


def _microvm_teardown_status(
    teardown_attempted: bool,
    lifecycle_errors: list[str],
) -> str:
    if not teardown_attempted:
        return "skipped"
    if lifecycle_errors:
        return "failed" if any("teardown" in error.lower() for error in lifecycle_errors) else "ok"
    return "ok"


def attach_microvm_audit_contract_fields(
    event: dict[str, Any],
    *,
    microvm_provider: str | None = None,
    platform_name: str | None = None,
    lifecycle: list[str] | None = None,
    lifecycle_errors: list[str] | None = None,
    network_proof_passed: bool = False,
    teardown_attempted: bool = False,
    gate: str = "ARC_MICROVM_EXEC_ENABLED=1",
    public_execution_enabled: bool | None = None,
) -> dict[str, Any]:
    """Add ADR-024 v1 microVM audit fields without removing legacy fields."""
    normalized_platform = _normalize_microvm_platform(platform_name)
    errors = lifecycle_errors or []
    started_at = str(event.get("started_at") or event.get("start_ts") or utc_now())
    ended_at = str(event.get("ended_at") or event.get("end_ts") or started_at)
    lifecycle_value = lifecycle if lifecycle is not None else list(event.get("lifecycle", []))
    if public_execution_enabled is not None:
        event["public_execution_enabled"] = public_execution_enabled
    event.update(
        {
            "event": "sandbox.microvm.run",
            "version": 1,
            "provider": "microvm",
            "microvm_provider": microvm_provider or _default_microvm_provider(normalized_platform),
            "platform": normalized_platform,
            "lifecycle": lifecycle_value,
            "lifecycle_errors": errors,
            "teardown_status": _microvm_teardown_status(teardown_attempted, errors),
            "network_proof_passed": network_proof_passed,
            "start_ts": started_at,
            "end_ts": ended_at,
            "duration_ms": _duration_ms_from_iso(started_at, ended_at),
            "gate": gate,
            "contract_doc": "docs/adr/ADR-024-microvm-public-execution-contract.md",
        }
    )
    return event


def build_microvm_audit_event(
    *,
    command: list[str],
    workspace_root: Path,
    provider_runtime: str,
    instance_name: str,
    lifecycle: list[str],
    network_proof_passed: bool,
    teardown_attempted: bool,
    started_at: str,
    ended_at: str,
    exit_code: int | None,
    stdout_truncated: bool,
    stderr_truncated: bool,
    redaction_applied: bool = False,
    lifecycle_errors: list[str] | None = None,
    gate: str = "ARC_MICROVM_INTEGRATION=1",
    public_execution_enabled: bool = False,
    platform_name: str | None = None,
) -> dict[str, Any]:
    """Build the ADR-024 microVM harness audit event.

    This records internal opt-in harness attempts only; it does not imply that
    public ``MicroVMIsolationProvider.execute()`` is available.
    """
    allowed = exit_code == 0 and network_proof_passed
    audit_id = f"microvm-{uuid.uuid4().hex}"
    event = {
        "audit_id": audit_id,
        "type": "MICROVM_COMMAND" if allowed else "MICROVM_DENIED",
        "command": command,
        "cwd": str(workspace_root),
        "classification": "microvm_harness",
        "decision": {
            "allowed": allowed,
            "classification": "microvm_harness",
            "reason": "network-off proof passed"
            if allowed
            else "microVM harness blocked or failed",
            "policy": "microvm-integration-harness",
            "approval_required": False,
            "approved": False,
        },
        "policy": "microvm-integration-harness",
        "provider": "microvm",
        "runtime": provider_runtime,
        "instance_name": instance_name,
        "allowed": allowed,
        "reason": "network-off proof passed" if allowed else "microVM harness blocked or failed",
        "lifecycle": lifecycle,
        "network_proof_passed": network_proof_passed,
        "strict_network_candidate": provider_runtime == "firecracker",
        "strict_network_proof": "proven" if network_proof_passed else "not_proven",
        "network_interfaces_configured": False if provider_runtime == "firecracker" else None,
        "teardown_attempted": teardown_attempted,
        "started_at": started_at,
        "ended_at": ended_at,
        "exit_code": exit_code,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "redaction_applied": redaction_applied,
        "public_execution_enabled": public_execution_enabled,
    }
    return attach_microvm_audit_contract_fields(
        event,
        microvm_provider=provider_runtime,
        platform_name=platform_name,
        lifecycle=lifecycle,
        lifecycle_errors=lifecycle_errors,
        network_proof_passed=network_proof_passed,
        teardown_attempted=teardown_attempted,
        gate=gate,
        public_execution_enabled=public_execution_enabled,
    )


def _container_daemon_alive(binary: str) -> bool:
    """Return True if the container daemon responds to an info probe."""
    try:
        result = subprocess.run(
            [binary, "info"],
            check=False,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def container_preflight() -> dict[str, Any]:
    """Detect container runtime availability for sandbox doctor."""
    from ..isolation.docker_provider import container_sandbox_enabled

    enabled = container_sandbox_enabled()
    docker_bin = shutil.which("docker")
    podman_bin = shutil.which("podman")
    binary = docker_bin or podman_bin
    runtime = "docker" if docker_bin else "podman" if podman_bin else None
    status = "unavailable"
    if enabled and binary:
        status = "ready" if _container_daemon_alive(binary) else "installed_not_configured"
    elif binary:
        status = "disabled"  # installed but ARC_ENABLE_CONTAINER_SANDBOX not set
    blockers: list[str] = []
    if not binary:
        blockers.append("docker or podman binary missing")
    if not enabled:
        blockers.append("ARC_ENABLE_CONTAINER_SANDBOX=1 not set")
    return {
        "provider": "container",
        "status": status,
        "enabled": enabled,
        "binary": binary,
        "runtime": runtime,
        "blockers": blockers,
    }


def microvm_preflight(system: str | None = None) -> dict[str, Any]:
    """Detect lightweight microVM runtime availability without executing workloads."""
    os_name = system or platform.system()
    if os_name == "Linux":
        firecracker = shutil.which("firecracker")
        cloud_hypervisor = shutil.which("cloud-hypervisor")
        binary = firecracker or cloud_hypervisor
        jailer = shutil.which("jailer")
        kvm = Path("/dev/kvm")
        kvm_exists = kvm.exists()
        kvm_rw = os.access(kvm, os.R_OK | os.W_OK) if kvm_exists else False
        machine = platform.machine().lower()
        arch_supported = machine in {"x86_64", "amd64", "aarch64", "arm64"}
        kernel_cache = os.environ.get("ARC_FIRECRACKER_KERNEL")
        rootfs_cache = os.environ.get("ARC_FIRECRACKER_ROOTFS")
        ch_kernel_cache = os.environ.get("ARC_CLOUDHYPERVISOR_KERNEL")
        ch_disk_cache = os.environ.get("ARC_CLOUDHYPERVISOR_DISK")
        kernel_exists = bool(kernel_cache and Path(kernel_cache).exists())
        rootfs_exists = bool(rootfs_cache and Path(rootfs_cache).exists())
        ch_kernel_exists = bool(ch_kernel_cache and Path(ch_kernel_cache).exists())
        ch_disk_exists = bool(ch_disk_cache and Path(ch_disk_cache).exists())
        firecracker_cache_ready = bool(kernel_exists and rootfs_exists)
        cloud_hypervisor_cache_ready = bool(ch_kernel_exists and ch_disk_exists)
        cache_ready = firecracker_cache_ready or cloud_hypervisor_cache_ready

        # Deep diagnostics
        if firecracker:
            version_result = _run_probe([firecracker, "--version"])
            jail_version_result = _run_probe([jailer, "--version"]) if jailer else None
        else:
            version_result = None
            jail_version_result = None

        # Kernel metadata validation
        kernel_size = None
        if kernel_cache:
            stats = os.stat(kernel_cache)
            kernel_size = stats.st_size

        # Jail permission validation
        jail_perms = None
        if jailer:
            try:
                jail_perms = oct(os.stat(jailer).st_mode)
            except Exception:
                jail_perms = None

        firecracker_ready = bool(
            firecracker
            and jailer
            and kvm_exists
            and kvm_rw
            and arch_supported
            and firecracker_cache_ready
        )
        cloud_hypervisor_ready = bool(
            cloud_hypervisor
            and kvm_exists
            and kvm_rw
            and arch_supported
            and cloud_hypervisor_cache_ready
        )
        ready = firecracker_ready or cloud_hypervisor_ready
        status = "ready" if ready else "installed_not_configured" if binary else "unavailable"
        blockers: list[str] = []
        if not binary:
            blockers.append("firecracker or cloud-hypervisor binary missing")
        if not kvm_exists:
            blockers.append("/dev/kvm missing")
        elif not kvm_rw:
            blockers.append("/dev/kvm is not read/write accessible")
        if not arch_supported:
            blockers.append(f"unsupported architecture: {machine}")
        if firecracker and not jailer:
            blockers.append("jailer missing for Firecracker proof path")
        if firecracker and not firecracker_cache_ready:
            blockers.append("ARC_FIRECRACKER_KERNEL or ARC_FIRECRACKER_ROOTFS missing/unreadable")
        if cloud_hypervisor and not cloud_hypervisor_cache_ready:
            blockers.append(
                "ARC_CLOUDHYPERVISOR_KERNEL or ARC_CLOUDHYPERVISOR_DISK missing/unreadable"
            )
        return {
            "provider": "microvm",
            "platform": "linux",
            "status": status,
            "runtime_preflight_status": status,
            "public_execution_enabled": False,
            "public_execution_status": "blocked",
            "contract_doc": "docs/adr/ADR-024-microvm-public-execution-contract.md",
            "strict_network_candidate": bool(firecracker),
            "firecracker_strict_candidate": bool(firecracker),
            "cloud_hypervisor_strict_candidate": bool(cloud_hypervisor),
            "strict_network_proof": "not_proven",
            "network_interfaces_configured": False,
            "binary": binary,
            "firecracker": firecracker,
            "cloud_hypervisor": cloud_hypervisor,
            "jailer": jailer,
            "jailer_required_for_firecracker": bool(firecracker),
            "kvm": kvm_exists,
            "kvm_rw": kvm_rw,
            "machine": machine,
            "arch_supported": arch_supported,
            "kernel_cache": kernel_cache,
            "kernel_exists": kernel_exists,
            "rootfs_cache": rootfs_cache,
            "rootfs_exists": rootfs_exists,
            "cache_ready": cache_ready,
            "firecracker_cache_ready": firecracker_cache_ready,
            "cloud_hypervisor_cache_ready": cloud_hypervisor_cache_ready,
            "cloud_hypervisor_kernel": ch_kernel_cache,
            "cloud_hypervisor_kernel_exists": ch_kernel_exists,
            "cloud_hypervisor_disk": ch_disk_cache,
            "cloud_hypervisor_disk_exists": ch_disk_exists,
            "blockers": blockers,
            "version": version_result,
            "jailer_version": jail_version_result,
            "kernel_size": kernel_size,
            "jail_perms": jail_perms,
        }
    if os_name == "Darwin":
        limactl = shutil.which("limactl")
        macos_version = platform.mac_ver()[0]
        limactl_version = _run_probe([limactl, "--version"]) if limactl else None
        limactl_list = _run_probe([limactl, "list", "--json"]) if limactl else None
        status = "installed_not_configured" if limactl else "unavailable"
        p2_blockers = [
            "Lima default user-mode/slirp network is present by design",
            "No documented Lima/VZ network-none template key found",
            "Guest-level route/firewall denial would not satisfy ADR-024 strict P2",
        ]
        return {
            "provider": "microvm",
            "platform": "macos",
            "status": status,
            "runtime_preflight_status": status,
            "public_execution_enabled": False,
            "public_execution_status": "blocked",
            "contract_doc": "docs/adr/ADR-024-microvm-public-execution-contract.md",
            "binary": limactl,
            "runtime": "lima-vz",
            "strict_network_isolation": False,
            "strict_no_network_proof": "blocked",
            "p2_status": "blocked",
            "p2_blockers": p2_blockers,
            "security_posture": "low_security_network_present",
            "network_reason": "Lima default/user-v2 networking provides guest network access",
            "guest_network_default": "present_by_lima_slirp",
            "workspace_mount_strategy": "lima-vz-virtiofs-workspace-only",
            "mount_escape_proof": "host_gated_only",
            "template_hardening": [
                "vmType=vz",
                "mountType=virtiofs",
                "workspace-only /workspace mount",
                "containerd disabled",
                "hostResolver disabled",
                "proxy env propagation disabled",
                "SSH agent/key forwarding disabled",
                "no additional named networks or port forwards",
            ],
            "macos_version": macos_version,
            "limactl_version": limactl_version,
            "limactl_list": limactl_list,
            "execution": "not_implemented",
        }
    return {
        "provider": "microvm",
        "platform": os_name.lower(),
        "status": "blocked",
        "runtime_preflight_status": "blocked",
        "public_execution_enabled": False,
        "public_execution_status": "blocked",
        "contract_doc": "docs/adr/ADR-024-microvm-public-execution-contract.md",
        "reason": "Windows/unsupported platform skipped",
    }


def _run_probe(argv: list[str | None]) -> dict[str, Any]:
    """Run bounded runtime probe; never creates VMs."""
    if not argv[0]:
        return {"ok": False, "error": "missing binary"}
    try:
        result = subprocess.run(
            [str(part) for part in argv],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001 - probe errors must be reported, not raised.
        return {"ok": False, "error": str(exc)}
    stdout, stdout_truncated = cap_output(result.stdout, 4096)
    stderr, stderr_truncated = cap_output(result.stderr, 4096)
    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }


def firecracker_doctor(system: str | None = None) -> dict[str, Any]:
    """Expanded Firecracker preflight — checks binary, KVM, jailer, kernel/rootfs cache.

    Returns a stable dict that can be emitted as JSON.  Never creates VMs.
    """
    os_name = system or platform.system()
    if os_name != "Linux":
        return {
            "provider": "firecracker",
            "platform": os_name.lower(),
            "status": "blocked",
            "reason": f"Firecracker requires Linux; platform={os_name}",
            "binary": None,
            "kvm": False,
            "jailer": None,
            "cache_ready": False,
        }

    firecracker = shutil.which("firecracker")
    cloud_hypervisor = shutil.which("cloud-hypervisor")
    binary = firecracker or cloud_hypervisor
    jailer = shutil.which("jailer")

    kvm_path = Path("/dev/kvm")
    kvm_exists = kvm_path.exists()
    kvm_rw = os.access(kvm_path, os.R_OK | os.W_OK) if kvm_exists else False

    kernel_env = os.environ.get("ARC_FIRECRACKER_KERNEL")
    rootfs_env = os.environ.get("ARC_FIRECRACKER_ROOTFS")
    ch_kernel_env = os.environ.get("ARC_CLOUDHYPERVISOR_KERNEL")
    ch_disk_env = os.environ.get("ARC_CLOUDHYPERVISOR_DISK")

    # Default cache paths if env vars not set
    default_cache = Path.home() / ".cache" / "arc" / "microvm"
    kernel_path = Path(kernel_env) if kernel_env else default_cache / "vmlinux"
    rootfs_path = Path(rootfs_env) if rootfs_env else default_cache / "rootfs.ext4"

    kernel_exists = kernel_path.exists()
    rootfs_exists = rootfs_path.exists()
    ch_kernel_path = (
        Path(ch_kernel_env) if ch_kernel_env else default_cache / "cloud-hypervisor-vmlinux"
    )
    ch_disk_path = Path(ch_disk_env) if ch_disk_env else default_cache / "cloud-hypervisor-disk.raw"
    ch_kernel_exists = ch_kernel_path.exists()
    ch_disk_exists = ch_disk_path.exists()
    firecracker_cache_ready = kernel_exists and rootfs_exists
    cloud_hypervisor_cache_ready = ch_kernel_exists and ch_disk_exists
    cache_ready = firecracker_cache_ready or cloud_hypervisor_cache_ready

    # Jailer optional — note absence but don't block installed_not_configured
    jailer_present = bool(jailer)
    jailer_perms: str | None = None
    if jailer:
        try:
            jailer_perms = oct(os.stat(jailer).st_mode)
        except Exception:
            jailer_perms = None

    # Kernel size (diagnostic only)
    kernel_size: int | None = None
    if kernel_exists:
        try:
            kernel_size = kernel_path.stat().st_size
        except Exception:
            pass

    ready = bool(binary and kvm_exists and kvm_rw and cache_ready)
    if ready:
        status = "ready"
    elif binary:
        status = "installed_not_configured"
    else:
        status = "unavailable"

    return {
        "provider": "firecracker",
        "platform": "linux",
        "status": status,
        "strict_network_candidate": bool(firecracker),
        "strict_network_proof": "not_proven",
        "network_interfaces_configured": False,
        "binary": binary,
        "firecracker": firecracker,
        "cloud_hypervisor": cloud_hypervisor,
        "jailer": jailer,
        "jailer_present": jailer_present,
        "jailer_perms": jailer_perms,
        "kvm": kvm_exists,
        "kvm_rw": kvm_rw,
        "kernel_path": str(kernel_path),
        "kernel_exists": kernel_exists,
        "kernel_size": kernel_size,
        "rootfs_path": str(rootfs_path),
        "rootfs_exists": rootfs_exists,
        "cache_ready": cache_ready,
        "firecracker_cache_ready": firecracker_cache_ready,
        "cloud_hypervisor_cache_ready": cloud_hypervisor_cache_ready,
        "cloud_hypervisor_kernel_path": str(ch_kernel_path),
        "cloud_hypervisor_kernel_exists": ch_kernel_exists,
        "cloud_hypervisor_disk_path": str(ch_disk_path),
        "cloud_hypervisor_disk_exists": ch_disk_exists,
    }


def is_path_within_root(path: Path, root: Path) -> bool:
    """Return True iff ``path`` resolves to a location inside ``root``.

    Uses ``os.path.realpath()`` to follow all symlinks before comparing,
    preventing symlink escape attacks where a symlink inside the workspace
    points to a path outside it.

    Works for non-existent paths and dangling symlinks: ``realpath()`` with
    strict=False resolves as far as possible without raising.

    Args:
        path: Candidate path to check.
        root: Root directory the path must be inside (inclusive).

    Returns:
        True if the fully resolved ``path`` starts with the fully resolved
        ``root`` path.  False otherwise.
    """
    real_root = os.path.realpath(root)
    real_path = os.path.realpath(path)
    # Ensure we compare with a trailing separator to avoid prefix collisions
    # e.g. /workspace-evil vs /workspace
    root_str = real_root.rstrip(os.sep) + os.sep
    path_str = real_path.rstrip(os.sep) + os.sep
    # Allow exact equality (path == root) or containment (path starts with root/)
    return path_str == root_str or path_str.startswith(root_str)


def check_workspace_escape(candidate: Path, workspace_root: Path) -> None:
    """Raise ``ValueError`` if ``candidate`` resolves outside ``workspace_root``.

    Used by sandbox harnesses before running any command that references a path,
    and by mount isolation checks before writing templates or starting VMs.

    Args:
        candidate: Path to validate.
        workspace_root: The workspace boundary.

    Raises:
        ValueError: If the resolved ``candidate`` is outside ``workspace_root``.
    """
    if not is_path_within_root(candidate, workspace_root):
        real = os.path.realpath(candidate)
        real_root = os.path.realpath(workspace_root)
        raise ValueError(
            f"Path escape detected: {candidate!r} resolves to {real!r} "
            f"which is outside workspace root {real_root!r}"
        )


def stable_json(data: Any) -> str:
    """Dump stable JSON for docs/tests."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def sandbox_policy_store_path() -> Path:
    """Return the sandbox policy config path."""
    override = os.environ.get("ARC_SANDBOX_POLICY_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arc" / "sandbox-policies.json"


def default_workspace_policy_path(workspace_root: Path) -> Path:
    """Return .arc/sandbox-policy.yaml inside workspace."""
    return workspace_root / ".arc" / "sandbox-policy.yaml"


def default_user_sandbox_policy_path() -> Path:
    """Return ~/.arc/sandbox-policy.yaml (user-level sandbox policy)."""
    return Path.home() / ".arc" / "sandbox-policy.yaml"


def load_sandbox_policy_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML sandbox policy file. Returns raw dict."""
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Policy YAML must be a mapping")
    return raw


def validate_sandbox_policy_yaml(path: Path) -> dict[str, Any]:
    """Validate a YAML sandbox policy file and return a stable report.

    Returns {"ok": bool, "path": str, "policy_name": str|None, "errors": list}
    """
    errors: list[str] = []
    try:
        raw = load_sandbox_policy_yaml(path)
    except FileNotFoundError as exc:
        return {"ok": False, "path": str(path), "policy_name": None, "errors": [str(exc)]}
    except Exception as exc:
        return {"ok": False, "path": str(path), "policy_name": None, "errors": [str(exc)]}

    if "name" not in raw:
        errors.append("missing required field: name")
    if "version" not in raw:
        errors.append("missing required field: version")
    elif raw["version"] != 1:
        errors.append("version must be 1")

    allowed = set(SandboxPolicy.model_fields) - {"workspace_root"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        errors.append(f"unknown fields: {', '.join(unknown)}")

    # Validate boolean fields
    bool_fields = ["allow_network", "allow_install", "allow_privileged", "allow_unknown"]
    for field in bool_fields:
        if field in raw and not isinstance(raw[field], bool):
            errors.append(f"{field} must be a boolean")

    if not errors:
        try:
            SandboxPolicy.model_validate({**raw, "workspace_root": Path.cwd()})
        except Exception as exc:
            errors.append(str(exc))

    return {
        "ok": not errors,
        "path": str(path),
        "policy_name": raw.get("name"),
        "errors": errors,
    }


def apply_sandbox_policy_yaml(
    source_path: Path,
    workspace_root: Path,
    *,
    target_path: Path | None = None,
) -> dict[str, Any]:
    """Validate and install a YAML policy file into workspace .arc/sandbox-policy.yaml.

    Returns {"ok": bool, "source": str, "target": str, "policy_name": str|None, "errors": list}
    """
    validation = validate_sandbox_policy_yaml(source_path)
    if not validation["ok"]:
        return {
            "ok": False,
            "source": str(source_path),
            "target": None,
            "policy_name": validation["policy_name"],
            "errors": validation["errors"],
        }
    root = workspace_root.expanduser().resolve()
    raw_dest = target_path or default_workspace_policy_path(root)
    dest = raw_dest.expanduser()
    if not dest.is_absolute():
        dest = root / dest
    dest = dest.resolve(strict=False)
    try:
        check_workspace_escape(dest, root)
    except ValueError as exc:
        return {
            "ok": False,
            "source": str(source_path),
            "target": str(dest),
            "policy_name": validation["policy_name"],
            "errors": [str(exc)],
        }
    dest.parent.mkdir(parents=True, exist_ok=True)
    import shutil as _shutil

    _shutil.copy2(str(source_path), str(dest))
    return {
        "ok": True,
        "source": str(source_path),
        "target": str(dest),
        "policy_name": validation["policy_name"],
        "errors": [],
    }


def resolve_sandbox_policy_with_yaml(
    name: str,
    workspace_root: Path,
    *,
    json_path: Path | None = None,
    yaml_path: Path | None = None,
) -> SandboxPolicy:
    """Resolve a sandbox policy with YAML-first lookup.

    Priority: JSON store (existing) → workspace YAML file → user YAML file → built-in.
    """
    if name == "local-safe":
        return SandboxPolicy(name=name, workspace_root=workspace_root)
    store_path = json_path or sandbox_policy_store_path()
    if store_path.exists():
        raw = json.loads(store_path.read_text(encoding="utf-8"))
        _validate_policy_config_shape(raw)
        for item in raw.get("policies", []):
            if item.get("name") == name:
                return SandboxPolicy.model_validate({**item, "workspace_root": workspace_root})

    # Try workspace YAML
    ws_yaml = yaml_path or default_workspace_policy_path(workspace_root)
    if ws_yaml.exists():
        try:
            raw = load_sandbox_policy_yaml(ws_yaml)
            if raw.get("name") == name:
                return SandboxPolicy.model_validate({**raw, "workspace_root": workspace_root})
        except Exception:
            pass

    # Try user YAML
    user_yaml = default_user_sandbox_policy_path()
    if user_yaml.exists():
        try:
            raw = load_sandbox_policy_yaml(user_yaml)
            if raw.get("name") == name:
                return SandboxPolicy.model_validate({**raw, "workspace_root": workspace_root})
        except Exception:
            pass

    raise KeyError(f"Sandbox policy not found: {name}")


def _try_yaml_policy(name: str, workspace_root: Path) -> SandboxPolicy | None:
    """Try workspace then user YAML files for a policy; return None if not found."""
    for yaml_path in (
        default_workspace_policy_path(workspace_root),
        default_user_sandbox_policy_path(),
    ):
        if not yaml_path.exists():
            continue
        try:
            raw = load_sandbox_policy_yaml(yaml_path)
            if raw.get("name") == name:
                return SandboxPolicy.model_validate({**raw, "workspace_root": workspace_root})
        except Exception:
            pass
    return None


def resolve_sandbox_policy(
    name: str, workspace_root: Path, path: Path | None = None
) -> SandboxPolicy:
    """Resolve a built-in or JSON-configured sandbox policy.

    Lookup order: built-in → JSON store → workspace YAML → user YAML.
    """
    if name == "local-safe":
        return SandboxPolicy(name=name, workspace_root=workspace_root)
    store_path = path or sandbox_policy_store_path()
    if store_path.exists():
        raw = json.loads(store_path.read_text(encoding="utf-8"))
        _validate_policy_config_shape(raw)
        for item in raw.get("policies", []):
            if item.get("name") == name:
                payload = {**item, "workspace_root": workspace_root}
                return SandboxPolicy.model_validate(payload)
    # Fall through to YAML files
    found = _try_yaml_policy(name, workspace_root)
    if found is not None:
        return found
    raise KeyError(f"Sandbox policy not found: {name}")


def list_sandbox_policies(workspace_root: Path, path: Path | None = None) -> list[SandboxPolicy]:
    """List built-in and configured sandbox policies."""
    policies = [SandboxPolicy(name="local-safe", workspace_root=workspace_root)]
    store_path = path or sandbox_policy_store_path()
    if store_path.exists():
        raw = json.loads(store_path.read_text(encoding="utf-8"))
        _validate_policy_config_shape(raw)
        for item in raw.get("policies", []):
            payload = {**item, "workspace_root": workspace_root}
            policies.append(SandboxPolicy.model_validate(payload))
    names = {policy.name for policy in policies}
    for yaml_path in (
        default_workspace_policy_path(workspace_root),
        default_user_sandbox_policy_path(),
    ):
        if not yaml_path.exists():
            continue
        raw_yaml = load_sandbox_policy_yaml(yaml_path)
        policy = SandboxPolicy.model_validate({**raw_yaml, "workspace_root": workspace_root})
        if policy.name not in names:
            policies.append(policy)
            names.add(policy.name)
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
    _persist_hmac_sandbox_event(event, target_dir)
    _persist_local_event_log_sandbox_event(event)
    return chain_path


def _persist_local_event_log_sandbox_event(event: dict[str, Any]) -> None:
    """Best-effort mirror into the local/recent ARC event log."""
    try:
        from ..events.persistence import get_writer
        from ..events.types import ArcEvent

        get_writer().write(
            ArcEvent(
                event_type="sandbox_command",
                payload={
                    "audit_id": event.get("audit_id"),
                    "sandbox_type": event.get("type"),
                    "command": event.get("command", []),
                    "cwd": event.get("cwd"),
                    "classification": event.get("classification"),
                    "decision": event.get("decision", {}),
                    "policy": event.get("policy"),
                    "provider": event.get("provider"),
                    "runtime": event.get("runtime"),
                    "allowed": event.get("allowed"),
                    "reason": event.get("reason"),
                    "started_at": event.get("started_at"),
                    "ended_at": event.get("ended_at"),
                    "exit_code": event.get("exit_code"),
                    "stdout_truncated": event.get("stdout_truncated", False),
                    "stderr_truncated": event.get("stderr_truncated", False),
                    "redaction_applied": event.get("redaction_applied", False),
                },
            )
        )
    except Exception:
        return


def _persist_hmac_sandbox_event(event: dict[str, Any], audit_dir: Path) -> None:
    """Best-effort HMAC mirror; skipped when no audit key exists."""
    try:
        from ..audit.schema import SandboxCommandEvent
        from ..audit.storage import AuditChainStore

        store = AuditChainStore(audit_dir=audit_dir)
        hmac_event = SandboxCommandEvent(
            run_id="sandbox",
            session_id="sandbox-cli",
            payload=event,
        )
        store.append_event(hmac_event)
    except Exception:
        return


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
    try:
        ok, reason = verify(chain_path, events_path)
    except Exception as exc:
        return {
            "ok": False,
            "chain": str(chain_path),
            "events": str(events_path),
            "reason": f"malformed sandbox audit log: {exc}",
        }
    return {"ok": ok, "chain": str(chain_path), "events": str(events_path), "reason": reason}


def list_sandbox_audit_events(
    audit_dir: Path | None = None,
    *,
    allowed: bool | None = None,
    classification: str | None = None,
    provider: str | None = None,
    command_contains: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List sandbox audit events with simple filters."""
    target_dir = audit_dir or sandbox_audit_dir()
    events_path = target_dir / "sandbox.events.jsonl"
    if not events_path.exists():
        return _sandbox_audit_list_result([], events_path, malformed=0)
    events: list[dict[str, Any]] = []
    malformed = 0
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
        else:
            malformed += 1
    if allowed is not None:
        events = [event for event in events if event.get("allowed") is allowed]
    if classification:
        events = [event for event in events if event.get("classification") == classification]
    if provider:
        events = [event for event in events if event.get("provider") == provider]
    if command_contains:
        events = [event for event in events if command_contains in _audit_command_text(event)]
    if since:
        events = [event for event in events if str(event.get("started_at", "")) >= since]
    if until:
        events = [event for event in events if str(event.get("started_at", "")) <= until]
    if limit == 0:
        events = []
    elif limit > 0:
        events = events[-limit:]
    return _sandbox_audit_list_result(events, events_path, malformed=malformed)


def _audit_command_text(event: dict[str, Any]) -> str:
    command = event.get("command", [])
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    return str(command)


def _sandbox_audit_list_result(
    events: list[dict[str, Any]], events_path: Path, *, malformed: int
) -> dict[str, Any]:
    return {
        "events": events,
        "path": str(events_path),
        "count": len(events),
        "source": "local_sandbox_audit",
        "summary_semantics": "local_recent_derived_not_global",
        "degraded": malformed > 0,
        "malformed": malformed,
    }


def get_sandbox_audit_event(audit_id: str, audit_dir: Path | None = None) -> dict[str, Any]:
    """Return a single sandbox audit event by ID."""
    result = list_sandbox_audit_events(audit_dir, limit=-1)
    for event in result["events"]:
        if event.get("audit_id") == audit_id:
            return {"event": event, "path": result["path"], "found": True}
    return {"event": None, "path": result["path"], "found": False}


def parse_relative_time(value: str, *, strict: bool = False) -> str:
    """Convert a relative time string to an ISO UTC string.

    Accepts:
    - ``Nh`` — N hours ago
    - ``Nm`` — N minutes ago
    - ``Nd`` — N days ago
    - ``now`` — current UTC time
    - Any other string is returned unchanged unless ``strict=True``.
    """
    value = value.strip()
    if value == "now":
        return utc_now()
    import re

    m = re.fullmatch(r"(\d+)([hmd])", value)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit == "h":
            delta = timedelta(hours=n)
        elif unit == "m":
            delta = timedelta(minutes=n)
        else:  # d
            delta = timedelta(days=n)
        return (datetime.now(timezone.utc) - delta).isoformat().replace("+00:00", "Z")
    if strict:
        _parse_iso_time(value)
    return value


def _parse_iso_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def compact_sandbox_audit_events(
    *,
    before: str | None = None,
    keep: int = 1000,
    audit_dir: Path | None = None,
) -> dict[str, Any]:
    """Prune sandbox audit events from ``sandbox.events.jsonl``.

    Two modes:
    - ``before`` supplied: remove events whose ``started_at`` < ``before``.
    - ``before`` omitted: keep the newest ``keep`` events.

    The chain file (``sandbox.audit.jsonl``) is never modified.

    Returns ``{"compacted": N, "remaining": M, "events_path": str}``.
    """
    target_dir = audit_dir or sandbox_audit_dir()
    events_path = target_dir / "sandbox.events.jsonl"
    if not events_path.exists():
        return {"ok": True, "compacted": 0, "remaining": 0, "events_path": str(events_path)}
    if keep < 0:
        raise ValueError("keep must be >= 0")
    if before is not None:
        before = parse_relative_time(before, strict=True)

    chain_path = target_dir / "sandbox.audit.jsonl"
    if chain_path.exists():
        return {
            "ok": False,
            "compacted": 0,
            "remaining": len(
                [
                    line
                    for line in events_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            ),
            "events_path": str(events_path),
            "reason": "refusing to compact canonical events while sandbox.audit.jsonl exists",
        }

    raw_lines = [
        line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    total = len(raw_lines)

    malformed = sum(1 for line in raw_lines if _event_started_at(line) is None)
    if malformed:
        return {
            "ok": False,
            "compacted": 0,
            "remaining": total,
            "events_path": str(events_path),
            "malformed": malformed,
            "reason": "refusing to compact malformed sandbox events",
        }

    if before is not None:
        kept_lines = [line for line in raw_lines if _event_started_at(line) >= before]
    elif keep == 0:
        kept_lines = []
    else:
        kept_lines = raw_lines[-keep:]

    compacted = total - len(kept_lines)
    tmp_path = events_path.with_suffix(events_path.suffix + ".tmp")
    tmp_path.write_text("".join(line + "\n" for line in kept_lines), encoding="utf-8")
    tmp_path.replace(events_path)
    return {
        "ok": True,
        "compacted": compacted,
        "remaining": len(kept_lines),
        "events_path": str(events_path),
    }


def _event_started_at(line: str) -> str | None:
    """Extract ``started_at`` from a raw event JSON line for compaction comparisons."""
    try:
        parsed = json.loads(line)
        return str(parsed.get("started_at", ""))
    except Exception:
        return None


def render_lima_template(workspace_root: Path, instance_name: str = "arc-sandbox") -> str:
    """Render an experimental Lima VZ template; gated by caller.

    Lima is a low-security harness for ARC until a real no-network template is
    found. `networks: []` does not prove absence of Lima's default user-mode
    network, so the harness still performs an in-guest route proof before argv.
    """
    workspace = str(workspace_root.resolve())
    return f"""# ARC experimental Lima VM template. Low-security harness only; strict network isolation is not proven.
# Internal Lima harness gated by ARC_MICROVM_INTEGRATION=1; public microVM execution remains blocked.
vmType: vz
mountType: virtiofs
cpus: 2
memory: 2GiB
disk: 20GiB
images:
  - location: https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-$(arch).img
mounts:
  - location: {workspace}
    mountPoint: /workspace
    writable: true
networks: [] # Does not prove no default Lima user-mode/slirp route.
portForwards: []
hostResolver:
  enabled: false # DNS hardening only; not a strict no-network proof.
propagateProxyEnv: false
containerd:
  system: false
  user: false
ssh:
  loadDotSSHPubKeys: false
  forwardAgent: false
  forwardX11: false
  forwardX11Trusted: false
provision:
  - mode: system
    script: |
      set -eu
      mkdir -p /workspace
message: "ARC experimental instance {instance_name}; network must be proven disabled before execution."
"""
