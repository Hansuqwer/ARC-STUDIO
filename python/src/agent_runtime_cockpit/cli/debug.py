"""CLI commands for ARC Debug — DAP adapter for agent run debugging (R99).

Commands:
  arc debug launch    Launch a debug session for a workflow.
  arc debug attach    Attach to a running debug session.
  arc debug status    Show debug adapter status.

All commands accept --json for machine-readable envelope output.
Local only. No remote debug server.
"""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.event_envelope import ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import debug_app


@debug_app.command("launch")
def debug_launch(
    program: str = typer.Argument(..., help="Program/workflow to debug"),
    host: str = typer.Option("127.0.0.1", "--host", help="Debug adapter host"),
    port: int = typer.Option(0, "--port", "-p", help="Debug adapter port (0=auto)"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Launch a debug session for a workflow (local DAP adapter)."""
    from ..debug import DebugAdapter

    _workspace(workspace)
    adapter = DebugAdapter(host=host, port=port)
    actual_port = adapter.start()

    _out(
        ok(
            {
                "session_id": program,
                "host": host,
                "port": actual_port,
                "status": "launched",
                "message": f"Debug adapter listening on {host}:{actual_port}. Connect your DAP client.",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Debug Session Launched[/bold]")
        console.print(f"  Program: {program}")
        console.print(f"  Host: {host}")
        console.print(f"  Port: {actual_port}")
        console.print(f"  Connect your DAP client to {host}:{actual_port}")

    adapter.stop()


@debug_app.command("attach")
def debug_attach(
    host: str = typer.Option("127.0.0.1", "--host", help="Debug adapter host"),
    port: int = typer.Option(..., "--port", "-p", help="Debug adapter port"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Attach to a running debug session (placeholder for future integration)."""
    _workspace(workspace)

    _out(
        ok(
            {
                "host": host,
                "port": port,
                "status": "attached",
                "message": f"Attached to debug adapter at {host}:{port}. Full attach integration pending.",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Debug Session Attached[/bold]")
        console.print(f"  Host: {host}")
        console.print(f"  Port: {port}")
        console.print("  [yellow]Full attach integration is pending.[/yellow]")


@debug_app.command("status")
def debug_status(
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Show debug adapter status."""
    from ..debug import DebugAdapter

    _workspace(workspace)
    adapter = DebugAdapter()
    status = adapter.get_status()

    _out(ok(status), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Debug Adapter Status[/bold]")
        console.print(f"  Running: {status['running']}")
        console.print(f"  Host: {status['host']}")
        console.print(f"  Port: {status['port']}")
        console.print(f"  Sessions: {len(status['sessions'])}")


__all__ = ["debug_app"]
