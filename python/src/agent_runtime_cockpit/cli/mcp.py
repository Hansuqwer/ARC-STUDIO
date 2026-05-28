"""MCP commands: serve (Phase 26 / R19) and workbench (Phase 78 / R48).

Provides the ``arc mcp serve --stdio`` command for the local MCP control plane
and the ``arc mcp workbench`` command group for diagnostic inspection of MCP servers.
Gated by workspace trust enforcement from Phase 23.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Optional

import anyio
import typer
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.trust import WorkspaceUntrusted, resolve_trust
from ._app import console, err_console
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import mcp_app, mcp_workbench_app

_AUDIT_EVENT_TYPE = "mcp_workbench_inspect"
_DEFAULT_INSPECT_TIMEOUT = 10.0


# ── Helper: persist audit event for workbench commands ──────────────────────


def _persist_workbench_audit_event(workspace: Path, event: dict) -> None:
    try:
        audit_dir = workspace / ".arc" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        path = audit_dir / "mcp.events.jsonl"
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(event, sort_keys=True, separators=(",", ":"), default=str) + "\n")
    except Exception:
        pass


# ── status command ──────────────────────────────────────────────────────────


@mcp_workbench_app.command("status")
def workbench_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show status of the local ARC MCP server and trust state.

    Reports whether the server can be created (trust check, workspace check),
    what tools/resources are registered, and current trust state.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    started_at = time.perf_counter()

    # Trust resolution (advisory, not enforcement)
    trust = resolve_trust(ws)

    # Check if server can be created
    server_creatable = False
    server_blocker: Optional[str] = None
    tools: list[str] = []
    resources: list[str] = []

    try:
        from ..mcp.server import MCPServerError, create_mcp_server

        mcp_server = create_mcp_server(workspace=ws)
        server_creatable = True

        # Extract tool and resource names from the FastMCP instance
        if hasattr(mcp_server, "_tool_manager") and mcp_server._tool_manager is not None:
            tools = sorted(t.name for t in mcp_server._tool_manager.list_tools())
        if hasattr(mcp_server, "_resource_manager") and mcp_server._resource_manager is not None:
            resources = sorted(
                t.uri_template for t in mcp_server._resource_manager.list_templates()
            )
    except MCPServerError as e:
        server_blocker = str(e)
    except WorkspaceUntrusted as e:
        server_blocker = str(e)

    elapsed = round((time.perf_counter() - started_at) * 1000, 3)

    data = {
        "workspace": str(ws),
        "server_creatable": server_creatable,
        "server_blocker": server_blocker,
        "tools": tools,
        "resources": resources,
        "trust": {
            "level": trust.level.value,
            "reason": trust.reason,
            "marker_path": trust.marker_path,
            "warning": trust.warning,
        },
        "diagnostic": "read-only",
    }

    _out(ok(data, workspace=str(ws), duration_ms=elapsed), json_output)


# ── inspect command ─────────────────────────────────────────────────────────


async def _inspect_server_async(
    server_cmd: list[str],
    timeout: float,
) -> dict:
    """Connect to a stdio MCP server, inspect its capabilities, and clean up."""
    proc = await asyncio.create_subprocess_exec(
        *server_cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](1000)
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](1000)

    async def _forward_stdin():
        try:
            async for msg in c2s_recv:
                json_data = msg.message.model_dump_json(by_alias=True, exclude_none=True)
                proc.stdin.write(json_data.encode("utf-8") + b"\n")
                await proc.stdin.drain()
        except anyio.EndOfStream:
            pass

    async def _forward_stdout():
        try:
            async for line in _async_iter_lines(proc.stdout, timeout):
                raw = line.decode("utf-8").strip()
                if not raw:
                    continue
                jsonrpc_msg = JSONRPCMessage.model_validate_json(raw)
                session_msg = SessionMessage(jsonrpc_msg)
                await s2c_send.send(session_msg)
        except Exception:
            pass
        finally:
            await s2c_send.aclose()

    async def _read_stderr():
        try:
            stderr_data = await asyncio.wait_for(proc.stderr.read(), timeout=timeout)
            if stderr_data:
                return stderr_data.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            pass
        return ""

    stderr_task = asyncio.create_task(_read_stderr())

    async with anyio.create_task_group() as tg:
        tg.start_soon(_forward_stdin)
        tg.start_soon(_forward_stdout)

        async with ClientSession(
            read_stream=s2c_recv,
            write_stream=c2s_send,
        ) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            resources_result = await session.list_resource_templates()
            prompts_result = await session.list_prompts()

            tools = [{"name": t.name, "description": t.description} for t in tools_result.tools]
            resources = [
                {"uriTemplate": r.uriTemplate, "name": r.name, "description": r.description}
                for r in resources_result.resourceTemplates
            ]
            prompts = [
                {"name": p.name, "description": p.description} for p in prompts_result.prompts
            ]

    # Clean up
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass

    stderr_output = stderr_task.result() if stderr_task.done() else ""

    return {
        "server_cmd": " ".join(server_cmd),
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
        "stderr": stderr_output or None,
    }


async def _async_iter_lines(stream, timeout: float):
    import asyncio

    BUFSIZE = 65536
    buf = b""
    while True:
        try:
            chunk = await asyncio.wait_for(stream.read(BUFSIZE), timeout=timeout)
        except asyncio.TimeoutError:
            break
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            yield line


def _inspect_server(
    server_cmd: list[str],
    workspace: Path,
    timeout: float,
) -> dict:
    """Synchronous wrapper around _inspect_server_async."""
    try:
        result = asyncio.run(_inspect_server_async(server_cmd, timeout))
    except asyncio.TimeoutError:
        result = {
            "server_cmd": " ".join(server_cmd),
            "error": f"inspect timed out after {timeout}s",
        }
    except BaseExceptionGroup as e:
        # Flatten ExceptionGroup to extract meaningful message
        messages = []
        for exc in e.exceptions:
            messages.append(str(exc)[:200])
        flat = "; ".join(messages)
        result = {
            "server_cmd": " ".join(server_cmd),
            "error": f"inspect failed: {flat}",
        }
    except Exception as e:
        result = {
            "server_cmd": " ".join(server_cmd),
            "error": str(e),
        }

    # Audit event
    _persist_workbench_audit_event(
        workspace,
        {
            "type": _AUDIT_EVENT_TYPE,
            "server_cmd": " ".join(server_cmd),
            "workspace": str(workspace),
            "error": result.get("error"),
            "tool_count": len(result.get("tools", [])),
            "resource_count": len(result.get("resources", [])),
            "prompt_count": len(result.get("prompts", [])),
            "timestamp": time.time(),
        },
    )

    return result


@mcp_workbench_app.command("inspect")
def workbench_inspect(
    server: str = typer.Argument(
        ..., help="MCP server command to inspect (e.g. 'python -m my_mcp_server')"
    ),
    timeout: float = typer.Option(
        _DEFAULT_INSPECT_TIMEOUT,
        "--timeout",
        help="Timeout in seconds for server inspection",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Connect to an MCP server via stdio and inspect its capabilities.

    Launches the given server command as a stdio subprocess, connects via
    MCP ClientSession, and lists tools, resources, and prompts. Closes the
    subprocess after inspection. No state is mutated.

    Examples:
        arc mcp workbench inspect --server "python -m my_mcp_server"
        arc mcp workbench inspect --server "uvx my_mcp_server" --timeout 15
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    started_at = time.perf_counter()

    if not server or not server.strip():
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                "Server command is required.",
                details={"code": "MISSING_SERVER_ARG"},
            ),
            json_output,
        )
        raise typer.Exit(2)

    # Parse server command string into argv list
    import shlex

    server_cmd = shlex.split(server)

    result = _inspect_server(server_cmd, ws, timeout)
    elapsed = round((time.perf_counter() - started_at) * 1000, 3)

    if "error" in result:
        _out(
            err(
                ArcErrorCode.INTERNAL_ERROR,
                result["error"],
                details={"server_cmd": result["server_cmd"]},
            ),
            json_output,
        )
        raise typer.Exit(1)

    _out(
        ok(
            {
                "server_cmd": result["server_cmd"],
                "tools": result["tools"],
                "resources": result["resources"],
                "prompts": result["prompts"],
                "stderr": result.get("stderr"),
                "diagnostic": "read-only",
            },
            workspace=str(ws),
            duration_ms=elapsed,
        ),
        json_output,
    )


# ── serve command (unchanged) ───────────────────────────────────────────────


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
        from ..mcp.server import MCPServerError, create_mcp_server

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
