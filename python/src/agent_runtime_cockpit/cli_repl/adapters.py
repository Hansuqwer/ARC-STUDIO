"""Read-only slash-command adapters for the interactive CLI."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..isolation.microvm import MicroVMIsolationProvider
from ..isolation.subprocess import SubprocessIsolationProvider
from ..runtime.mode import RuntimeMode
from ..security.sandbox import (
    decide,
    list_sandbox_policies,
    resolve_sandbox_policy,
    validate_command_paths,
)


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
