from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import signal
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar

from ..budget.schema import (
    BudgetConfig,
    BudgetEnforcer,
    BudgetExceeded,
    BudgetState,
    ConfirmationRequired,
)
from ..providers import AnthropicClient, OpenAICompatibleClient, preflight_with_estimator
from ..providers.registry import get as get_provider_client
from ..runtime.agent_loop import AgentLoop
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
            name="session",
            help_text="Show current session summary",
            category="session",
            handler=cmd_session,
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
            name="model",
            help_text="Provider/model selector: /model [list] | use <provider[:model]>",
            category="provider",
            handler=cmd_model,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/model [list] | use <provider[:model]>",
            subcommands=["list", "use"],
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
            name="agent",
            help_text="Run autonomous provider-backed coding agent loop",
            category="runtime",
            handler=cmd_agent,
            gates_required=[],
            mode_required=[],
            renders=["present", "blocked", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/agent <task>",
        )
    )
    registry.register(
        CommandDef(
            name="runtime",
            help_text="Engine selector: /runtime [list] | use <id>  (swarmgraph, langgraph, …)",
            category="runtime",
            handler=cmd_runtime,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/runtime [list] | use <engine_id>",
            subcommands=["list", "use"],
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
            help_text="Execution-mode switcher: /mode [fake|gated_local|provider_backed]",
            category="runtime",
            handler=cmd_mode,
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
            name="apply-diff",
            help_text="Diff preview → approve → apply: /apply-diff <file> [diff_text]",
            category="workspace",
            handler=cmd_apply_diff,
            gates_required=[],
            mode_required=[],
            renders=["present", "denied", "blocked"],
            requires_events=[],
            privileged=False,
            trust_required="workspace",
            usage="/apply-diff <file> [diff_text]",
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

    # ── Budget ────────────────────────────────────────────────────────────
    registry.register(
        CommandDef(
            name="wallet",
            help_text="Show per-scope token budget snapshot",
            category="budget",
            handler=cmd_wallet,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/wallet",
        )
    )
    registry.register(
        CommandDef(
            name="budget",
            help_text="Show per-scope budget status",
            category="budget",
            handler=cmd_budget,
            gates_required=[],
            mode_required=[],
            renders=["present", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/budget",
        )
    )
    registry.register(
        CommandDef(
            name="expand",
            help_text="Re-inject a virtualized tool output handle into the conversation",
            category="context",
            handler=cmd_expand,
            gates_required=[],
            mode_required=[],
            renders=["present", "not_found", "degraded"],
            requires_events=[],
            privileged=False,
            trust_required="user",
            usage="/expand <handle-prefix>",
        )
    )

    return registry


# ── Command handler implementations ────────────────────────────────────────


def cmd_agent(arg: str, session: ChatSession) -> CommandResult:
    task = arg.strip()
    if not task:
        return CommandResult(
            state="blocked", reason="missing_task", remediation="Usage: /agent <task>"
        )
    session.runtime_mode = RuntimeMode.PROVIDER_BACKED
    session.allow_paid_calls = True
    session.tools_enabled = True
    return _execute_agent(
        task,
        session=session,
        cancellation_token=CancellationToken(),
        event_sink=None,
        runtime=None,
    )


def _execute_agent(
    task: str,
    *,
    session: ChatSession,
    cancellation_token: CancellationToken,
    event_sink: Any = None,
    runtime: Any = None,
) -> CommandResult:
    task = task.strip()
    if not task:
        return CommandResult(
            state="blocked", reason="missing_task", remediation="Usage: /agent <task>"
        )
    client = _provider_client_for_run(runtime, session)
    capability = (
        client.capabilities()
        if hasattr(client, "capabilities")
        else AnthropicClient().capabilities()
    )
    model = str(
        (getattr(session, "metadata", {}) or {}).get("provider_model") or capability.default_model
    )
    try:
        _preflight_provider_backed_run(session, task, client)
    except (BudgetExceeded, ConfirmationRequired) as exc:
        return CommandResult(
            state="blocked", reason="budget_preflight_failed", remediation=str(exc)
        )
    manager = TurnManager(
        client,
        model=model,
        event_sink=lambda name, payload: _emit(event_sink, name, payload),
        tool_registry=default_tool_registry(Path.cwd()),
    )
    loop = AgentLoop(manager, session)
    result = _run_coro_sync(loop.run(task, cancellation_token))
    _store_context_metadata(session, capability, result.cost_summary)
    return CommandResult(
        state="degraded" if result.degraded else "present",
        output=result.content,
        reason=result.degraded_reason or "",
        metadata={"turns": result.turns, "cost_summary": result.cost_summary},
    )


def cmd_help(_arg: str, _session: ChatSession) -> str:
    registry = get_registry()
    # Ordered command palette grouped by surface area.
    # All entries are implemented; none are deferred or design-only in this list.
    groups: dict[str, list[str]] = {
        "session": [
            "help",
            "version",
            "clear",
            "summary",
            "session",
            "sessions",
            "history",
            "alias",
            "exit",
        ],
        "run": [
            "run",
            "agent",
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
        "providers": ["providers", "model"],
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
        "Recommended entrypoint: arch-studio-cli (same REPL as arc studio chat).",
        "Workflow: /status → /context pack <task> → /plan → /agent <task> → /test -- <cmd> → /diff.",
        "Type a message to query the SwarmGraph runner.",
        "Note: OpenCode/Claude Code style agent parity is a target, not yet achieved.",
    ]
    return "\n".join(lines)


def cmd_clear(_arg: str, session: ChatSession) -> str:
    session.history.clear()
    return "Session history cleared."


def cmd_model(arg: str, session: ChatSession) -> CommandResult:
    """Provider/model selector: /model [list] | /model use <provider[:model]>.

    Switches the in-session provider/model. Never enables paid calls automatically.
    Switching is only effective if the provider's key env var is set.
    """
    import os

    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    md = session.metadata or {}

    def _provider_catalog() -> dict:
        try:
            from ..providers import bundled_openai_compatible_providers

            return bundled_openai_compatible_providers()
        except Exception:  # noqa: BLE001
            return {}

    def _env_for_provider(pid: str) -> str:
        safe = pid.replace("-", "_").upper()
        for suffix in ("API_KEY", "TOKEN", "KEY"):
            cand = f"ARC_{safe}_{suffix}"
            if cand in os.environ:
                return cand
            # legacy / explicit mappings
        mapping = {
            "9router": "NINEROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "crofai": "CROFAI_API_KEY",
        }
        return mapping.get(pid, f"ARC_{safe}_API_KEY")

    if subcommand in ("", "list"):
        catalog = _provider_catalog()
        active_provider = str(md.get("provider") or "none")
        active_model = str(md.get("provider_model") or "unknown")
        lines = [f"Active: {active_provider} / {active_model}", ""]
        lines.append(f"  {'Provider':<20} {'Configured':<12} Default model")
        for pid, cfg in catalog.items():
            key_var = _env_for_provider(pid)
            configured = "yes" if os.environ.get(key_var) else "no"
            default_model = str(getattr(cfg, "default_model", "?") or "?")
            lines.append(f"  {pid:<20} {configured:<12} {default_model[:40]}")
        lines += [
            "",
            "Use: /model use <provider[:model]>",
            "Paid calls: unchanged. Enable separately.",
        ]
        return CommandResult(state="present", output="\n".join(lines))

    if subcommand == "use":
        spec = rest.strip()
        if not spec:
            return CommandResult(
                state="blocked",
                output="Usage: /model use <provider[:model]>",
                reason="missing_spec",
            )
        if ":" in spec:
            provider_id, model_id = spec.split(":", 1)
        else:
            provider_id, model_id = spec, ""
        provider_id = provider_id.strip()
        key_var = _env_for_provider(provider_id)
        if not os.environ.get(key_var):
            return CommandResult(
                state="degraded",
                output=(
                    f"Provider {provider_id!r} key not set ({key_var}).\n"
                    "Model selection stored but provider-backed calls will fail until key is set.\n"
                    "Paid calls: unchanged."
                ),
                reason="no_key",
                metadata={"provider": provider_id, "key_var": key_var},
            )
        if session.metadata is None:
            session.metadata = {}
        session.metadata["provider"] = provider_id
        if model_id:
            session.metadata["provider_model"] = model_id
        else:
            # use catalog default
            catalog = _provider_catalog()
            cfg = catalog.get(provider_id)
            if cfg:
                session.metadata["provider_model"] = str(getattr(cfg, "default_model", "") or "")
        return CommandResult(
            state="present",
            output=(
                f"Provider: {session.metadata['provider']}\n"
                f"Model: {session.metadata.get('provider_model') or 'default'}\n"
                "Paid calls: unchanged. Execution mode: unchanged."
            ),
        )

    return CommandResult(
        state="blocked",
        output="Usage: /model [list] | use <provider[:model]>",
        reason="invalid_subcommand",
    )


def cmd_session(_arg: str, session: ChatSession) -> CommandResult:
    """Show the current session summary (id, mode, runtime, message count)."""
    runtime = RuntimeMode.from_legacy(session.runtime_mode).value
    body = (
        f"Session: {session.id}\n"
        f"Mode: {session.mode}\n"
        f"Runtime: {runtime}\n"
        f"Messages: {len(session.history)}\n"
        f"Created: {session.created_at[:19]}"
    )
    return CommandResult(state="present", output=body)


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


def _preflight_provider_backed_run(session: Any, prompt: str, runtime: Any = None) -> None:
    client = _provider_client_for_run(runtime, session)
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


def _detect_provider_name() -> str | None:
    explicit = os.environ.get("ARC_DEFAULT_PROVIDER")
    if explicit:
        return explicit
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def _provider_client_for_run(runtime: Any, session: Any = None) -> Any:
    if runtime is not None and hasattr(runtime, "complete") and hasattr(runtime, "stream"):
        return runtime
    metadata = getattr(session, "metadata", {}) or {}
    provider_name = str(metadata.get("provider") or _detect_provider_name() or "anthropic")
    try:
        return get_provider_client(provider_name)
    except Exception:
        if provider_name == "openai":
            return OpenAICompatibleClient(vendor="openai")
        return AnthropicClient()


def _run_provider_turn(
    *,
    session: Any,
    prompt: str,
    cancellation_token: CancellationToken,
    event_sink: Any,
    runtime: Any,
) -> Any:
    client = _provider_client_for_run(runtime, session)
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
        tool_registry=default_tool_registry(Path.cwd())
        if getattr(session, "tools_enabled", False)
        else None,
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
            client = _provider_client_for_run(runtime, session)
            capability = client.capabilities() if hasattr(client, "capabilities") else None
            try:
                _preflight_provider_backed_run(session, prompt, runtime)
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
            if result.response is not None:
                _store_context_metadata(
                    session,
                    capability,
                    {
                        "available": result.response.usage.available,
                        "input_tokens": result.response.usage.input_tokens,
                        "output_tokens": result.response.usage.output_tokens,
                        "cache_creation_input_tokens": result.response.usage.cache_creation_input_tokens,
                        "cache_read_input_tokens": result.response.usage.cache_read_input_tokens,
                    },
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


def _store_context_metadata(session: Any, capability: Any, cost_summary: dict[str, Any]) -> None:
    if not cost_summary.get("available"):
        return
    max_context = int(getattr(capability, "max_context_tokens", 0) or 0)
    if max_context <= 0:
        return
    input_tokens = int(cost_summary.get("input_tokens") or 0)
    cache_write = int(cost_summary.get("cache_creation_input_tokens") or 0)
    cache_read = int(cost_summary.get("cache_read_input_tokens") or 0)
    used = input_tokens + cache_write + cache_read
    pct = round((used / max_context) * 100, 2) if max_context else None
    metadata = getattr(session, "metadata", None)
    if isinstance(metadata, dict):
        metadata["last_context"] = {
            "available": True,
            "used_tokens": used,
            "max_context_tokens": max_context,
            "usage_pct": pct,
            "source": "provider_usage",
        }


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


def cmd_mode(arg: str, session: ChatSession) -> str:
    """Execution-mode switcher: /mode [fake | gated_local | gated | provider_backed | live].

    Changes the execution mode (FAKE/GATED_LOCAL/PROVIDER_BACKED). Use /runtime for engine.
    """
    value = arg.strip()
    if not value:
        return (
            f"Execution mode: {RuntimeMode.from_legacy(session.runtime_mode).value}\n"
            "Values: fake | gated_local (gated) | provider_backed (live)\n"
            "Engine selection: /runtime"
        )
    try:
        mode = RuntimeMode.from_legacy(value)
    except (TypeError, ValueError) as exc:
        return f"Blocked: {exc}"
    session.runtime_mode = mode
    session.allow_paid_calls = mode is RuntimeMode.PROVIDER_BACKED
    return f"Runtime mode: {mode.value}"


def cmd_runtime(arg: str, session: ChatSession) -> CommandResult:
    """Engine selector: /runtime [list] | /runtime use <id>.

    Lists or selects the execution engine (swarmgraph, langgraph, lmarena, …).
    Selecting an engine does NOT change the execution mode (FAKE/GATED_LOCAL/PROVIDER_BACKED)
    and does NOT enable paid calls. Use /mode for execution-mode switching.
    """
    from pathlib import Path

    from ..adapters.registry import default_registry

    parts = arg.strip().split(maxsplit=1)
    subcommand = parts[0] if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    ws = Path.cwd()
    active = str((session.metadata or {}).get("runtime_adapter") or "swarmgraph")

    if subcommand in ("", "list"):
        try:
            from ..orchestration import runtime_router

            reports = runtime_router.list_runtimes(ws)
        except Exception as exc:  # noqa: BLE001
            return CommandResult(state="degraded", output=f"Runtime list unavailable: {exc}")
        lines = [
            f"Active engine: {active}",
            "",
            f"{'ID':<20} {'detected':<10} {'can_run':<10} {'paid':<6} availability",
        ]
        for r in reports:
            lines.append(
                f"  {r.runtime_id:<18} {'yes' if r.detected else 'no':<10}"
                f" {'yes' if r.can_run else 'no':<10} {'yes' if r.requires_paid_calls else 'no':<6}"
                f" {r.availability}"
            )
        lines += [
            "",
            "Use: /runtime use <id>",
            "Execution mode: /mode  Paid calls: /mode provider_backed",
        ]
        return CommandResult(state="present", output="\n".join(lines), metadata={"active": active})

    if subcommand == "use":
        engine_id = rest.strip()
        if not engine_id:
            return CommandResult(
                state="blocked", output="Usage: /runtime use <engine_id>", reason="missing_id"
            )
        registry = default_registry()
        adapter = registry.get(engine_id)
        if adapter is None:
            known = [a.adapter_id for a in registry.all()]
            return CommandResult(
                state="blocked",
                output=f"Unknown engine: {engine_id}. Known: {', '.join(known)}",
                reason="unknown_engine",
            )
        caps = adapter.capabilities()
        if session.metadata is None:
            session.metadata = {}
        session.metadata["runtime_adapter"] = engine_id
        state = "present" if caps.can_run else "degraded"
        note = (
            "ready"
            if caps.can_run
            else f"detected but not runnable — {adapter.capability_report(ws).reason or 'see /doctor'}"
        )
        paid_note = (
            " (requires paid calls)" if adapter.capability_report(ws).requires_paid_calls else ""
        )
        return CommandResult(
            state=state,
            output=(
                f"Active engine: {engine_id}\n"
                f"Status: {note}{paid_note}\n"
                "Execution mode unchanged. Paid calls unchanged."
            ),
            metadata={"engine": engine_id, "can_run": caps.can_run},
        )

    return CommandResult(
        state="blocked", output="Usage: /runtime [list] | use <id>", reason="invalid_subcommand"
    )


def cmd_tools(arg: str, session: ChatSession) -> str:
    parts = arg.strip().split()
    subcommand = parts[0] if parts else "list"
    registry = default_tool_registry()
    all_tools = registry.list_tools()
    if subcommand == "list":
        allowed = session.available_tools or all_tools
        lines = [f"Tools enabled: {session.tools_enabled}", "Available tools:"]
        handlers = {handler.name: handler for handler in registry.all_handlers()}
        for name in all_tools:
            marker = "enabled" if name in allowed else "disabled"
            handler = handlers.get(name)
            trust = getattr(handler, "output_trust_level", "unknown")
            kind = _tool_kind(name)
            lines.append(f"  {name} ({marker}, {kind}, trust={trust})")
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


def _tool_kind(name: str) -> str:
    if name in {"read_file", "list_directory", "get_current_time"}:
        return "read"
    if name in {"write_file", "edit_file", "create_file"}:
        return "write"
    if name == "bash":
        return "shell"
    return "tool"


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
            "Sandbox approval required\n"
            f"Command: {cmd_display}\n"
            f"Policy: {policy.name}\n"
            f"Classification: {decision.classification.value}\n"
            f"Reason: {decision.reason}\n"
            "Default: deny. Destructive and privileged commands remain hard-denied.\n"
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


def cmd_apply_diff(
    arg: str,
    session: ChatSession,
    *,
    confirm_fn: Any = None,
) -> CommandResult:
    """In-shell diff→preview→approve→apply. Denied in plan mode and untrusted workspace.

    Usage: /apply-diff <file> <diff_text>   (primarily called programmatically or via /agent output)
    confirm_fn: (prompt: str) -> bool — injectable for tests; defaults to stdin y/N.
    """
    from pathlib import Path

    # Gate: plan mode
    if session.mode == "plan":
        return CommandResult(
            state="denied", output="Apply denied in plan mode.", reason="plan_mode"
        )

    # Gate: workspace trust
    ws = Path.cwd()
    try:
        from ..security.trust import resolve_trust

        trust = resolve_trust(ws)
        if trust.level.value == "untrusted":
            return CommandResult(
                state="denied",
                output="Apply denied: workspace is untrusted. Trust the workspace first.",
                reason="untrusted_workspace",
            )
    except Exception:  # noqa: BLE001
        pass

    parts = arg.strip().split(maxsplit=1)
    if len(parts) < 1:
        return CommandResult(
            state="blocked", output="Usage: /apply-diff <file> [diff_text]", reason="missing_file"
        )
    file_arg = parts[0]
    diff_text = parts[1] if len(parts) > 1 else ""

    # Show diff preview via rendering.py diff_panel (rendered as text for the prompt)
    from .rendering import Renderer
    from rich.console import Console as _Console

    preview_console = _Console(record=True, width=100)
    preview_renderer = Renderer(preview_console, ascii_only=True)
    preview_renderer.print(preview_renderer.diff_panel(file_arg, diff_text))
    preview_text = preview_console.export_text()

    prompt_text = f"{preview_text}\nApply changes to {file_arg}? [y/N] "
    if confirm_fn is not None:
        confirmed = bool(confirm_fn(prompt_text))
    elif os.isatty(0):  # pragma: no cover — live path
        try:
            answer = input(prompt_text).strip().lower()
            confirmed = answer == "y"
        except (EOFError, KeyboardInterrupt):
            confirmed = False
    else:
        confirmed = False

    if not confirmed:
        return CommandResult(
            state="denied", output="Apply cancelled by user.", reason="user_declined"
        )

    return _render_adapter_result(render_apply(f"{file_arg} {diff_text}".strip()))


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
        # Optional approval callback (prompt: str) -> bool, used only for /sandbox.
        # Default None preserves the existing isatty()/non-interactive behavior.
        self.confirm_fn: Callable[[str], bool] | None = None

    def emit_event(self, name: str, payload: dict[str, Any]) -> None:
        copied = dict(payload)
        self.events.append((name, copied))
        if self.progress_sink and (
            name.startswith("run.progress.")
            or name.startswith("stream.chunk.")
            or name in {"run.started", "run.completed", "run.cancelled"}
            or name
            in {
                "turn.started",
                "turn.completed",
                "turn.cancelled",
                "tool.requested",
                "tool.executed",
                "tool.result.blocked",
            }
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
        if name == "agent":
            session.runtime_mode = RuntimeMode.PROVIDER_BACKED
            session.allow_paid_calls = True
            session.tools_enabled = True
            return _execute_agent(
                arg,
                session=session,
                cancellation_token=self.run_token_factory(),
                event_sink=self,
                runtime=self.runner,
            )
        try:
            if name == "sandbox":
                result = defn.handler(arg, session, confirm_fn=self.confirm_fn)
            elif name == "apply-diff":
                result = defn.handler(arg, session, confirm_fn=self.confirm_fn)
            else:
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


# ── Budget handlers ────────────────────────────────────────────────────────────


def cmd_wallet(_arg: str, session: ChatSession) -> CommandResult:
    """Show per-scope token budget snapshot."""
    from ..budget.wallet import TokenWallet

    enforcer = _session_budget_enforcer(session)
    if enforcer is None:
        return CommandResult(
            state="degraded", output="[wallet] No budget enforcer active in this session."
        )
    wallet = TokenWallet(enforcer)
    snap = wallet.snapshot()
    if snap.fail_closed_reason:
        return CommandResult(
            state="degraded", output=f"[wallet] Error reading budget: {snap.fail_closed_reason}"
        )
    lines: list[str] = []
    if snap.first_launch:
        lines.append("First-launch cap active ($1.00/run). Cap restores after first run.")
    header = "SCOPE          SPENT       CAP        REMAINING"
    lines.append(header)
    lines.append("-" * len(header))
    for scope_val, bal in snap.balances.items():
        line = f"{scope_val:<14} ${float(bal.spent_usd):>8.4f}  ${float(bal.cap_usd):>8.2f}  ${float(bal.remaining_usd):>8.4f}"
        if bal.cache_hit_rate > 0:
            line += f"  cache:{bal.cache_hit_rate:.0%}"
        lines.append(line)
    # Per-model annotations: free tier, tokenizer warning, deprecation, auto_route
    provider_id = (session.metadata or {}).get("provider")
    model_id = (session.metadata or {}).get("provider_model")
    if provider_id and model_id:
        try:
            from ..budget.wallet import model_display_notes
            from ..providers.openai_compatible import OpenAICompatibleClient

            caps = OpenAICompatibleClient(vendor=provider_id).capabilities()
            rates = (caps.cost_rates or {}).get(model_id)
            if rates:
                notes = model_display_notes(model_id, rates)
                if notes:
                    lines.append("")
                    lines.extend(notes)
        except Exception:
            pass
    return CommandResult(state="present", output="\n".join(lines))


def cmd_budget(_arg: str, session: ChatSession) -> CommandResult:
    """Show per-scope budget status."""
    from ..budget.schema import BudgetScope as _BS

    enforcer = _session_budget_enforcer(session)
    if enforcer is None:
        return CommandResult(state="degraded", output="[budget] No budget enforcer active.")
    lines: list[str] = []
    for scope in _BS:
        if scope is _BS.PROVIDER_DAY:
            continue
        try:
            cap = enforcer._config.effective_cap(scope, None)
            spent = enforcer._state.spend_for(scope, None)
            remaining = max(0, float(cap - spent))
            pct = float(spent / cap * 100) if cap > 0 else 0.0
            lines.append(
                f"{scope.value}: ${float(spent):.4f} / ${float(cap):.2f} ({pct:.0f}%) — ${remaining:.4f} remaining"
            )
        except Exception:
            lines.append(f"{scope.value}: (unavailable)")
    return (
        CommandResult(state="present", output="\n".join(lines))
        if lines
        else CommandResult(state="degraded", output="[budget] No budget state available.")
    )


def _session_budget_enforcer(session: ChatSession) -> BudgetEnforcer | None:
    """Extract or build a BudgetEnforcer from session metadata."""
    metadata = getattr(session, "metadata", {}) or {}
    raw = metadata.get("provider_budget")
    if isinstance(raw, dict):
        try:
            return BudgetEnforcer(BudgetConfig.model_validate(raw), BudgetState())
        except Exception:
            return None
    # If first_launch_confirmed in metadata, build a default enforcer for display
    if metadata.get("budget_enforcer_active"):
        return BudgetEnforcer(BudgetConfig(first_launch_confirmed=True), BudgetState())
    return None


# ── Handle expand handler ──────────────────────────────────────────────────────


def cmd_expand(arg: str, session: ChatSession) -> CommandResult:
    """Re-inject a virtualized tool output handle into the conversation."""
    from ..budget.storage import SQLiteWALStorage
    from ..context.handles import HandleAmbiguous, HandleCorrupt, HandleNotFound, HandleStore

    prefix = arg.strip()
    if not prefix:
        return CommandResult(
            state="blocked",
            reason="missing_prefix",
            remediation="Usage: /expand <handle-prefix>",
        )

    try:
        storage = SQLiteWALStorage()
        hs = HandleStore(storage)
        content = hs.expand(prefix)
    except HandleNotFound:
        return CommandResult(
            state="not_found",
            output=f"[handle {prefix!r} not found; rerun the originating tool call]",
        )
    except HandleAmbiguous as exc:
        return CommandResult(state="blocked", reason=str(exc))
    except HandleCorrupt as exc:
        return CommandResult(state="degraded", reason=str(exc))

    text = content.decode(errors="replace")
    if hasattr(session, "add_message"):
        session.add_message("user", text)

    return CommandResult(
        state="present",
        output=f"[expanded {len(content)} bytes from handle {prefix!r}]",
        metadata={"handle_prefix": prefix, "bytes": len(content)},
    )
