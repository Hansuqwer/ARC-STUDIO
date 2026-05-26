from __future__ import annotations

from pathlib import Path

import typer

from ..protocol.event_envelope import ok
from ._app import console
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import batch_app


@batch_app.command("plan")
def batch_plan(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy for sandbox lines"),
    workspace: str | None = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Show deterministic expanded batch plan without executing."""
    from ..cli_repl.batch import build_batch_plan, render_plan_text

    ws = _workspace(workspace)
    plan = build_batch_plan(file.read_text(encoding="utf-8"), policy=policy, workspace=ws)
    if json_output:
        _out(ok(plan.model_dump(mode="json")), True)
        return
    console.print(render_plan_text(plan))


@batch_app.command("run")
def batch_run(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy for sandbox lines"),
    workspace: str | None = WORKSPACE_FLAG,
    continue_on_error: bool = typer.Option(
        False, "--continue-on-error", help="Continue after denied/failed command"
    ),
    json_output: bool = JSON_FLAG,
) -> None:
    """Execute deterministic batch file with no shell interpretation."""
    from ..cli_repl.batch import (
        BatchErrorMode,
        build_batch_plan,
        execute_batch_plan,
        render_plan_text,
    )

    ws = _workspace(workspace)
    plan = build_batch_plan(file.read_text(encoding="utf-8"), policy=policy, workspace=ws)
    if not json_output:
        console.print(render_plan_text(plan))
        console.print("[bold]Executing batch plan[/bold]")
    mode = BatchErrorMode.CONTINUE_ON_ERROR if continue_on_error else BatchErrorMode.FAIL_FAST
    result = execute_batch_plan(plan, error_mode=mode)
    if json_output:
        _out(ok(result.model_dump(mode="json")), True)
    else:
        for item in result.results:
            color = "green" if item.state in {"present", "ok", "completed"} else "yellow"
            if item.state in {"denied", "blocked", "error", "failed"}:
                color = "red"
            console.print(
                f"[{color}]{item.state}[/{color}] {item.line_no}.{item.index}: {item.command}"
            )
            if item.output:
                console.print(item.output)
            if item.reason:
                console.print(f"[dim]{item.reason}[/dim]")
    if not result.ok:
        raise typer.Exit(1)
