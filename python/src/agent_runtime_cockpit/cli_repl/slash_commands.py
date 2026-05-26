from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, TypeVar

from ..budget.schema import (
    BudgetConfig,
    BudgetEnforcer,
    BudgetExceeded,
    BudgetState,
    ConfirmationRequired,
)
from ..providers import AnthropicClient, preflight_with_estimator
from ..runtime.mode import RuntimeMode
from ..runtime.registry import default_runtime_registry
from ..runtime.turn_manager import TurnManager
from ..swarmgraph import SwarmGraphRunner
from ..swarmgraph.config import SwarmGraphConfig
from ..tools import default_tool_registry
from .adapters import (
    SlashAdapterResult,
    render_audit_list,
    render_audit_verify,
    render_doctor_summary,
    render_mcp_status,
    render_policy_explain,
    render_policy_list,
    render_policy_show,
    render_providers_status,
    render_run_show,
    render_run_status,
    render_runs_list,
    render_sandbox_doctor,
    render_sandbox_run,
    render_read,
    render_search,
    render_status,
    render_task_list,
    render_task_status,
)
from .cancellation import CancellationReason, CancellationToken, Cancelled
from .commands import CommandDef, get_registry
from .session import ChatSession

T = TypeVar("T")


def _run_coro_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine synchronously, handling both sync and async contexts.

    If called from a sync context (no running event loop), uses asyncio.run().
    If called from an async context (event loop already running), runs the
    coroutine in a worker thread to avoid nesting event loops.

    Args:
        coro: The coroutine to execute.

    Returns:
        The result of the coroutine.

    """
    try:
        # Check if we're already in an event loop
        asyncio.get_running_loop()
        # We're in an async context; run in a worker thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No event loop running; safe to use asyncio.run()
        return asyncio.run(coro)


@dataclass
class CommandResult:
    state: str
    output: str = ""
    reason: str = ""
    remediation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.output:
            return self.output
        if self.reason:
            return f"{self.state}: {self.reason}"
        return self.state

    def __contains__(self, value: str) -> bool:
        return value in str(self)


def _build_registry():
    """Build and return the command registry with all slash commands.

    Idempotent: if commands are already registered, returns the existing registry.
    """
    registry = get_registry()
    if registry.list_commands():
        return registry  # Already initialized

    # ── Meta ──────────────────────────────────────────────────────────────
    registry.register(
        CommandDef(
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
        )
    )
    registry.register(
        CommandDef(
            name="version",
            help_text="Show version info",
            category="meta",
            handler=cmd_version,
            gates_required=[],
            mode_required=[],
            renders=["present"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="exit",
            help_text="Save session and exit",
            category="meta",
            handler=cmd_exit,
            aliases=["quit"],
            gates_required=[],
            mode_required=[],
            renders=["present"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )

    # ── Session ───────────────────────────────────────────────────────────
    registry.register(
        CommandDef(
            name="clear",
            help_text="Clear session history",
            category="session",
            handler=cmd_clear,
            gates_required=[],
            mode_required=[],
            renders=["present"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="summary",
            help_text="Show session summary",
            category="session",
            handler=cmd_summary,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="sessions",
            help_text="List saved sessions",
            category="session",
            handler=cmd_sessions,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="history",
            help_text="Show recent messages",
            category="session",
            handler=cmd_history,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )

    # ── Runtime ───────────────────────────────────────────────────────────
    registry.register(
        CommandDef(
            name="run",
            help_text="Execute prompt with SwarmGraph runner",
            category="runtime",
            handler=cmd_run,
            gates_required=[],
            mode_required=["build", "auto"],
            renders=["present", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="runtime",
            help_text="Show or set runtime mode: fake, gated_local, provider_backed",
            category="runtime",
            handler=cmd_runtime,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="tools",
            help_text="Manage session tools: /tools list|enable|disable",
            category="runtime",
            handler=cmd_tools,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="mode",
            help_text="Alias for /runtime",
            category="runtime",
            handler=cmd_runtime,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="plan",
            help_text="Switch to Plan mode (read-only)",
            category="runtime",
            handler=cmd_plan,
            gates_required=[],
            mode_required=[],
            renders=["present"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="build",
            help_text="Switch to Build mode (can write)",
            category="runtime",
            handler=cmd_build,
            gates_required=[],
            mode_required=[],
            renders=["present"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )
    registry.register(
        CommandDef(
            name="auto",
            help_text="Switch to policy-driven mode",
            category="runtime",
            handler=cmd_auto,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
        )
    )

    # ── Workspace ─────────────────────────────────────────────────────────
    registry.register(
        CommandDef(
            name="status",
            help_text="Show workspace, runtime, and session status",
            category="workspace",
            handler=cmd_status,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/status",
        )
    )
    registry.register(
        CommandDef(
            name="doctor",
            help_text="Run environment diagnostics",
            category="workspace",
            handler=cmd_doctor,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/doctor",
        )
    )
    registry.register(
        CommandDef(
            name="runs",
            help_text="List/show run records: /runs [list|show|status]",
            category="workspace",
            handler=cmd_runs,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/runs [list|show|status] [run_id]",
            subcommands=["list", "show", "status"],
        )
    )
    registry.register(
        CommandDef(
            name="read",
            help_text="Read a workspace file: /read [--offset N] [--limit N] <path>",
            category="workspace",
            handler=cmd_read,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "blocked", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/read [--offset N] [--limit N] <path>",
        )
    )
    registry.register(
        CommandDef(
            name="search",
            help_text="Search workspace text: /search <regex> [--include GLOB] [--path PATH]",
            category="workspace",
            handler=cmd_search,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "blocked", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/search <regex> [--include GLOB] [--path PATH]",
        )
    )
    registry.register(
        CommandDef(
            name="sandbox",
            help_text="Sandbox tools: /sandbox doctor|run -- <cmd...>",
            category="workspace",
            handler=cmd_sandbox,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/sandbox doctor|run [--policy NAME] -- <cmd...>",
            subcommands=["doctor", "run"],
        )
    )
    registry.register(
        CommandDef(
            name="policy",
            help_text="Explain/list sandbox policies",
            category="compliance",
            handler=cmd_policy,
            gates_required=[],
            mode_required=[],
            renders=["present", "denied", "blocked", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/policy explain [--policy NAME] -- <cmd...>",
            subcommands=["explain", "list", "show"],
        )
    )
    registry.register(
        CommandDef(
            name="audit",
            help_text="Audit events: /audit [list [limit]]|verify <run_id>",
            category="audit",
            handler=cmd_audit,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "denied", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/audit [list [limit]]|verify <run_id>",
            subcommands=["list", "verify"],
        )
    )
    registry.register(
        CommandDef(
            name="task",
            help_text="Task management: /task [list [--status S] [--limit N]]|status <id>",
            category="tasks",
            handler=cmd_task,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "error"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/task [list [--status S] [--limit N]]|status <task_id>",
            subcommands=["list", "status"],
        )
    )
    registry.register(
        CommandDef(
            name="providers",
            help_text="Show provider statuses",
            category="providers",
            handler=cmd_providers_status,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/providers",
            subcommands=["status"],
        )
    )
    registry.register(
        CommandDef(
            name="mcp",
            help_text="Show MCP server status",
            category="MCP",
            handler=cmd_mcp_status,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/mcp",
            subcommands=["status"],
        )
    )

    return registry


# ── Command handler implementations ────────────────────────────────────────


def cmd_help(_arg: str, _session: ChatSession) -> str:
    registry = get_registry()
    groups = {
        "session": ["help", "clear", "summary", "sessions", "history", "exit"],
        "run": ["run", "runtime", "mode", "plan", "build", "auto", "runs"],
        "sandbox": ["sandbox"],
        "policy": ["policy"],
        "workspace": ["status", "doctor", "read", "search"],
        "providers": ["providers"],
        "tools": ["tools"],
        "audit": ["audit"],
        "tasks": ["task"],
        "MCP": ["mcp"],
    }
    lines = ["Available slash commands:"]
    for group, names in groups.items():
        lines.append(f"\n{group}:")
        if not names:
            lines.append("  deferred: not implemented in REPL yet")
            continue
        for name in names:
            cmd = registry.get(name)
            if cmd is None:
                lines.append(f"  /{name} (absent)")
                continue
            usage = cmd.usage or f"/{cmd.name}"
            states = ",".join(cmd.renders)
            lines.append(f"  {usage} - {cmd.help_text} [{states}]")
    lines.append("\nType a message to send a query or use /slash commands above.")
    return "\n".join(lines)


def cmd_clear(_arg: str, session: ChatSession) -> str:
    session.history.clear()
    return "Session history cleared."


def cmd_run(arg: Any, session: Any, cancellation_token: Any = None) -> str | CommandResult:
    if isinstance(arg, list):
        return _handle_run_context(arg, session)
    token = (
        cancellation_token
        if isinstance(cancellation_token, CancellationToken)
        else CancellationToken()
    )
    return _execute_run(str(arg or ""), session=session, cancellation_token=token)


def _run_gate_open(session: Any) -> bool:
    return os.environ.get("ARC_ALLOW_RUN") == "1" or bool(getattr(session, "allow_run", False))


def _provider_budget_config(session: Any) -> BudgetConfig:
    metadata = getattr(session, "metadata", {}) or {}
    raw = metadata.get("provider_budget")
    if isinstance(raw, dict):
        return BudgetConfig.model_validate(raw)
    return BudgetConfig(first_launch_confirmed=True)


def _preflight_provider_backed_run(session: Any, prompt: str) -> None:
    client = AnthropicClient()
    capability = client.capabilities()
    model = str(
        (getattr(session, "metadata", {}) or {}).get("provider_model") or capability.default_model
    )
    enforcer = BudgetEnforcer(_provider_budget_config(session), BudgetState())
    preflight_with_estimator(
        enforcer,
        provider_capability=capability,
        request_model=model,
        request_messages=[{"role": "user", "content": prompt}],
        provider_id=capability.provider_id,
        run_active=True,
        workflow_active=False,
    )


def _emit(ctx: Any, name: str, payload: dict[str, Any]) -> None:
    emit = getattr(ctx, "emit_event", None)
    if callable(emit):
        emit(name, payload)


def _render_run_result(result: Any) -> str:
    if hasattr(result, "render"):
        return str(result.render())
    if isinstance(result, dict):
        output = result.get("results", [])
        summary = f"Run completed: status={result.get('status')}, "
        summary += f"tasks={result.get('total_tasks', 0)}, "
        summary += f"cost=${result.get('total_cost_usd', 0):.4f}"
        if output:
            summary += f"\nOutput: {output[0].get('output', '')}"
        return summary
    return str(result)


def _result_summary(result: Any) -> dict[str, Any]:
    if hasattr(result, "summary"):
        return dict(result.summary())
    if isinstance(result, dict):
        return {
            "status": result.get("status"),
            "total_tasks": result.get("total_tasks", 0),
            "completed_tasks": result.get("completed_tasks", 0),
        }
    return {"type": type(result).__name__}


def _make_runner(config: Any, cancellation_token: CancellationToken) -> Any:
    parameters = inspect.signature(SwarmGraphRunner).parameters
    accepts_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())
    kwargs: dict[str, Any] = {}
    if "cancellation_token" in parameters or accepts_kwargs:
        kwargs["cancellation_token"] = cancellation_token
    if "config" in parameters:
        return SwarmGraphRunner(config=config, **kwargs)
    return SwarmGraphRunner(config, **kwargs)


def _run_runner(
    runner: Any,
    prompt: str,
    cancellation_token: CancellationToken,
    on_progress: Callable[[dict[str, Any]], None],
) -> Any:
    parameters = inspect.signature(runner.run).parameters
    kwargs: dict[str, Any] = {}
    if "cancellation_token" in parameters:
        kwargs["cancellation_token"] = cancellation_token
    if "on_progress" in parameters:
        kwargs["on_progress"] = on_progress
    return runner.run(prompt=prompt, **kwargs)


def _provider_client_for_run(runtime: Any) -> Any:
    if runtime is not None and hasattr(runtime, "complete") and hasattr(runtime, "stream"):
        return runtime
    return AnthropicClient()


def _run_provider_turn(
    *,
    session: Any,
    prompt: str,
    cancellation_token: CancellationToken,
    event_sink: Any,
    runtime: Any,
) -> Any:
    client = _provider_client_for_run(runtime)
    capability = (
        client.capabilities()
        if hasattr(client, "capabilities")
        else AnthropicClient().capabilities()
    )
    model = str(
        (getattr(session, "metadata", {}) or {}).get("provider_model") or capability.default_model
    )
    manager = TurnManager(
        client,
        model=model,
        event_sink=lambda name, payload: _emit(event_sink, name, payload),
        tool_registry=default_tool_registry() if getattr(session, "tools_enabled", False) else None,
    )
    return _run_coro_sync(manager.run_turn(session, prompt, cancellation_token=cancellation_token))


def _execute_run(
    prompt: str,
    *,
    session: Any,
    cancellation_token: CancellationToken,
    event_sink: Any = None,
    runtime: Any = None,
) -> CommandResult:
    """Single source of truth for /run gate, cancellation, and events."""
    prompt = prompt.strip()
    runtime_mode = RuntimeMode.from_legacy(getattr(session, "runtime_mode", RuntimeMode.FAKE))
    capability = default_runtime_registry().get(runtime_mode)
    if runtime_mode is RuntimeMode.PROVIDER_BACKED and not getattr(
        session, "allow_paid_calls", False
    ):
        return CommandResult(
            state="blocked",
            reason="paid_calls_disabled",
            remediation="Set allow_paid_calls before using provider_backed runtime mode.",
            metadata=capability.model_dump(mode="json"),
        )
    if not _run_gate_open(session):
        return CommandResult(
            state="blocked",
            reason="gate_closed",
            remediation="Set ARC_ALLOW_RUN=1 or enable session allow_run.",
        )
    if not prompt:
        return CommandResult(
            state="blocked", reason="missing_prompt", remediation="Usage: /run <prompt>"
        )

    started = time.monotonic()
    previous = signal.getsignal(signal.SIGINT)
    progress_stages: list[str] = []

    def _progress_metadata(elapsed_ms: int) -> dict[str, Any]:
        return {
            "elapsed_ms": elapsed_ms,
            "progress_event_count": len(progress_stages),
            "progress_stages": list(progress_stages),
        }

    def _on_sigint(signum: int, frame: Any) -> None:  # noqa: ARG001
        cancellation_token.cancel(CancellationReason.USER, "SIGINT")

    def _on_progress(payload: dict[str, Any]) -> None:
        stage = str(payload.get("stage", "unknown"))
        progress_stages.append(stage)
        _emit(event_sink, f"run.progress.{stage}", payload)

    signal.signal(signal.SIGINT, _on_sigint)
    try:
        _emit(
            event_sink,
            "run.started",
            {
                "prompt_chars": len(prompt),
                "runtime_mode": runtime_mode.value,
                "profile_id": getattr(session, "profile_id", "default"),
                "isolation_id": getattr(session, "isolation_id", "none"),
            },
        )
        cancellation_token.raise_if_cancelled()
        if runtime_mode is RuntimeMode.PROVIDER_BACKED:
            try:
                _preflight_provider_backed_run(session, prompt)
            except (BudgetExceeded, ConfirmationRequired) as exc:
                _emit(
                    event_sink,
                    "run.blocked.budget",
                    {"reason": type(exc).__name__, "detail": str(exc)},
                )
                elapsed_ms = int((time.monotonic() - started) * 1000)
                return CommandResult(
                    state="blocked",
                    reason="budget_preflight_failed",
                    remediation=str(exc),
                    metadata=_progress_metadata(elapsed_ms),
                )
            result = _run_provider_turn(
                session=session,
                prompt=prompt,
                cancellation_token=cancellation_token,
                event_sink=event_sink,
                runtime=runtime,
            )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _emit(
                event_sink,
                "run.completed",
                {
                    "elapsed_ms": elapsed_ms,
                    "result_summary": {"type": "provider_turn", "degraded": result.degraded},
                },
            )
            return CommandResult(
                state="degraded" if result.degraded else "present",
                output=result.content,
                reason=result.degraded_reason or "",
                metadata=_progress_metadata(elapsed_ms),
            )
        config = runtime if runtime is not None else SwarmGraphConfig(num_workers=3, max_rounds=1)
        runner = _make_runner(config, cancellation_token)
        result = _run_runner(runner, prompt, cancellation_token, _on_progress)
        if hasattr(session, "add_message"):
            session.add_message("user", prompt)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _emit(
            event_sink,
            "run.completed",
            {
                "elapsed_ms": elapsed_ms,
                "result_summary": _result_summary(result),
            },
        )
        return CommandResult(
            state="present",
            output=_render_run_result(result),
            metadata=_progress_metadata(elapsed_ms),
        )
    except Cancelled as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _emit(
            event_sink,
            "run.cancelled",
            {
                "reason": exc.reason.value,
                "detail": exc.detail,
                "elapsed_ms": elapsed_ms,
            },
        )
        return CommandResult(
            state="degraded",
            output=str(exc),
            reason="cancelled",
            metadata=_progress_metadata(elapsed_ms),
        )
    finally:
        signal.signal(signal.SIGINT, previous)


def _handle_run_context(args: list[str], ctx: Any) -> CommandResult:
    prompt = " ".join(args).strip()
    factory = getattr(ctx, "run_token_factory", None)
    token: CancellationToken = factory() if callable(factory) else CancellationToken()
    return _execute_run(
        prompt,
        session=ctx.session,
        cancellation_token=token,
        event_sink=ctx,
        runtime=getattr(ctx, "runtime", None),
    )


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


def cmd_runtime(arg: str, session: ChatSession) -> str:
    value = arg.strip()
    if not value:
        capability = default_runtime_registry().get(session.runtime_mode)
        return (
            f"Runtime: {RuntimeMode.from_legacy(session.runtime_mode).value}\n"
            f"Profile: {session.profile_id}\n"
            f"Isolation: {session.isolation_id}\n"
            f"Allow paid calls: {session.allow_paid_calls}\n"
            f"Cost source: {capability.cost_source_default}"
        )
    try:
        mode = RuntimeMode.from_legacy(value)
    except (TypeError, ValueError) as exc:
        return f"Blocked: {exc}"
    session.runtime_mode = mode
    session.allow_paid_calls = mode is RuntimeMode.PROVIDER_BACKED
    return f"Runtime mode: {mode.value}"


def cmd_tools(arg: str, session: ChatSession) -> str:
    parts = arg.strip().split()
    subcommand = parts[0] if parts else "list"
    registry = default_tool_registry()
    all_tools = registry.list_tools()
    if subcommand == "list":
        allowed = session.available_tools or all_tools
        lines = [f"Tools enabled: {session.tools_enabled}", "Available tools:"]
        for name in all_tools:
            marker = "enabled" if name in allowed else "disabled"
            lines.append(f"  {name} ({marker})")
        return "\n".join(lines)
    if subcommand == "enable":
        if len(parts) > 1:
            requested = parts[1:]
            unknown = [name for name in requested if name not in all_tools]
            if unknown:
                return f"Blocked: unknown tools: {', '.join(unknown)}"
            session.available_tools = requested
        session.tools_enabled = True
        return "Tools enabled."
    if subcommand == "disable":
        session.tools_enabled = False
        if len(parts) > 1:
            disabled = set(parts[1:])
            current = session.available_tools or all_tools
            session.available_tools = [name for name in current if name not in disabled]
            session.tools_enabled = bool(session.available_tools)
            return f"Disabled tools: {', '.join(parts[1:])}"
        return "Tools disabled."
    return "Usage: /tools list|enable [tool ...]|disable [tool ...]"


def _render_adapter_result(result: SlashAdapterResult) -> CommandResult:
    return CommandResult(
        state=result.state,
        output=result.text,
        reason=result.data.get("reason", "") if isinstance(result.data, dict) else "",
        metadata=result.data,
    )


def cmd_status(_arg: str, session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_status(session))


def cmd_doctor(_arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_doctor_summary())


def cmd_sandbox(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "doctor"
    if subcommand == "doctor":
        return _render_adapter_result(render_sandbox_doctor())
    if subcommand == "run":
        return _render_adapter_result(render_sandbox_run(arg))
    return CommandResult(state="blocked", output="Usage: /sandbox doctor", reason="invalid_usage")


def cmd_policy(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "explain":
        return _render_adapter_result(render_policy_explain(rest))
    if subcommand == "list":
        return _render_adapter_result(render_policy_list())
    if subcommand == "show":
        return _render_adapter_result(render_policy_show(rest))
    return CommandResult(
        state="blocked",
        output="Usage: /policy explain [--policy NAME] -- <cmd...>|list|show <name>",
        reason="invalid_usage",
    )


def cmd_runs(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "list":
        return _render_adapter_result(render_runs_list())
    if subcommand in {"show", "get"}:
        return _render_adapter_result(render_run_show(rest))
    if subcommand == "status":
        return _render_adapter_result(render_run_status(rest))
    return _render_adapter_result(render_run_show(arg))


def cmd_read(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_read(arg))


def cmd_search(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_search(arg))


def cmd_audit(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "list":
        limit = 20
        if rest and rest.isdigit():
            limit = int(rest)
        return _render_adapter_result(render_audit_list(limit=limit))
    if subcommand == "verify":
        return _render_adapter_result(render_audit_verify(rest))
    return CommandResult(
        state="blocked",
        output="Usage: /audit [list [limit]]|verify <run_id>",
        reason="invalid_usage",
    )


def cmd_task(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "list":
        status_filter = None
        limit = 50
        for token in rest.split():
            if token.startswith("--status="):
                status_filter = token.split("=", 1)[1]
            elif token.startswith("--limit="):
                limit = int(token.split("=", 1)[1])
        return _render_adapter_result(render_task_list(status_filter=status_filter, limit=limit))
    if subcommand == "status":
        return _render_adapter_result(render_task_status(rest))
    return CommandResult(
        state="blocked",
        output="Usage: /task [list [--status S] [--limit N]]|status <task_id>",
        reason="invalid_usage",
    )


def cmd_providers_status(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_providers_status())


def cmd_mcp_status(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_mcp_status())


class SlashCommandHandler:
    """Handler that routes slash commands through the unified registry."""

    def __init__(
        self, runner: Any = None, progress_sink: Callable[[str, dict[str, Any]], None] | None = None
    ) -> None:
        self.runner = runner
        self.progress_sink = progress_sink
        self.cancellation_token: CancellationToken = CancellationToken()
        self.events: list[tuple[str, dict[str, Any]]] = []
        self._registry = _build_registry()

    def emit_event(self, name: str, payload: dict[str, Any]) -> None:
        copied = dict(payload)
        self.events.append((name, copied))
        if self.progress_sink and (
            name.startswith("run.progress.")
            or name in {"run.started", "run.completed", "run.cancelled"}
        ):
            self.progress_sink(name, dict(copied))

    def run_token_factory(self) -> CancellationToken:
        return self.cancellation_token.child()

    def handle(self, command: str, session: ChatSession) -> str | CommandResult | None:
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
            return _execute_run(
                arg,
                session=session,
                cancellation_token=self.run_token_factory(),
                event_sink=self,
                runtime=self.runner,
            )
        try:
            result = defn.handler(arg, session)
            if name == "sandbox" and isinstance(result, CommandResult):
                audit = (
                    result.metadata.get("audit_event")
                    if isinstance(result.metadata, dict)
                    else None
                )
                if isinstance(audit, dict):
                    self.emit_event(
                        "sandbox.denied" if result.state == "denied" else "sandbox.command",
                        audit,
                    )
            return result
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised by regression tests with monkeypatches
            return CommandResult(
                state="error",
                output=f"Error running /{name}: {exc}",
                reason=type(exc).__name__,
                metadata={"command": name, "error_type": type(exc).__name__},
            )
