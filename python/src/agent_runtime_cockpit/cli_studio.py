"""
ARC Studio — thin CLI shim (≤30 lines) that delegates to `arc studio chat`.

This module is the `arc-studio` console_scripts entry point. It imports
the unified cli_repl machinery and delegates all behavior there.

Usage:
  arc-studio                  Interactive chat REPL (delegates to arc studio chat)
  arc-studio <message>        One-shot dispatch (delegates to arc studio chat)
  arc-studio --version        Print version and exit

Legacy StudioSession flat JSON sessions are still readable via the unified
ChatSession.load() fallback, but never written. Use `arc studio sessions
migrate` to convert legacy sessions to the canonical format.
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .cli_repl.chat_repl import run_chat_repl

app = typer.Typer(
    name="arc-studio",
    help="ARC Studio — Run agents. See everything.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    message: Optional[str] = typer.Argument(None, help="One-shot message or slash command"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    """
    ARC Studio — Run agents. See everything.

    With no arguments, launches interactive chat. With one argument, runs
    the message as a one-shot command and exits.

    This is a thin shim that delegates to `arc studio chat`.
    """
    if version:
        console.print(f"ARC Studio v{__version__}")
        raise typer.Exit()

    run_chat_repl(
        initial_prompt=message,
        non_interactive=message is not None,
    )
