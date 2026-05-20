from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .commands import CommandDef, get_registry
from .cancellation import Cancelled, CancellationReason, CancellationToken
from .session import ChatSession
from ..swarmgraph import SwarmGraphRunner
from ..swarmgraph.config import SwarmGraphConfig


@dataclass
class CommandResult:
    state: str
    output: str = ""
    reason: str = ""
    remediation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _build_registry():
    """Build and return the command registry with all slash commands.

    Idempotent: if commands are already registered, returns the existing registry.
    """
    registry = get_registry()
    if registry.list_commands():
        return registry  # Already initialized

    # ── Meta ──────────────────────────────────────────────────────────────
    registry.register(CommandDef(
        name="help",
        help_text="Show this help message",
        category="meta",
        handler=cmd_help,
        aliases=[],
        gates_required=[],
        mode_required=[],
        renders=["present"],
        requires_events=[],
        privileged=False,
        trust_required="user",
    ))
    registry.register(CommandDef(
        name="version",
        help_text="Show version info",
        category="meta",
        handler=cmd_version,
        gates_required=[], mode_required=[], renders=["present"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="exit",
        help_text="Save session and exit",
        category="meta",
        handler=cmd_exit,
        aliases=["quit"],
        gates_required=[], mode_required=[], renders=["present"], requires_events=[], privileged=False, trust_required="user",
    ))

    # ── Session ───────────────────────────────────────────────────────────
    registry.register(CommandDef(
        name="clear",
        help_text="Clear session history",
        category="session",
        handler=cmd_clear,
        gates_required=[], mode_required=[], renders=["present"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="summary",
        help_text="Show session summary",
        category="session",
        handler=cmd_summary,
        gates_required=[], mode_required=[], renders=["present", "absent"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="sessions",
        help_text="List saved sessions",
        category="session",
        handler=cmd_sessions,
        gates_required=[], mode_required=[], renders=["present", "absent"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="history",
        help_text="Show recent messages",
        category="session",
        handler=cmd_history,
        gates_required=[], mode_required=[], renders=["present", "absent"], requires_events=[], privileged=False, trust_required="user",
    ))

    # ── Runtime ───────────────────────────────────────────────────────────
    registry.register(CommandDef(
        name="run",
        help_text="Execute prompt with SwarmGraph runner",
        category="runtime",
        handler=cmd_run,
        gates_required=[], mode_required=["build", "auto"], renders=["present", "blocked"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="plan",
        help_text="Switch to Plan mode (read-only)",
        category="runtime",
        handler=cmd_plan,
        gates_required=[], mode_required=[], renders=["present"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="build",
        help_text="Switch to Build mode (can write)",
        category="runtime",
        handler=cmd_build,
        gates_required=[], mode_required=[], renders=["present"], requires_events=[], privileged=False, trust_required="user",
    ))
    registry.register(CommandDef(
        name="auto",
        help_text="Switch to policy-driven mode",
        category="runtime",
        handler=cmd_auto,
        gates_required=[], mode_required=[], renders=["present", "blocked"], requires_events=[], privileged=False, trust_required="user",
    ))

    # ── Workspace ─────────────────────────────────────────────────────────
    registry.register(CommandDef(
        name="status",
        help_text="Show workspace, runtime, and session status",
        category="workspace",
        handler=cmd_status,
        gates_required=[], mode_required=[], renders=["present", "absent"], requires_events=[], privileged=False, trust_required="workspace",
    ))
    registry.register(CommandDef(
        name="doctor",
        help_text="Run environment diagnostics",
        category="workspace",
        handler=cmd_doctor,
        gates_required=[], mode_required=[], renders=["present", "degraded"], requires_events=[], privileged=False, trust_required="workspace",
    ))
    registry.register(CommandDef(
        name="runs",
        help_text="List recent run records",
        category="workspace",
        handler=cmd_runs,
        gates_required=[], mode_required=[], renders=["present", "absent"], requires_events=[], privileged=False, trust_required="workspace",
    ))

    return registry


# ── Command handler implementations ────────────────────────────────────────

def cmd_help(_arg: str, _session: ChatSession) -> str:
    registry = get_registry()
    return (
        "Available slash commands:"
        + registry.help_text()
        + "\n\n"
        + 'Type a message to send a query or use /slash commands above.'
    )


def cmd_clear(_arg: str, session: ChatSession) -> str:
    session.history.clear()
    return "Session history cleared."


def cmd_run(arg: Any, session: Any, cancellation_token: Any = None) -> str | CommandResult:
    if isinstance(arg, list):
        return _handle_run_context(arg, session)
    if not arg:
        return "Usage: /run <prompt>"
    config = SwarmGraphConfig(
        num_workers=3,
        max_rounds=1,
    )
    runner = SwarmGraphRunner(config=config)
    result = runner.run(prompt=arg, cancellation_token=cancellation_token)
    session.add_message("user", arg)
    output = result.get("results", [])
    summary = f"Run completed: status={result.get('status')}, "
    summary += f"tasks={result.get('total_tasks', 0)}, "
    summary += f"cost=${result.get('total_cost_usd', 0):.4f}"
    if output:
        summary += f"\nOutput: {output[0].get('output', '')}"
    return summary


def _gate_open(ctx: Any) -> bool:
    return os.environ.get("ARC_ALLOW_RUN") == "1" or bool(getattr(ctx.session, "allow_run", False))


def _emit(ctx: Any, name: str, payload: dict[str, Any]) -> None:
    emit = getattr(ctx, "emit_event", None)
    if callable(emit):
        emit(name, payload)


def _handle_run_context(args: list[str], ctx: Any) -> CommandResult:
    if not _gate_open(ctx):
        return CommandResult(
            state="blocked",
            reason="gate_closed",
            remediation="Set ARC_ALLOW_RUN=1 or enable session allow_run.",
        )
    prompt = " ".join(args).strip()
    if not prompt:
        return CommandResult(state="blocked", reason="missing_prompt", remediation="Usage: /run <prompt>")

    factory = getattr(ctx, "run_token_factory", None)
    token: CancellationToken = factory() if callable(factory) else CancellationToken()
    started = time.monotonic()
    previous = signal.getsignal(signal.SIGINT)

    def _on_sigint(signum: int, frame: Any) -> None:  # noqa: ARG001
        token.cancel(CancellationReason.USER, "SIGINT")

    def _on_progress(payload: dict[str, Any]) -> None:
        stage = str(payload.get("stage", "unknown"))
        _emit(ctx, f"run.progress.{stage}", payload)

    signal.signal(signal.SIGINT, _on_sigint)
    try:
        _emit(ctx, "run.started", {"prompt_chars": len(prompt)})
        runner = SwarmGraphRunner(getattr(ctx, "runtime", None), cancellation_token=token)
        result = runner.run(prompt, on_progress=_on_progress)
        output = result.render() if hasattr(result, "render") else str(result)
        _emit(ctx, "run.completed", {"elapsed_ms": int((time.monotonic() - started) * 1000)})
        return CommandResult(state="present", output=output)
    except Cancelled as exc:
        _emit(ctx, "run.cancelled", {
            "reason": exc.reason.value,
            "detail": exc.detail,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        })
        return CommandResult(state="degraded", output=str(exc), reason="cancelled")
    finally:
        signal.signal(signal.SIGINT, previous)


def cmd_summary(_arg: str, session: ChatSession) -> str:
    n = len(session.history)
    return f"Session {session.id}: {n} messages, created {session.created_at[:19]}"


def cmd_sessions(_arg: str, _session: ChatSession) -> str:
    sessions = ChatSession.list_sessions()
    if not sessions:
        return "No saved sessions."
    lines = ["Saved sessions:"]
    for s in sessions[:10]:
        n = len(s.history)
        lines.append(f"  {s.id[:16]}... - {n} msgs, {s.updated_at[:19]}")
    return "\n".join(lines)


def cmd_history(arg: str, session: ChatSession) -> str:
    n = int(arg) if arg.isdigit() else 10
    recent = session.history[-n:]
    if not recent:
        return "No messages in history."
    lines: list[str] = []
    for msg in recent:
        role = msg.get("role", "?")
        content = msg.get("content", "")[:200]
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def cmd_version(_arg: str, _session: ChatSession) -> str:
    return "ARC Studio - SwarmGraph Native Runtime v0.1.0-alpha"


def cmd_exit(_arg: str, _session: ChatSession) -> str:
    return "__EXIT__"


def cmd_plan(_arg: str, session: ChatSession) -> str:
    session.set_mode("plan")
    return "Switched to Plan mode (read-only)."


def cmd_build(_arg: str, session: ChatSession) -> str:
    session.set_mode("build")
    return "Switched to Build mode (can write)."


def cmd_auto(_arg: str, session: ChatSession) -> str:
    session.set_mode("auto")
    return "Switched to Auto mode (policy-driven)."


def cmd_status(_arg: str, session: ChatSession) -> str:
    from pathlib import Path
    ws = Path.cwd().resolve()
    lines = [
        f"Workspace: {ws}",
        f"Mode: {session.mode.upper()}",
        f"Session: {session.id[:12]}",
        f"Messages: {len(session.history)}",
    ]
    runtime_dir = ws / ".arc" / "traces"
    run_count = len(list(runtime_dir.glob("*.jsonl"))) if runtime_dir.exists() else 0
    lines.append(f"Stored runs: {run_count}")
    return "\n".join(lines)


def cmd_doctor(_arg: str, _session: ChatSession) -> str:
    from pathlib import Path
    ws = Path.cwd().resolve()
    checks = [
        ("Workspace exists", ws.exists()),
        ("ARC dir exists", (ws / ".arc").exists()),
    ]
    results = []
    for label, ok in checks:
        glyph = "✓" if ok else "✗"
        results.append(f"  {glyph} {label}")
    return "\n".join(results)


def cmd_runs(_arg: str, _session: ChatSession) -> str:
    from pathlib import Path
    from datetime import datetime
    ws = Path.cwd().resolve()
    traces = ws / ".arc" / "traces"
    if not traces.exists():
        return "No runs stored."
    run_files = sorted(traces.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_files:
        return "No runs stored."
    lines = [f"Runs ({len(run_files)}):"]
    for f in run_files[:10]:
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M:%S")
        lines.append(f"  {f.stem[:16]}  {f.stat().st_size}B  {mtime}")
    return "\n".join(lines)


class SlashCommandHandler:
    """Handler that routes slash commands through the unified registry."""

    def __init__(self, runner: Any = None) -> None:
        self.runner = runner
        self.cancellation_token: Any = None
        self._registry = _build_registry()

    def handle(self, command: str, session: ChatSession) -> str | None:
        cmd = command.strip()
        parts = cmd.split(maxsplit=1)
        name = parts[0].lstrip("/").lower()
        arg = parts[1] if len(parts) > 1 else ""

        defn = self._registry.get(name)
        if defn is None:
            if cmd.startswith("/"):
                return f"Unknown slash command: {name}. Try /help."
            return None

        if defn.mode_required and session.mode not in defn.mode_required:
            allowed = ", ".join(defn.mode_required)
            return f"Blocked: /{name} requires mode: {allowed}. Current mode: {session.mode}."

        if name == "run":
            return defn.handler(arg, session, self.cancellation_token)
        return defn.handler(arg, session)
