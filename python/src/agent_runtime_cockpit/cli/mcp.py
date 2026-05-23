"""MCP commands: serve (Phase 26 / R19).

Provides the ``arc mcp serve --stdio`` command for the local MCP control plane.
Gated by workspace trust enforcement from Phase 23.
"""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err
from ..security.trust import WorkspaceUntrusted

from ._app import console, err_console
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import mcp_app


@mcp_app.command("serve")
def mcp_serve(
    stdio: bool = typer.Option(
        True, "--stdio", help="Use stdio transport (only supported transport)"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Start the ARC MCP local control plane server.

    Uses stdio transport only. This is a local control plane — no network
    sockets are opened. All tools are gated by workspace trust enforcement.

    Compatible with Claude Desktop, Codex, and other local MCP clients.

    Examples:

        arc mcp serve --stdio

        ARC_MCP_SERVE_STDIO=1 arc mcp serve
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    if not stdio:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                "Only stdio transport is supported. Use --stdio.",
                details={"code": "UNSUPPORTED_TRANSPORT"},
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Import and create the MCP server
    try:
        from ..mcp.server import create_mcp_server, MCPServerError

        mcp_server = create_mcp_server(workspace=ws)
    except MCPServerError as e:
        err_console.print(f"[red]MCP server error:[/red] {e}")
        raise typer.Exit(1)
    except WorkspaceUntrusted as e:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                f"MCP server blocked: {e}",
                details={"code": "WORKSPACE_UNTRUSTED"},
            ),
            json_output,
        )
        raise typer.Exit(1)

    console.print("[dim]ARC MCP server starting on stdio...[/dim]")
    console.print("[dim]Trusted workspace:[/dim]", str(ws))
    try:
        mcp_server.run(transport="stdio")
    except KeyboardInterrupt:
        console.print("\n[dim]MCP server stopped.[/dim]")
        raise typer.Exit(0)
