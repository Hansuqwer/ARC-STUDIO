"""Read-only slash-command adapters for the interactive CLI."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..isolation.microvm import MicroVMIsolationProvider
from ..isolation.subprocess import SubprocessIsolationProvider
from ..runtime.mode import RuntimeMode
from ..security.sandbox import (
    SandboxResult,
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    list_sandbox_audit_events,
    list_sandbox_policies,
    persist_sandbox_audit_event,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
    verify_sandbox_audit,
)

READ_MAX_BYTES = 64_000
READ_DEFAULT_LIMIT = 200
SEARCH_MAX_FILE_BYTES = 256_000
SEARCH_MAX_FILES = 500
SEARCH_MAX_MATCHES = 50
SEARCH_MAX_LINE_CHARS = 240
SEARCH_SKIP_DIRS = {
    ".arc",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "lib",
    "node_modules",
}


@dataclass(frozen=True)
class SlashAdapterResult:
    """Structured adapter result rendered by the REPL."""

    state: str
    text: str
    data: dict[str, Any] = field(default_factory=dict)
    exit_code: int = 0


def _workspace(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()).resolve()


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _workspace_path(value: str, workspace: Path) -> Path:
    if not value:
        raise ValueError("missing path")
    raw = Path(value).expanduser()
    candidate = raw if raw.is_absolute() else workspace / raw
    resolved = candidate.resolve(strict=False)
    if candidate.exists() and candidate.is_symlink():
        raise ValueError(f"path is a symlink: {value}")
    if not resolved.is_relative_to(workspace):
        raise ValueError(f"path escapes workspace: {value}")
    return resolved


def _is_text_sample(data: bytes) -> bool:
    return b"\x00" not in data


def _parse_read_args(arg: str) -> tuple[str, int, int]:
    parts = shlex.split(arg)
    offset = 1
    limit = READ_DEFAULT_LIMIT
    path = ""
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--offset" and index + 1 < len(parts):
            offset = int(parts[index + 1])
            index += 2
            continue
        if part == "--limit" and index + 1 < len(parts):
            limit = int(parts[index + 1])
            index += 2
            continue
        if not path:
            path = part
            index += 1
            continue
        raise ValueError("Usage: /read [--offset N] [--limit N] <path>")
    if offset < 1 or limit < 1:
        raise ValueError("offset and limit must be positive")
    return path, offset, min(limit, READ_DEFAULT_LIMIT)


def render_read(arg: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        path_arg, offset, limit = _parse_read_args(arg)
        path = _workspace_path(path_arg, ws)
    except (OSError, ValueError) as exc:
        return SlashAdapterResult(state="blocked", text=f"Blocked: {exc}", exit_code=2)
    if not path.exists():
        return SlashAdapterResult(state="absent", text=f"File not found: {path_arg}", exit_code=2)
    if not path.is_file():
        return SlashAdapterResult(
            state="blocked", text=f"Blocked: not a file: {path_arg}", exit_code=2
        )
    data = path.read_bytes()[: READ_MAX_BYTES + 1]
    if not _is_text_sample(data):
        return SlashAdapterResult(
            state="blocked", text=f"Blocked: binary file: {path_arg}", exit_code=2
        )
    truncated = len(data) > READ_MAX_BYTES
    text = data[:READ_MAX_BYTES].decode("utf-8", errors="replace")
    lines = text.splitlines()
    start = offset - 1
    selected = lines[start : start + limit]
    output = "\n".join(f"{start + index + 1}: {line}" for index, line in enumerate(selected))
    if not output:
        output = f"No lines at offset {offset}."
    if truncated:
        output += "\n[truncated]"
    return SlashAdapterResult(
        state="degraded" if truncated else "present",
        text=output,
        data={
            "path": str(path),
            "offset": offset,
            "limit": limit,
            "lines_returned": len(selected),
            "truncated": truncated,
        },
    )


def _parse_search_args(arg: str) -> tuple[str, str, str]:
    parts = shlex.split(arg)
    pattern = ""
    include = "*"
    path = "."
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--include" and index + 1 < len(parts):
            include = parts[index + 1]
            index += 2
            continue
        if part == "--path" and index + 1 < len(parts):
            path = parts[index + 1]
            index += 2
            continue
        if not pattern:
            pattern = part
            index += 1
            continue
        raise ValueError('Usage: /search <regex> [--include "*.py"] [--path subdir]')
    if not pattern:
        raise ValueError('Usage: /search <regex> [--include "*.py"] [--path subdir]')
    return pattern, include, path


def _iter_search_files(root: Path, include: str) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob(include):
        if len(files) >= SEARCH_MAX_FILES:
            break
        if any(part in SEARCH_SKIP_DIRS for part in path.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        files.append(path)
    return files


def render_search(arg: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        pattern, include, path_arg = _parse_search_args(arg)
        root = _workspace_path(path_arg, ws)
        regex = re.compile(pattern)
    except (OSError, re.error, ValueError) as exc:
        return SlashAdapterResult(state="blocked", text=f"Blocked: {exc}", exit_code=2)
    if not root.exists():
        return SlashAdapterResult(
            state="absent", text=f"Search path not found: {path_arg}", exit_code=2
        )
    if root.is_file():
        candidates = [root]
    elif root.is_dir():
        candidates = _iter_search_files(root, include)
    else:
        return SlashAdapterResult(
            state="blocked", text=f"Blocked: not searchable: {path_arg}", exit_code=2
        )

    matches: list[dict[str, Any]] = []
    truncated = False
    files_scanned = 0
    for file_path in candidates:
        if len(matches) >= SEARCH_MAX_MATCHES:
            truncated = True
            break
        try:
            data = file_path.read_bytes()[: SEARCH_MAX_FILE_BYTES + 1]
        except OSError:
            continue
        if len(data) > SEARCH_MAX_FILE_BYTES:
            truncated = True
        if not _is_text_sample(data):
            continue
        files_scanned += 1
        text = data[:SEARCH_MAX_FILE_BYTES].decode("utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(
                    {
                        "path": str(file_path.relative_to(ws)),
                        "line": line_number,
                        "text": line[:SEARCH_MAX_LINE_CHARS],
                    }
                )
                if len(matches) >= SEARCH_MAX_MATCHES:
                    truncated = True
                    break

    if not matches:
        return SlashAdapterResult(
            state="absent",
            text="No matches.",
            data={"matches": [], "files_scanned": files_scanned, "truncated": truncated},
        )
    lines = ["Search matches:"]
    for item in matches:
        lines.append(f"  {item['path']}:{item['line']}: {item['text']}")
    if truncated:
        lines.append("[truncated]")
    return SlashAdapterResult(
        state="degraded" if truncated else "present",
        text="\n".join(lines),
        data={"matches": matches, "files_scanned": files_scanned, "truncated": truncated},
    )


def render_status(session: Any, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    traces = ws / ".arc" / "traces"
    run_count = len(list(traces.glob("*.jsonl"))) if traces.exists() else 0
    runtime = RuntimeMode.from_legacy(getattr(session, "runtime_mode", "fake")).value
    lines = [
        f"Workspace: {ws}",
        f"Mode: {getattr(session, 'mode', 'build').upper()}",
        f"Runtime: {runtime}",
        f"Profile: {getattr(session, 'profile_id', 'default')}",
        f"Isolation: {getattr(session, 'isolation_id', 'none')}",
        f"Session: {getattr(session, 'id', 'unknown')[:12]}",
        f"Messages: {len(getattr(session, 'history', []))}",
        f"Stored runs: {run_count}",
    ]
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"workspace": str(ws), "runtime": runtime, "stored_runs": run_count},
    )


def render_doctor_summary(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    subprocess_provider = SubprocessIsolationProvider().describe()
    microvm_provider = MicroVMIsolationProvider().describe()
    checks = [
        ("Workspace exists", ws.exists()),
        ("ARC dir exists", (ws / ".arc").exists()),
        ("Subprocess sandbox", bool(subprocess_provider.get("available", True))),
        ("MicroVM execution", bool(microvm_provider.get("available", False))),
    ]
    lines = ["Doctor:"]
    for label, ok in checks:
        glyph = "✓" if ok else "✗"
        lines.append(f"  {glyph} {label}")
    lines.append(f"MicroVM status: {microvm_provider.get('reason', 'preflight_only')}")
    return SlashAdapterResult(
        state="present" if ws.exists() else "degraded",
        text="\n".join(lines),
        data={"workspace": str(ws), "providers": [subprocess_provider, microvm_provider]},
    )


def render_sandbox_doctor(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    providers = [SubprocessIsolationProvider().describe(), MicroVMIsolationProvider().describe()]
    lines = ["Sandbox providers:"]
    for index, provider in enumerate(providers):
        default_name = "subprocess" if index == 0 else "microvm"
        name = provider.get("name") or provider.get("provider") or default_name
        available = _format_bool(bool(provider.get("available", False)))
        reason = provider.get("reason") or provider.get("execution_status") or "ok"
        lines.append(f"  {name}: available={available}, reason={reason}")
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"workspace": str(ws), "providers": providers},
    )


def _parse_policy_explain(arg: str) -> tuple[str, list[str]]:
    parts = shlex.split(arg)
    policy = "local-safe"
    if "--" in parts:
        parts = parts[parts.index("--") + 1 :]
    if parts[:2] and parts[0] == "--policy":
        if len(parts) < 3:
            raise ValueError("Usage: /policy explain [--policy NAME] -- <cmd...>")
        policy = parts[1]
        parts = parts[2:]
        if parts[:1] == ["--"]:
            parts = parts[1:]
    return policy, parts


def _parse_sandbox_run(arg: str) -> tuple[str, str, list[str]]:
    parts = shlex.split(arg)
    if parts[:1] == ["run"]:
        parts = parts[1:]
    policy = "local-safe"
    provider = "subprocess"
    command: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command = parts[index + 1 :]
            break
        if part == "--policy" and index + 1 < len(parts):
            policy = parts[index + 1]
            index += 2
            continue
        if part.startswith("--policy="):
            policy = part.split("=", 1)[1]
            index += 1
            continue
        if part == "--provider" and index + 1 < len(parts):
            provider = parts[index + 1]
            index += 2
            continue
        if part.startswith("--provider="):
            provider = part.split("=", 1)[1]
            index += 1
            continue
        command = parts[index:]
        break
    return policy, provider, command


def render_sandbox_run(arg: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        policy_name, provider, command = _parse_sandbox_run(arg)
        if not command:
            return SlashAdapterResult(
                state="blocked",
                text="Usage: /sandbox run [--policy NAME] [--provider subprocess] -- <cmd...>",
                exit_code=2,
            )
        policy = resolve_sandbox_policy(policy_name, ws)
        cwd = ensure_workspace_cwd(Path.cwd(), policy.workspace_root)
        decision = decide(command, policy)
        validate_command_paths(command, policy)
    except (KeyError, ValueError) as exc:
        return SlashAdapterResult(state="blocked", text=f"Blocked: {exc}", exit_code=2)

    started_at = utc_now()
    ended_at = started_at
    if not decision.allowed:
        audit = build_audit_event(
            command=command,
            cwd=cwd,
            decision=decision,
            provider=provider,
            started_at=started_at,
            ended_at=ended_at,
            exit_code=None,
            stdout_truncated=False,
            stderr_truncated=False,
            redaction_applied=False,
        )
        audit_path = persist_sandbox_audit_event(audit)
        audit["audit_path"] = str(audit_path)
        result = SandboxResult(
            command=command,
            cwd=str(cwd),
            classification=decision.classification,
            decision=decision,
            provider=provider,
            audit_event=audit,
        )
        return SlashAdapterResult(
            state="denied",
            text=(
                f"Sandbox denied: {' '.join(command)}\n"
                f"Classification: {decision.classification.value}\nReason: {decision.reason}"
            ),
            data=result.model_dump(mode="json"),
            exit_code=3,
        )

    if provider == "microvm":
        return SlashAdapterResult(
            state="blocked",
            text="Blocked: microVM execution not yet available through REPL sandbox run",
            data={"provider": provider, "reason": "microvm_execution_unavailable"},
            exit_code=2,
        )
    if provider != "subprocess":
        return SlashAdapterResult(
            state="blocked",
            text=f"Blocked: unsupported sandbox provider: {provider}",
            data={"provider": provider, "reason": "unsupported_provider"},
            exit_code=2,
        )

    iso = asyncio.run(
        SubprocessIsolationProvider(
            safe_env_keys=frozenset(policy.env_allowlist),
            workspace_root=ws,
            max_output_bytes=policy.max_output_bytes,
        ).execute(command, cwd=cwd, timeout_seconds=policy.timeout_seconds)
    )
    ended_at = utc_now()
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider=iso.provider,
        started_at=started_at,
        ended_at=ended_at,
        exit_code=iso.exit_code,
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
    )
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)
    result = SandboxResult(
        command=command,
        cwd=str(cwd),
        classification=decision.classification,
        decision=decision,
        provider=iso.provider,
        exit_code=iso.exit_code,
        stdout=iso.stdout,
        stderr=iso.stderr,
        duration_ms=iso.duration_ms,
        timed_out=iso.killed and iso.kill_reason == "timeout",
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
        audit_event=audit,
    )
    lines = [
        f"Sandbox allowed: {' '.join(command)}",
        f"Classification: {decision.classification.value}",
        f"Exit code: {iso.exit_code}",
    ]
    if iso.stdout:
        lines.extend(["stdout:", iso.stdout.rstrip()])
    if iso.stderr:
        lines.extend(["stderr:", iso.stderr.rstrip()])
    return SlashAdapterResult(
        state="present" if iso.exit_code == 0 else "error",
        text="\n".join(lines),
        data=result.model_dump(mode="json"),
        exit_code=iso.exit_code,
    )


def render_policy_explain(arg: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        policy_name, command = _parse_policy_explain(arg)
        if not command:
            return SlashAdapterResult(
                state="blocked",
                text="Usage: /policy explain [--policy NAME] -- <cmd...>",
                exit_code=2,
            )
        policy = resolve_sandbox_policy(policy_name, ws)
        decision = decide(command, policy)
        path_valid = True
        path_error = ""
        try:
            validate_command_paths(command, policy)
        except ValueError as exc:
            path_valid = False
            path_error = str(exc)
        allowed = decision.allowed and path_valid
        lines = [
            f"Policy: {policy.name}",
            f"Command: {' '.join(command)}",
            f"Classification: {decision.classification.value}",
            f"Decision: {'allow' if allowed else 'deny'}",
            f"Reason: {decision.reason if path_valid else path_error}",
        ]
        if decision.approval_required:
            lines.append("Approval required: yes")
        return SlashAdapterResult(
            state="present" if allowed else "denied",
            text="\n".join(lines),
            data={
                "policy": policy.name,
                "command": command,
                "classification": decision.classification.value,
                "allowed": allowed,
                "reason": decision.reason if path_valid else path_error,
            },
        )
    except (KeyError, ValueError) as exc:
        return SlashAdapterResult(state="blocked", text=f"Blocked: {exc}", exit_code=2)


def render_policy_list(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        policies = list_sandbox_policies(ws)
    except ValueError as exc:
        return SlashAdapterResult(state="blocked", text=f"Blocked: {exc}", exit_code=2)
    lines = ["Sandbox policies:"]
    for policy in policies:
        lines.append(
            "  "
            + policy.name
            + f" (network={_format_bool(policy.allow_network)}, install={_format_bool(policy.allow_install)}, unknown={_format_bool(policy.allow_unknown)})"
        )
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"policies": [p.model_dump(mode="json") for p in policies]},
    )


def render_policy_show(name: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    policy_name = name.strip() or "local-safe"
    try:
        policy = resolve_sandbox_policy(policy_name, ws)
    except (KeyError, ValueError) as exc:
        return SlashAdapterResult(state="absent", text=f"Policy not found: {exc}", exit_code=2)
    lines = [
        f"Policy: {policy.name}",
        f"Workspace: {policy.workspace_root}",
        f"Allow network: {_format_bool(policy.allow_network)}",
        f"Allow install: {_format_bool(policy.allow_install)}",
        f"Allow privileged: {_format_bool(policy.allow_privileged)}",
        f"Allow unknown: {_format_bool(policy.allow_unknown)}",
        f"Timeout: {policy.timeout_seconds}s",
        f"Max output: {policy.max_output_bytes} bytes",
    ]
    return SlashAdapterResult(
        state="present", text="\n".join(lines), data={"policy": policy.model_dump(mode="json")}
    )


def _trace_files(workspace: Path) -> list[Path]:
    traces = workspace / ".arc" / "traces"
    if not traces.exists():
        return []
    return sorted(traces.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def render_runs_list(workspace: Path | None = None, limit: int = 10) -> SlashAdapterResult:
    ws = _workspace(workspace)
    run_files = _trace_files(ws)
    if not run_files:
        return SlashAdapterResult(state="absent", text="No runs stored.", data={"runs": []})
    lines = [f"Runs ({len(run_files)}):"]
    rows = []
    for file_path in run_files[:limit]:
        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S")
        rows.append({"run_id": file_path.stem, "path": str(file_path), "bytes": stat.st_size})
        lines.append(f"  {file_path.stem[:16]}  {stat.st_size}B  {mtime}")
    return SlashAdapterResult(state="present", text="\n".join(lines), data={"runs": rows})


def _load_trace_events(workspace: Path, run_id: str) -> list[dict[str, Any]]:
    trace = workspace / ".arc" / "traces" / f"{run_id}.jsonl"
    if not trace.exists():
        matches = list((workspace / ".arc" / "traces").glob(f"{run_id}*.jsonl"))
        if len(matches) == 1:
            trace = matches[0]
    if not trace.exists():
        raise FileNotFoundError(run_id)
    events: list[dict[str, Any]] = []
    for line in trace.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def render_run_show(run_id: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    clean = run_id.strip()
    if not clean:
        return SlashAdapterResult(state="blocked", text="Usage: /runs show <run_id>", exit_code=2)
    try:
        events = _load_trace_events(ws, clean)
    except FileNotFoundError:
        return SlashAdapterResult(state="absent", text=f"Run not found: {clean}", exit_code=2)
    except json.JSONDecodeError as exc:
        return SlashAdapterResult(
            state="degraded", text=f"Run trace is malformed: {exc}", exit_code=1
        )
    event_types = [
        str(event.get("type") or event.get("event_type") or "unknown") for event in events
    ]
    lines = [f"Run: {clean}", f"Events: {len(events)}"]
    if event_types:
        lines.append(f"First event: {event_types[0]}")
        lines.append(f"Last event: {event_types[-1]}")
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"run_id": clean, "event_count": len(events), "event_types": event_types},
    )


def render_run_status(run_id: str, workspace: Path | None = None) -> SlashAdapterResult:
    result = render_run_show(run_id, workspace)
    if result.state != "present":
        return result
    event_types = result.data.get("event_types", [])
    terminal = next(
        (
            event
            for event in reversed(event_types)
            if event in {"RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED"}
        ),
        None,
    )
    status = terminal or "unknown"
    return SlashAdapterResult(
        state="present",
        text=f"Run: {result.data['run_id']}\nStatus: {status}\nEvents: {result.data['event_count']}",
        data={**result.data, "status": status},
    )


# ── Phase 41 P1: audit, task, providers, mcp adapters ──────────────────


def render_audit_list(
    limit: int = 20,
    workspace: Path | None = None,
) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        events = list_sandbox_audit_events(audit_dir=ws / ".arc" / "audit", limit=limit)
    except (OSError, ValueError) as exc:
        return SlashAdapterResult(state="degraded", text=f"Degraded: {exc}", exit_code=1)
    if not events.get("events"):
        return SlashAdapterResult(state="absent", text="No audit events found.", data=events)
    lines = ["Audit events:"]
    for event in events["events"]:
        cmd = " ".join(event.get("command", []))
        classification = event.get("classification", "unknown")
        allowed = event.get("allowed")
        decision = "allowed" if allowed else "denied"
        lines.append(
            f"  {event.get('event_id', '?')[:12]}  {decision:7s}  {classification:12s}  {cmd}"
        )
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data=events,
    )


def render_audit_verify(run_id: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    clean = run_id.strip()
    if not clean:
        return SlashAdapterResult(
            state="blocked",
            text="Usage: /audit verify <run_id>",
            exit_code=2,
        )
    try:
        result = verify_sandbox_audit(audit_dir=ws / ".arc" / "audit")
    except Exception as exc:
        return SlashAdapterResult(
            state="error",
            text=f"Error verifying audit: {exc}",
            exit_code=1,
        )
    ok = result.get("ok")
    lines = [
        f"Run: {clean}",
        f"Audit chain: {'VERIFIED' if ok else 'FAILED'}",
        f"Chain: {result.get('chain', 'unknown')}",
        f"Events: {result.get('events', 'unknown')}",
    ]
    if result.get("reason"):
        lines.append(f"Reason: {result['reason']}")
    return SlashAdapterResult(
        state="present" if ok else "denied",
        text="\n".join(lines),
        data=result,
    )


def render_task_list(
    status_filter: str | None = None,
    limit: int = 50,
    workspace: Path | None = None,
) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        from ..tasks import TaskExecutor, TaskStorage

        storage = TaskStorage(ws / ".arc" / "tasks.db")
        executor = TaskExecutor(storage)
        status_enum = None
        if status_filter:
            from ..tasks.models import TaskStatus

            try:
                status_enum = TaskStatus(status_filter)
            except ValueError:
                return SlashAdapterResult(
                    state="blocked",
                    text=f"Blocked: invalid status filter: {status_filter}",
                    exit_code=2,
                )
        tasks = executor.list_tasks(status=status_enum, limit=limit)
    except Exception as exc:
        return SlashAdapterResult(
            state="degraded",
            text=f"Degraded: {exc}",
            exit_code=1,
        )
    if not tasks:
        return SlashAdapterResult(state="absent", text="No tasks found.", data={"tasks": []})
    lines = ["Tasks:"]
    for t in tasks:
        lines.append(f"  {t.id[:12]}  {t.status.value:10s}  {t.type.value:5s}  {t.operation}")
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"tasks": [t.model_dump() for t in tasks], "count": len(tasks)},
    )


def render_task_status(task_id: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    clean = task_id.strip()
    if not clean:
        return SlashAdapterResult(
            state="blocked",
            text="Usage: /task status <task_id>",
            exit_code=2,
        )
    try:
        from ..tasks import TaskExecutor, TaskStorage

        storage = TaskStorage(ws / ".arc" / "tasks.db")
        executor = TaskExecutor(storage)
        task = executor.get_task_status(clean)
    except Exception as exc:
        return SlashAdapterResult(
            state="error",
            text=f"Error: {exc}",
            exit_code=1,
        )
    if not task:
        return SlashAdapterResult(
            state="absent",
            text=f"Task not found: {clean}",
            exit_code=2,
        )
    lines = [
        f"Task: {task.id}",
        f"Type: {task.type.value}",
        f"Operation: {task.operation}",
        f"Status: {task.status.value.upper()}",
        f"Created: {task.created_at}",
    ]
    if task.started_at:
        lines.append(f"Started: {task.started_at}")
    if task.ended_at:
        lines.append(f"Ended: {task.ended_at}")
    if task.retry_count > 0:
        lines.append(f"Retries: {task.retry_count}/{task.max_retries}")
    if task.error:
        lines.append(f"Error: {task.error}")
    if task.result:
        lines.append(f"Result: {json.dumps(task.result, default=str)}")
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"task": task.model_dump()},
    )


def render_providers_status() -> SlashAdapterResult:
    try:
        from ..provider_action import provider_statuses

        statuses = provider_statuses(os.environ)
    except Exception as exc:
        return SlashAdapterResult(
            state="error",
            text=f"Error: {exc}",
            exit_code=1,
        )
    lines = ["Provider statuses:"]
    for status in statuses:
        configured = "yes" if status.api_key_configured else "no"
        lines.append(
            f"  {status.provider:20s}  configured={configured:3s}  source={status.api_key_source}"
        )
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"providers": [s.model_dump() for s in statuses], "count": len(statuses)},
    )


def render_mcp_status(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        from ..security.trust import ensure_trusted

        ensure_trusted(ws)
        trust_ok = True
    except Exception:
        trust_ok = False
    mcp_available = False
    try:
        import importlib.util

        spec = importlib.util.find_spec("agent_runtime_cockpit.mcp.server")
        mcp_available = spec is not None
    except (ImportError, ValueError):
        mcp_available = False
    lines = ["MCP status:"]
    lines.append(f"  Workspace trusted: {_format_bool(trust_ok)}")
    lines.append(f"  MCP server available: {_format_bool(mcp_available)}")
    if not trust_ok:
        lines.append("  Note: MCP tools are gated by workspace trust")
    data = {
        "workspace_trusted": trust_ok,
        "mcp_available": mcp_available,
        "workspace": str(ws),
    }
    state = "present" if trust_ok and mcp_available else "degraded"
    return SlashAdapterResult(
        state=state,
        text="\n".join(lines),
        data=data,
    )


def render_hitl_pending(
    include_expired: bool = False, workspace: Path | None = None
) -> SlashAdapterResult:
    ws = _workspace(workspace)
    from ..audit.hitl_sqlite_store import HitlSqliteStore

    prompts = HitlSqliteStore(ws / ".arc" / "hitl.db").list_prompts(include_expired=include_expired)
    if not prompts:
        return SlashAdapterResult(
            state="absent", text="No pending HITL prompts.", data={"prompts": []}
        )
    lines = ["Pending HITL prompts:"]
    for prompt in prompts:
        lines.append(f"  {prompt.hitl_id[:12]}  run={prompt.run_id}  step={prompt.step_id}")
        lines.append(f"    {prompt.prompt_text[:160]}")
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"count": len(prompts), "prompts": [p.model_dump() for p in prompts]},
    )


def render_hitl_respond(arg: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    parts = shlex.split(arg)
    if len(parts) < 2:
        return SlashAdapterResult(
            state="blocked",
            text="Usage: /hitl respond <id> <approve|reject|modify|skip>",
            exit_code=2,
        )
    hitl_id, decision = parts[0], parts[1].lower()
    reason = " ".join(parts[2:])
    try:
        from ..audit.hitl import HitlDecision
        from ..audit.hitl_sqlite_store import HitlSqliteStore

        decision_enum = HitlDecision(decision)
        store = HitlSqliteStore(ws / ".arc" / "hitl.db")
        token = os.environ.get("HITL_TOKEN") or store.get_token(hitl_id)
        if not token:
            return SlashAdapterResult(
                state="blocked",
                text=f"Blocked: HITL prompt not found or token missing: {hitl_id}",
                exit_code=2,
            )
        response = store.respond(
            hitl_id=hitl_id,
            decision=decision_enum,
            token=token,
            operator_id="repl-user",
            notes=reason,
            audit_hash=None,
        )
    except ValueError as exc:
        return SlashAdapterResult(state="blocked", text=f"Blocked: {exc}", exit_code=2)
    if response is None:
        return SlashAdapterResult(
            state="blocked",
            text=f"Blocked: failed to respond to HITL prompt: {hitl_id}",
            exit_code=2,
        )
    return SlashAdapterResult(
        state="present",
        text=f"HITL response recorded: {response.hitl_id}\nDecision: {response.decision.value}",
        data={"response": response.model_dump()},
    )


def render_context_pack(task: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    clean = task.strip()
    if not clean:
        return SlashAdapterResult(state="blocked", text="Usage: /context pack <task>", exit_code=2)
    from ..context.pack import ContextPackGenerator

    entries = ContextPackGenerator().generate(clean, ws, save=True)
    lines = [f"Context pack: {len(entries)} entries"]
    for entry in entries[:10]:
        title = getattr(entry, "title", None) or getattr(entry, "source", "entry")
        lines.append(f"  {title}")
    return SlashAdapterResult(
        state="present" if entries else "absent",
        text="\n".join(lines),
        data={"count": len(entries), "entries": [e.model_dump() for e in entries]},
    )


def render_workspace_trust_status(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    from ..security.trust import resolve_trust

    resolution = resolve_trust(ws)
    lines = [f"Workspace: {ws}", f"Trust: {resolution.level.value}", f"Reason: {resolution.reason}"]
    if resolution.warning:
        lines.append(f"Warning: {resolution.warning}")
    return SlashAdapterResult(
        state="present" if resolution.level.value == "trusted" else "degraded",
        text="\n".join(lines),
        data=resolution.model_dump(mode="json") | {"workspace": str(ws)},
    )


def render_config_show(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    from ..config.loader import load_config

    config = load_config(workspace=ws)
    flattened = config.flatten()
    lines = ["Config:"]
    for key, value in sorted(flattened.items()):
        lines.append(f"  {key}: {value}")
    return SlashAdapterResult(state="present", text="\n".join(lines), data={"config": flattened})


def render_config_validate(workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    try:
        from ..config.loader import load_config

        config = load_config(workspace=ws)
    except Exception as exc:
        return SlashAdapterResult(state="error", text=f"Config invalid: {exc}", exit_code=1)
    return SlashAdapterResult(
        state="present",
        text="Config valid.",
        data={"valid": True, "version": config.version, "workspace": str(ws)},
    )


def render_replay(run_id: str, workspace: Path | None = None) -> SlashAdapterResult:
    ws = _workspace(workspace)
    clean = run_id.strip()
    if not clean:
        return SlashAdapterResult(state="blocked", text="Usage: /replay <run_id>", exit_code=2)
    try:
        from ..adapters.langgraph.replay_detector import analyze_run_replay_capability

        capability = analyze_run_replay_capability(clean, ws, None)
    except Exception as exc:
        return SlashAdapterResult(
            state="degraded", text=f"Replay analysis unavailable: {exc}", exit_code=1
        )
    return SlashAdapterResult(
        state="present",
        text=f"Replay: {clean}\nSummary: {capability.get_capability_summary()}",
        data={
            "run_id": capability.run_id,
            "runtime": capability.runtime,
            "can_replay_trace": capability.can_replay_trace,
            "can_resume_checkpoint": capability.can_resume_checkpoint,
            "determinism_level": capability.determinism_level,
            "warnings": capability.warnings,
        },
    )


def render_battle_list(limit: int = 20, workspace: Path | None = None) -> SlashAdapterResult:
    from ..battle import BattleStore

    ws = _workspace(workspace)
    battles = BattleStore(ws / ".arc" / "battles.db").list_battle_runs(limit=limit)
    if not battles:
        return SlashAdapterResult(state="absent", text="No battles found.", data={"battles": []})
    lines = ["Battles:"]
    for battle in battles:
        lines.append(
            f"  {battle.id[:12]}  {battle.status.value:10s}  workers={battle.workers}  {battle.prompt[:80]}"
        )
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={"count": len(battles), "battles": [b.model_dump(mode="json") for b in battles]},
    )


def render_battle_show(battle_id: str, workspace: Path | None = None) -> SlashAdapterResult:
    clean = battle_id.strip()
    if not clean:
        return SlashAdapterResult(
            state="blocked", text="Usage: /battle show <battle_id>", exit_code=2
        )
    from ..battle import BattleStore

    ws = _workspace(workspace)
    store = BattleStore(ws / ".arc" / "battles.db")
    battle = store.get_battle_run(clean)
    if battle is None:
        return SlashAdapterResult(state="absent", text=f"Battle not found: {clean}", exit_code=2)
    candidates = store.get_candidates(clean)
    votes = store.get_votes(clean)
    outcome = store.get_outcome(clean)
    lines = [
        f"Battle: {battle.id}",
        f"Status: {battle.status.value}",
        f"Workers: {battle.workers}",
        f"Prompt: {battle.prompt}",
        f"Candidates: {len(candidates)}",
        f"Votes: {len(votes)}",
    ]
    return SlashAdapterResult(
        state="present",
        text="\n".join(lines),
        data={
            "battle": battle.model_dump(mode="json"),
            "candidates": [c.model_dump(mode="json") for c in candidates],
            "votes": [v.model_dump(mode="json") for v in votes],
            "outcome": outcome.model_dump(mode="json") if outcome else None,
        },
    )


def render_events_watch(since: int = 20, event_type: str | None = None) -> SlashAdapterResult:
    from ..events.bus import get_bus

    bus = get_bus()
    start = max(0, len(bus._ring_buffer) - max(0, since))
    events = bus._replay_since(start)
    if event_type:
        events = [event for event in events if event.event_type == event_type]
    if not events:
        return SlashAdapterResult(
            state="absent",
            text="No buffered events. Live watch is available in non-REPL CLI only.",
            data={"events": [], "live_watch": False},
        )
    lines = ["Buffered events:"]
    for event in events:
        lines.append(f"  {event.event_type}  run={getattr(event, 'run_id', '')}")
    return SlashAdapterResult(
        state="degraded",
        text="\n".join(lines) + "\nLive watch is available in non-REPL CLI only.",
        data={"events": [e.model_dump(mode="json") for e in events], "live_watch": False},
    )


def render_dashboard(
    session: Any | None = None, workspace: Path | None = None
) -> SlashAdapterResult:
    ws = _workspace(workspace)
    sections = [
        ("system", render_status(session or object(), ws)),
        ("runs", render_runs_list(ws, limit=5)),
        ("sandbox", render_sandbox_doctor(ws)),
        ("providers", render_providers_status()),
        ("mcp", render_mcp_status(ws)),
        ("tasks", render_task_list(workspace=ws, limit=5)),
        ("audit", render_audit_list(workspace=ws, limit=5)),
    ]
    lines = ["ARC Dashboard:"]
    data: dict[str, Any] = {"workspace": str(ws), "sections": {}}
    for name, result in sections:
        lines.append(f"\n{name}: {result.state}")
        summary = result.text.splitlines()[0] if result.text else result.state
        lines.append(f"  {summary}")
        data["sections"][name] = {"state": result.state, "data": result.data}
    degraded = any(result.state in {"degraded", "error"} for _, result in sections)
    return SlashAdapterResult(
        state="degraded" if degraded else "present",
        text="\n".join(lines),
        data=data,
    )
