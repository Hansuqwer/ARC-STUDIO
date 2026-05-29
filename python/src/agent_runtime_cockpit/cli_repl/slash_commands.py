from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import signal
import shlex
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
    _parse_sandbox_run,
    render_audit_list,
    render_audit_verify,
    render_battle_list,
    render_battle_show,
    render_config_show,
    render_config_validate,
    render_context_pack,
    render_dashboard,
    render_apply,
    render_doctor_summary,
    render_diff,
    render_edit_apply,
    render_edit_plan,
    render_events_watch,
    render_hitl_pending,
    render_hitl_respond,
    render_mcp_status,
    render_policy_explain,
    render_policy_list,
    render_policy_show,
    render_providers_add,
    render_providers_list,
    render_providers_remove,
    render_providers_summary,
    render_providers_test,
    render_replay,
    render_run_show,
    render_run_status,
    render_runs_list,
    render_sandbox_doctor,
    render_sandbox_run,
    render_read,
    render_search,
    render_status,
    render_test,
    render_task_list,
    render_task_status,
    render_workspace_trust_status,
)
from .aliases import get_alias, list_aliases, remove_alias, set_alias
from .cancellation import CancellationReason, CancellationToken, Cancelled
from .commands import CommandDef, get_registry
from .pipeline import ChainOperator, has_chain_operator, parse_command_chain
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
            help_text="List, resume, or search saved sessions",
            category="session",
            handler=cmd_sessions,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/sessions [list]|resume <session_id>|search <query>",
            subcommands=["list", "resume", "search"],
        )
    )
    registry.register(
        CommandDef(
            name="history",
            help_text="Show or search recent messages",
            category="session",
            handler=cmd_history,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/history [N]|search <query>",
            subcommands=["search"],
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
            name="edit",
            help_text="Safety-gated edit loop: /edit plan|apply|approve",
            category="workspace",
            handler=cmd_edit,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked", "denied"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/edit plan|apply --path PATH --content TEXT [--approve] | approve <plan-id> <token>",
            subcommands=["plan", "apply", "approve"],
        )
    )
    registry.register(
        CommandDef(
            name="diff",
            help_text="Show saved edit-plan metadata: /diff --plan-id ID",
            category="workspace",
            handler=cmd_diff,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked", "denied"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/diff --plan-id ID",
        )
    )
    registry.register(
        CommandDef(
            name="apply",
            help_text="Apply a guarded edit plan: /apply --plan-id ID --content TEXT --approve",
            category="workspace",
            handler=cmd_apply,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked", "denied"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/apply --path PATH --content TEXT --approve | --plan-id ID --content TEXT --approval-token TOKEN",
        )
    )
    registry.register(
        CommandDef(
            name="test",
            help_text="Run local test command through sandbox: /test -- <cmd...>",
            category="workspace",
            handler=cmd_test,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked", "denied", "error"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/test [--policy NAME] -- <cmd...>",
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
            help_text="Provider management: status, list, add, remove, test",
            category="providers",
            handler=cmd_providers,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded", "absent", "error"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/providers [list|add|remove|test]",
            subcommands=["list", "add", "remove", "test"],
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
    registry.register(
        CommandDef(
            name="dashboard",
            help_text="Show local ARC dashboard",
            category="workspace",
            handler=cmd_dashboard,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/dashboard",
        )
    )
    registry.register(
        CommandDef(
            name="alias",
            help_text="Manage REPL aliases: /alias list|show|set|remove|run",
            category="session",
            handler=cmd_alias,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/alias list|show <name>|set <name> <command>|remove <name>|run <name>",
            subcommands=["list", "show", "set", "remove", "run"],
        )
    )
    registry.register(
        CommandDef(
            name="hitl",
            help_text="Human approvals: /hitl pending|respond <id> <decision>",
            category="compliance",
            handler=cmd_hitl,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/hitl pending|respond <id> <approve|reject|modify|skip>",
            subcommands=["pending", "respond"],
        )
    )
    registry.register(
        CommandDef(
            name="context",
            help_text="Context utilities: /context pack <task>",
            category="workspace",
            handler=cmd_context,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/context pack <task>",
            subcommands=["pack"],
        )
    )
    registry.register(
        CommandDef(
            name="workspace",
            help_text="Workspace utilities: /workspace trust-status",
            category="workspace",
            handler=cmd_workspace,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/workspace trust-status",
            subcommands=["trust-status", "status"],
        )
    )
    registry.register(
        CommandDef(
            name="config",
            help_text="Configuration: /config show|validate",
            category="workspace",
            handler=cmd_config,
            gates_required=[],
            mode_required=[],
            renders=["present", "error"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/config show|validate",
            subcommands=["show", "validate"],
        )
    )
    registry.register(
        CommandDef(
            name="replay",
            help_text="Analyze replay capability: /replay <run_id>",
            category="runtime",
            handler=cmd_replay,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/replay <run_id>",
        )
    )
    registry.register(
        CommandDef(
            name="battle",
            help_text="Battle runs: /battle list|show <id>",
            category="runtime",
            handler=cmd_battle,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/battle list|show <id>",
            subcommands=["list", "show"],
        )
    )
    registry.register(
        CommandDef(
            name="events",
            help_text="Event buffer: /events watch [--since N] [--type T]",
            category="runtime",
            handler=cmd_events,
            gates_required=[],
            mode_required=[],
            renders=["present", "absent", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/events watch [--since N] [--type T]",
            subcommands=["watch"],
        )
    )

    return registry


# ── Command handler implementations ────────────────────────────────────────


def cmd_help(_arg: str, _session: ChatSession) -> str:
    registry = get_registry()
    # Ordered command palette grouped by surface area.
    # All entries are implemented; none are deferred or design-only in this list.
    groups: dict[str, list[str]] = {
        "session": ["help", "version", "clear", "summary", "sessions", "history", "alias", "exit"],
        "run": [
            "run",
            "runtime",
            "mode",
            "plan",
            "build",
            "auto",
            "runs",
            "replay",
            "battle",
            "events",
        ],
        "sandbox": ["sandbox"],
        "policy": ["policy"],
        "workspace": [
            "status",
            "doctor",
            "dashboard",
            "edit",
            "read",
            "search",
            "context",
            "workspace",
            "config",
        ],
        "providers": ["providers"],
        "tools": ["tools"],
        "audit": ["audit", "hitl"],
        "tasks": ["task"],
        "mcp": ["mcp"],
    }
    lines = [
        "ARC Studio — slash command palette",
        "━" * 48,
    ]
    for group, names in groups.items():
        lines.append(f"\n  {group.upper()}")
        for name in names:
            cmd = registry.get(name)
            if cmd is None:
                continue
            usage = cmd.usage or f"/{cmd.name}"
            lines.append(f"    {usage}")
            lines.append(f"      {cmd.help_text}")
    lines += [
        "",
        "━" * 48,
        "Type a message to query the SwarmGraph runner.",
        "Note: OpenCode/Claude Code style agent parity is a target, not yet achieved.",
    ]
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
    parts = _arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "resume":
        return _cmd_sessions_resume(rest, _session)
    if subcommand == "search":
        return _cmd_sessions_search(rest)
    if subcommand not in {"list", ""}:
        return "Usage: /sessions [list]|resume <session_id>|search <query>"
    sessions = ChatSession.list_sessions()
    if not sessions:
        return "No saved sessions."
    lines = ["Saved sessions:"]
    for s in sessions[:10]:
        n = len(s.history)
        lines.append(f"  {s.id[:16]}... - {n} msgs, {s.updated_at[:19]}")
    return "\n".join(lines)


def _cmd_sessions_resume(session_id: str, session: ChatSession) -> str:
    clean = session_id.strip()
    if not clean:
        return "Usage: /sessions resume <session_id>"
    loaded = ChatSession.load(clean)
    if loaded is None:
        return f"Session not found: {clean}"
    session.id = loaded.id
    session.mode = loaded.mode
    session.runtime_mode = loaded.runtime_mode
    session.profile_id = loaded.profile_id
    session.isolation_id = loaded.isolation_id
    session.allow_paid_calls = loaded.allow_paid_calls
    session.tools_enabled = loaded.tools_enabled
    session.max_tool_iterations = loaded.max_tool_iterations
    session.available_tools = loaded.available_tools
    session.created_at = loaded.created_at
    session.updated_at = loaded.updated_at
    session.history = list(loaded.history)
    session.metadata = dict(loaded.metadata)
    return f"Resumed session {session.id}: {len(session.history)} messages."


def _cmd_sessions_search(query: str) -> str:
    needle = query.strip().lower()
    if not needle:
        return "Usage: /sessions search <query>"
    matches: list[str] = []
    for saved in ChatSession.list_sessions():
        for message in saved.history:
            content = message.get("content", "")
            if needle in content.lower():
                role = message.get("role", "?")
                matches.append(f"  {saved.id[:16]}  [{role}] {content[:160]}")
                break
    if not matches:
        return "No matching sessions."
    return "Session matches:\n" + "\n".join(matches[:20])


def cmd_history(arg: str, session: ChatSession) -> str:
    parts = arg.strip().split(maxsplit=1)
    if parts[:1] == ["search"]:
        return _cmd_history_search(parts[1] if len(parts) > 1 else "", session)
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


def _cmd_history_search(query: str, session: ChatSession) -> str:
    needle = query.strip().lower()
    if not needle:
        return "Usage: /history search <query>"
    matches: list[str] = []
    for index, msg in enumerate(session.history, start=1):
        content = msg.get("content", "")
        if needle in content.lower():
            role = msg.get("role", "?")
            matches.append(f"{index}: [{role}] {content[:200]}")
    if not matches:
        return "No matching history messages."
    return "History matches:\n" + "\n".join(matches[:20])


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


def _command_succeeded(result: str | CommandResult | None) -> bool:
    if result is None:
        return False
    if isinstance(result, CommandResult):
        return result.state in {"present", "absent"} and result.reason not in {
            "invalid_usage",
            "gate_closed",
        }
    return not str(result).lower().startswith(("blocked", "error", "unknown"))


def _result_text(result: str | CommandResult | None) -> str:
    return str(result or "")


def cmd_status(_arg: str, session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_status(session))


def cmd_doctor(_arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_doctor_summary())


def cmd_sandbox(
    arg: str,
    _session: ChatSession,
    *,
    confirm_fn: Any = None,
) -> CommandResult:
    """Handle /sandbox subcommands.

    confirm_fn: callable(prompt: str) -> bool — injectable for tests.
    Defaults to a stdin y/n prompt.  Only used for approval_required decisions
    that are not DESTRUCTIVE/PRIVILEGED.  Destructive and privileged commands
    remain hard-denied regardless of any confirmation.
    """
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "doctor"
    if subcommand == "doctor":
        return _render_adapter_result(render_sandbox_doctor())
    if subcommand == "run":
        return _sandbox_run_with_approval(arg, confirm_fn=confirm_fn)
    return CommandResult(
        state="blocked", output="Usage: /sandbox doctor|run -- <cmd...>", reason="invalid_usage"
    )


def _sandbox_run_with_approval(
    arg: str,
    *,
    confirm_fn: Any = None,
) -> CommandResult:
    """Run sandbox command with optional interactive approval for approval_required decisions.

    DESTRUCTIVE and PRIVILEGED are always hard-denied — approve_decision() enforces this.
    NETWORK, INSTALL, UNKNOWN: prompt via confirm_fn when approval_required.
    """
    from pathlib import Path as _Path
    from ..security.sandbox import (
        CommandClassification,
        decide,
        resolve_sandbox_policy,
    )

    try:
        policy_name, _provider, command = _parse_sandbox_run(arg)
    except Exception as exc:
        return CommandResult(state="blocked", output=f"Blocked: {exc}", reason="parse_error")

    if not command:
        return CommandResult(
            state="blocked",
            output="Usage: /sandbox run [--policy NAME] -- <cmd...>",
            reason="invalid_usage",
        )

    try:
        ws = _Path.cwd()
        policy = resolve_sandbox_policy(policy_name, ws)
        decision = decide(command, policy)
    except (KeyError, ValueError) as exc:
        return CommandResult(state="blocked", output=f"Blocked: {exc}", reason="policy_error")

    _APPROVABLE = {
        CommandClassification.NETWORK,
        CommandClassification.INSTALL,
        CommandClassification.UNKNOWN,
    }

    pre_approved = False
    if (
        not decision.allowed
        and decision.approval_required
        and decision.classification in _APPROVABLE
    ):
        cmd_display = " ".join(command)
        prompt_text = (
            f"Command requires approval: {cmd_display}\n"
            f"Classification: {decision.classification.value}\n"
            "Approve? [y/N] "
        )
        if confirm_fn is not None:
            confirmed = bool(confirm_fn(prompt_text))
        elif os.isatty(0):  # pragma: no cover — live interactive path
            try:
                answer = input(prompt_text).strip().lower()
                confirmed = answer == "y"
            except (EOFError, KeyboardInterrupt):
                confirmed = False
        else:
            # Non-interactive (no TTY): delegate denial to the adapter
            # which emits the structured audit event with Classification info.
            return _render_adapter_result(render_sandbox_run(arg, pre_approved=False))

        if not confirmed:
            # Emit audit event for the denied-approval path via the adapter
            from ..security.sandbox import (
                build_audit_event,
                ensure_workspace_cwd,
                persist_sandbox_audit_event,
            )

            try:
                _cwd = ensure_workspace_cwd(_Path.cwd(), policy.workspace_root)
                _started = _ended = (
                    __import__("datetime")
                    .datetime.now(__import__("datetime").timezone.utc)
                    .isoformat()
                )
                audit = build_audit_event(
                    command=command,
                    cwd=_cwd,
                    decision=decision,
                    provider=_provider,
                    started_at=_started,
                    ended_at=_ended,
                    exit_code=None,
                    stdout_truncated=False,
                    stderr_truncated=False,
                    redaction_applied=False,
                )
                audit_path = persist_sandbox_audit_event(audit)
                audit["audit_path"] = str(audit_path)
            except Exception:  # noqa: BLE001
                audit = {}
            return CommandResult(
                state="denied",
                output=f"Sandbox denied (not approved): {cmd_display}",
                reason="approval_declined",
                metadata={
                    "classification": decision.classification.value,
                    "command": list(command),
                    "audit_event": audit,
                },
            )
        pre_approved = True

    return _render_adapter_result(render_sandbox_run(arg, pre_approved=pre_approved))


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


def cmd_edit(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "plan"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "plan":
        return _render_adapter_result(render_edit_plan(rest))
    if subcommand == "apply":
        return _render_adapter_result(render_edit_apply(rest))
    if subcommand == "approve":
        parts = rest.split(maxsplit=1)
        if len(parts) != 2:
            return CommandResult(
                state="blocked",
                output="Usage: /edit approve <plan-id> <token>",
                reason="invalid_usage",
            )
        try:
            from pathlib import Path
            from ..security.edit_loop import approve_edit_plan

            approval = approve_edit_plan(Path.cwd(), parts[0], parts[1])
        except (OSError, ValueError) as exc:
            return CommandResult(state="blocked", output=f"Blocked: {exc}")
        return CommandResult(
            state="present",
            output=f"Edit plan approved: {approval.plan_id}",
            metadata=approval.model_dump(mode="json"),
        )
    return CommandResult(
        state="blocked",
        output="Usage: /edit plan|apply --path PATH --content TEXT [--approve] | approve <plan-id> <token>",
        reason="invalid_usage",
    )


def cmd_diff(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_diff(arg))


def cmd_apply(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_apply(arg))


def cmd_test(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_test(arg))


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


def cmd_providers(arg: str, _session: ChatSession) -> CommandResult:
    """Handle /providers subcommands: list, add, remove, test, or default status."""
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "list":
        return _render_adapter_result(render_providers_list())
    if subcommand == "add":
        # Parse --provider and --api-key-env flags
        tokens = rest.split()
        provider = ""
        api_key_env = ""
        for i, token in enumerate(tokens):
            if token == "--provider" and i + 1 < len(tokens):
                provider = tokens[i + 1]
            elif token == "--api-key-env" and i + 1 < len(tokens):
                api_key_env = tokens[i + 1]
            elif token.startswith("--provider="):
                provider = token.split("=", 1)[1]
            elif token.startswith("--api-key-env="):
                api_key_env = token.split("=", 1)[1]
        if not provider or not api_key_env:
            return CommandResult(
                state="blocked",
                output="Usage: /providers add --provider <name> --api-key-env <env>",
                reason="invalid_usage",
            )
        return _render_adapter_result(render_providers_add(provider, api_key_env))
    if subcommand == "remove":
        if not rest:
            return CommandResult(
                state="blocked",
                output="Usage: /providers remove <account_id>",
                reason="invalid_usage",
            )
        return _render_adapter_result(render_providers_remove(rest.strip()))
    if subcommand == "test":
        if not rest:
            return CommandResult(
                state="blocked",
                output="Usage: /providers test <account_id>",
                reason="invalid_usage",
            )
        return _render_adapter_result(render_providers_test(rest.strip()))
    # Default: show status summary
    return _render_adapter_result(render_providers_summary())


def cmd_mcp_status(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_mcp_status())


def cmd_dashboard(arg: str, session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_dashboard(session))


def cmd_alias(arg: str, _session: ChatSession) -> CommandResult:
    try:
        tokens = shlex.split(arg.strip())
    except ValueError as exc:
        return CommandResult(state="blocked", output=f"Invalid alias syntax: {exc}")
    scope = "workspace"
    filtered: list[str] = []
    for token in tokens:
        if token == "--user":
            scope = "user"
        elif token == "--workspace":
            scope = "workspace"
        else:
            filtered.append(token)
    parts = filtered
    subcommand = parts[0] if parts else "list"
    if subcommand == "list":
        aliases = (
            [item for item in list_aliases() if item.scope == scope] if tokens else list_aliases()
        )
        if not aliases:
            return CommandResult(state="absent", output="No aliases configured.")
        lines = ["Aliases:"]
        for item in aliases:
            lines.append(f"  {item.name} ({item.scope}) -> {item.command}")
        return CommandResult(state="present", output="\n".join(lines))
    if subcommand == "show" and len(parts) >= 2:
        item = get_alias(parts[1])
        if item is None:
            return CommandResult(state="absent", output=f"Alias not found: {parts[1]}")
        return CommandResult(
            state="present", output=f"{item.name} ({item.scope}) -> {item.command}"
        )
    if subcommand == "set" and len(parts) >= 3:
        command = arg.split(parts[1], 1)[1].strip()
        command = command.replace("--user", "", 1).replace("--workspace", "", 1).strip()
        item = set_alias(parts[1], command, scope=scope)
        return CommandResult(state="present", output=f"Alias set: {item.name} -> {item.command}")
    if subcommand in {"remove", "delete"} and len(parts) >= 2:
        removed = remove_alias(parts[1], scope=scope)
        return CommandResult(
            state="present" if removed else "absent",
            output=f"Alias {'removed' if removed else 'not found'}: {parts[1]}",
        )
    if subcommand == "run" and len(parts) >= 2:
        item = get_alias(parts[1])
        if item is None:
            return CommandResult(state="absent", output=f"Alias not found: {parts[1]}")
        return CommandResult(
            state="present",
            output=f"Alias expansion: {item.name} -> {item.command}",
            metadata={"alias_expansion": item.command, "alias_name": item.name},
        )
    return CommandResult(
        state="blocked",
        output="Usage: /alias [--user|--workspace] list|show <name>|set <name> <command>|remove <name>|run <name>",
        reason="invalid_usage",
    )


def cmd_hitl(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "pending"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "pending":
        return _render_adapter_result(
            render_hitl_pending(include_expired="--include-expired" in rest)
        )
    if subcommand == "respond":
        return _render_adapter_result(render_hitl_respond(rest))
    return CommandResult(
        state="blocked",
        output="Usage: /hitl pending|respond <id> <decision>",
        reason="invalid_usage",
    )


def cmd_context(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    if parts and parts[0] == "pack":
        return _render_adapter_result(render_context_pack(parts[1] if len(parts) > 1 else ""))
    return CommandResult(
        state="blocked", output="Usage: /context pack <task>", reason="invalid_usage"
    )


def cmd_workspace(arg: str, _session: ChatSession) -> CommandResult:
    subcommand = arg.strip() or "trust-status"
    if subcommand in {"trust-status", "status"}:
        return _render_adapter_result(render_workspace_trust_status())
    return CommandResult(
        state="blocked", output="Usage: /workspace trust-status", reason="invalid_usage"
    )


def cmd_config(arg: str, _session: ChatSession) -> CommandResult:
    subcommand = arg.strip() or "show"
    if subcommand == "show":
        return _render_adapter_result(render_config_show())
    if subcommand == "validate":
        return _render_adapter_result(render_config_validate())
    return CommandResult(
        state="blocked", output="Usage: /config show|validate", reason="invalid_usage"
    )


def cmd_replay(arg: str, _session: ChatSession) -> CommandResult:
    return _render_adapter_result(render_replay(arg))


def cmd_battle(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""
    if subcommand == "list":
        return _render_adapter_result(render_battle_list(limit=int(rest) if rest.isdigit() else 20))
    if subcommand == "show":
        return _render_adapter_result(render_battle_show(rest))
    return CommandResult(
        state="blocked", output="Usage: /battle list|show <id>", reason="invalid_usage"
    )


def cmd_events(arg: str, _session: ChatSession) -> CommandResult:
    parts = arg.strip().split()
    if parts[:1] and parts[0] != "watch":
        return CommandResult(
            state="blocked",
            output="Usage: /events watch [--since N] [--type T]",
            reason="invalid_usage",
        )
    since = 20
    event_type = None
    index = 1 if parts[:1] == ["watch"] else 0
    while index < len(parts):
        if parts[index] == "--since" and index + 1 < len(parts):
            since = int(parts[index + 1])
            index += 2
            continue
        if parts[index].startswith("--since="):
            since = int(parts[index].split("=", 1)[1])
            index += 1
            continue
        if parts[index] == "--type" and index + 1 < len(parts):
            event_type = parts[index + 1]
            index += 2
            continue
        if parts[index].startswith("--type="):
            event_type = parts[index].split("=", 1)[1]
            index += 1
            continue
        return CommandResult(
            state="blocked",
            output="Usage: /events watch [--since N] [--type T]",
            reason="invalid_usage",
        )
    return _render_adapter_result(render_events_watch(since=since, event_type=event_type))


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
        self._alias_depth = 0

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
        if has_chain_operator(cmd):
            return self._handle_chain(cmd, session)
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
            if name == "alias" and isinstance(result, CommandResult):
                expansion = result.metadata.get("alias_expansion")
                if isinstance(expansion, str):
                    if self._alias_depth >= 5:
                        return CommandResult(
                            state="blocked",
                            output="Blocked: alias expansion depth exceeded",
                            reason="alias_recursion",
                        )
                    self._alias_depth += 1
                    try:
                        expanded = self.handle(expansion, session)
                    finally:
                        self._alias_depth -= 1
                    return CommandResult(
                        state=expanded.state if isinstance(expanded, CommandResult) else "present",
                        output=f"{result.output}\n{_result_text(expanded)}",
                        metadata={"alias_expansion": expansion},
                    )
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

    def _handle_chain(self, command: str, session: ChatSession) -> CommandResult:
        try:
            segments = parse_command_chain(command)
        except ValueError as exc:
            return CommandResult(
                state="blocked", output=f"Pipeline parse error: {exc}", reason="parse_error"
            )
        outputs: list[str] = []
        previous: str | CommandResult | None = None
        for segment in segments:
            previous_ok = _command_succeeded(previous) if previous is not None else True
            if segment.operator_before is ChainOperator.AND and not previous_ok:
                outputs.append(f"Skipped after &&: {segment.command}")
                continue
            if segment.operator_before is ChainOperator.OR and previous_ok:
                outputs.append(f"Skipped after ||: {segment.command}")
                continue
            current = segment.command
            if segment.operator_before is ChainOperator.PIPE:
                pipe_name = current.split(maxsplit=1)[0].lstrip("/").lower()
                if pipe_name not in {"search", "read", "status", "history"}:
                    blocked = CommandResult(
                        state="blocked",
                        output=f"Pipeline target blocked by adapter pipe contract: {current}",
                        reason="pipe_contract_denied",
                    )
                    previous = blocked
                    outputs.append(blocked.output)
                    continue
                current = f"{current} {shlex.quote(_result_text(previous))}"
            result = (
                self.handle(current, session)
                if current.startswith("/")
                else CommandResult(state="present", output=current)
            )
            previous = result
            outputs.append(_result_text(result))
        final_state = previous.state if isinstance(previous, CommandResult) else "present"
        return CommandResult(
            state=final_state,
            output="\n".join(part for part in outputs if part),
            metadata={"pipeline_segments": len(segments)},
        )
