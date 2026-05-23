"""Root ARC CLI app definition (extracted from cli.py Phase 25)."""

from __future__ import annotations

import os
import sys as _sys

import typer
from rich.console import Console

from .. import __version__ as arc_version
from ..security.context import EnforcementContext, DryRunAbort, set_enforcement_context

from ._subapps import (
    adapter_app,
    audit_app,
    config_app,
    context_app,
    doctor_app,
    eval_app,
    hitl_app,
    isolation_app,
    mcp_app,
    profiles_app,
    prompt_app,
    providers_app,
    receipt_app,
    runs_app,
    storage_app,
    studio_app,
    studio_sessions_app,
    workspace_app,
)

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="arc",
    help="ARC — Agent Runtime Cockpit CLI",
    no_args_is_help=False,
    add_completion=False,
)

# Register sub-apps on the root app
app.add_typer(context_app)
app.add_typer(adapter_app)
app.add_typer(doctor_app)
app.add_typer(workspace_app)
app.add_typer(isolation_app)
app.add_typer(config_app)
app.add_typer(hitl_app)
app.add_typer(storage_app)
app.add_typer(studio_app)
studio_app.add_typer(studio_sessions_app)
app.add_typer(runs_app)
app.add_typer(eval_app)
app.add_typer(providers_app)
app.add_typer(receipt_app)
app.add_typer(audit_app)
app.add_typer(profiles_app)
app.add_typer(mcp_app)
app.add_typer(prompt_app)


@app.callback(invoke_without_command=True)
def _arc_default(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    allow_paid: bool = typer.Option(False, "--allow-paid", help="Bypass paid-call gate"),
    trust_workspace: bool = typer.Option(
        False, "--trust-workspace", help="Bypass workspace trust gate"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Deny all operations and log"),
) -> None:
    """ARC — Agent Runtime Cockpit CLI.

    With no arguments and a TTY, launches the ARC Studio interactive REPL.
    Use ARC_NO_TUI=1 to disable this behavior and show help instead.
    """
    if version:
        console.print(f"ARC Studio v{arc_version}")
        raise typer.Exit()

    enforcement_ctx = EnforcementContext(
        allow_paid=allow_paid,
        trust_workspace=trust_workspace,
        dry_run=dry_run,
    )
    set_enforcement_context(enforcement_ctx)

    if ctx.invoked_subcommand is not None:
        return

    no_tui = os.environ.get("ARC_NO_TUI", "")
    if not no_tui and _sys.stdin.isatty():
        from ..cli_repl.chat_repl import run_chat_repl

        run_chat_repl()
    else:
        import click as _click

        _click.echo(ctx.get_help())


def main() -> None:
    """Main entry point for ARC CLI with enforcement error handling."""
    try:
        app()
    except DryRunAbort as e:
        console.print(f"[yellow]Dry-run:[/yellow] {e}", err=True)
        _sys.exit(2)
