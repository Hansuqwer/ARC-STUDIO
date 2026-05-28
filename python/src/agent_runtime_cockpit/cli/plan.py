"""Plan CLI commands for Plan/Apply/Review loop (Phase 75).

Provides ``arc plan explain`` to show what a command or sequence of
commands would do under the sandbox policy, including classification,
file intents, approval requirements, and known/unknown cost/risk.
"""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.plan import build_plan, persist_plan_audit_event
from ..security.sandbox import resolve_sandbox_policy
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import plan_app


@plan_app.command(
    "explain",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def plan_explain(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain what a command or sequence would do under the sandbox policy.

    Returns a plan envelope with classification, file intents, sandbox
    decisions, approval requirements, and known/unknown cost/risk estimates.
    No commands are executed.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    raw_args = list(ctx.args)

    if not raw_args:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing command"), json_output)
        raise typer.Exit(2)

    try:
        policy_model = resolve_sandbox_policy(policy, ws)
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)

    commands = _parse_command_sequence(raw_args)
    plan = build_plan(commands, policy_model)
    audit_path = persist_plan_audit_event(plan, ws)

    payload = plan.model_dump(mode="json")
    payload["audit_path"] = str(audit_path)
    _out(ok(payload, workspace=str(ws)), json_output)


def _parse_command_sequence(args: list[str]) -> list[list[str]]:
    """Parse a flat argument list into a sequence of commands.

    Commands are separated by ``--`` tokens. If no ``--`` is present,
    the entire argument list is treated as a single command.
    """
    commands: list[list[str]] = []
    current: list[str] = []
    for arg in args:
        if arg == "--":
            if current:
                commands.append(current)
            current = []
        else:
            current.append(arg)
    if current:
        commands.append(current)
    return commands
