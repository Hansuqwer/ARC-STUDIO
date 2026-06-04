"""MCP commands: serve (Phase 26 / R19) and workbench (Phase 78 / R48).

Provides the ``arc mcp serve --stdio`` command for the local MCP control plane
and the ``arc mcp workbench`` command group for diagnostic inspection of MCP servers.
Gated by workspace trust enforcement from Phase 23.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from pathlib import Path
from typing import Optional

import anyio
import typer
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage

from ..mcp.session import (
    cleanup_stale_sessions,
    list_sessions,
    show_session,
    start_session,
    stop_session,
)
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..isolation.subprocess import SubprocessIsolationProvider
from ..security.sandbox import (
    approve_decision_with_token,
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    persist_sandbox_audit_event,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
)
from ..security.trust import WorkspaceUntrusted, ensure_trusted, resolve_trust
from ._app import console, err_console
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import mcp_app, mcp_workbench_app

_AUDIT_EVENT_TYPE = "mcp_workbench_inspect"
_DEFAULT_INSPECT_TIMEOUT = 10.0
_MCP_STDERR_MAX_BYTES = 65_536


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


def _persist_mcp_sandbox_audit(
    *,
    command: list[str],
    cwd: Path,
    decision,
    started_at: str,
    exit_code: int | None,
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
    redaction_applied: bool = False,
) -> dict:
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider="subprocess",
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=exit_code,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        redaction_applied=redaction_applied,
    )
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)
    return audit


def _deny_decision(decision, reason: str):
    return decision.model_copy(
        update={
            "allowed": False,
            "reason": reason,
            "approval_required": False,
            "approved": False,
        }
    )


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
    *,
    cwd: Path | None = None,
    safe_env_keys: frozenset[str] | None = None,
) -> dict:
    """Connect to a stdio MCP server, inspect its capabilities, and clean up."""
    provider = SubprocessIsolationProvider(
        safe_env_keys=safe_env_keys,
        workspace_root=cwd,
        max_output_bytes=_MCP_STDERR_MAX_BYTES,
    )
    proc = await asyncio.create_subprocess_exec(
        *server_cmd,
        cwd=str(cwd) if cwd else None,
        env=provider.filter_env(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
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
        chunks = bytearray()
        try:
            stderr_data = await asyncio.wait_for(
                proc.stderr.read(_MCP_STDERR_MAX_BYTES + 1), timeout=timeout
            )
            if stderr_data:
                chunks.extend(stderr_data[:_MCP_STDERR_MAX_BYTES])
        except asyncio.TimeoutError:
            pass
        return bytes(chunks).decode("utf-8", errors="replace")

    async def _terminate_process() -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            await proc.wait()

    stderr_task = asyncio.create_task(_read_stderr())

    try:
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
    finally:
        await _terminate_process()

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
    *,
    safe_env_keys: frozenset[str] | None = None,
    cwd: Path | None = None,
) -> dict:
    """Synchronous wrapper around _inspect_server_async."""
    try:
        result = asyncio.run(
            _inspect_server_async(
                server_cmd,
                timeout,
                cwd=cwd,
                safe_env_keys=safe_env_keys,
            )
        )
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
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Use a scoped sandbox approval token"
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
    perf_start = time.perf_counter()

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

    try:
        ensure_trusted(ws)
        cwd = ensure_workspace_cwd(Path.cwd(), ws)
        policy_model = resolve_sandbox_policy(policy, ws)
        decision = decide(server_cmd, policy_model)
        decision = approve_decision_with_token(
            token=approval_token,
            command=server_cmd,
            policy=policy_model,
            decision=decision,
        )
    except WorkspaceUntrusted as exc:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                str(exc),
                details={"code": "WORKSPACE_UNTRUSTED"},
            ),
            json_output,
        )
        raise typer.Exit(3) from exc
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2) from exc

    started_at = utc_now()
    try:
        validate_command_paths(server_cmd, policy_model)
    except ValueError as exc:
        audit = _persist_mcp_sandbox_audit(
            command=server_cmd,
            cwd=cwd,
            decision=_deny_decision(decision, str(exc)),
            started_at=started_at,
            exit_code=None,
        )
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                str(exc),
                details={"audit_path": audit["audit_path"], "audit_id": audit["audit_id"]},
            ),
            json_output,
        )
        raise typer.Exit(2) from exc
    if not decision.allowed:
        audit = _persist_mcp_sandbox_audit(
            command=server_cmd,
            cwd=cwd,
            decision=decision,
            started_at=started_at,
            exit_code=None,
        )
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                decision.reason,
                details={
                    "classification": decision.classification.value,
                    "policy": policy_model.name,
                    "audit_path": audit["audit_path"],
                    "audit_id": audit["audit_id"],
                },
            ),
            json_output,
        )
        raise typer.Exit(3)

    result = _inspect_server(
        server_cmd,
        ws,
        timeout,
        cwd=cwd,
        safe_env_keys=frozenset(policy_model.env_allowlist),
    )
    elapsed = round((time.perf_counter() - perf_start) * 1000, 3)

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

    _persist_mcp_sandbox_audit(
        command=server_cmd,
        cwd=cwd,
        decision=decision,
        started_at=started_at,
        exit_code=0,
    )

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


# ── session commands ─────────────────────────────────────────────────────────


@mcp_workbench_app.command("session-start")
def workbench_session_start(
    server: str = typer.Argument(..., help="MCP server command to start"),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Use a scoped sandbox approval token"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Start a persistent MCP session (stdio subprocess).

    The server process runs in a process group for clean teardown.
    No HTTP listener. No auto-restart.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    import shlex

    server_cmd = shlex.split(server)
    if not server_cmd:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing server command"), json_output)
        raise typer.Exit(2)

    try:
        ensure_trusted(ws)
        cwd = ensure_workspace_cwd(Path.cwd(), ws)
        policy_model = resolve_sandbox_policy(policy, ws)
        decision = decide(server_cmd, policy_model)
        decision = approve_decision_with_token(
            token=approval_token,
            command=server_cmd,
            policy=policy_model,
            decision=decision,
        )
    except WorkspaceUntrusted as exc:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                str(exc),
                details={"code": "WORKSPACE_UNTRUSTED"},
            ),
            json_output,
        )
        raise typer.Exit(3) from exc
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2) from exc

    started_at = utc_now()
    try:
        validate_command_paths(server_cmd, policy_model)
    except ValueError as exc:
        audit = _persist_mcp_sandbox_audit(
            command=server_cmd,
            cwd=cwd,
            decision=_deny_decision(decision, str(exc)),
            started_at=started_at,
            exit_code=None,
        )
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                str(exc),
                details={"audit_path": audit["audit_path"], "audit_id": audit["audit_id"]},
            ),
            json_output,
        )
        raise typer.Exit(2) from exc
    if not decision.allowed:
        audit = _persist_mcp_sandbox_audit(
            command=server_cmd,
            cwd=cwd,
            decision=decision,
            started_at=started_at,
            exit_code=None,
        )
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                decision.reason,
                details={
                    "classification": decision.classification.value,
                    "policy": policy_model.name,
                    "audit_path": audit["audit_path"],
                    "audit_id": audit["audit_id"],
                },
            ),
            json_output,
        )
        raise typer.Exit(3)

    provider = SubprocessIsolationProvider(safe_env_keys=frozenset(policy_model.env_allowlist))
    record = start_session(ws, server_cmd, cwd=cwd, env=provider.filter_env())
    _persist_mcp_sandbox_audit(
        command=server_cmd,
        cwd=cwd,
        decision=decision,
        started_at=started_at,
        exit_code=0,
    )
    _out(ok(record.model_dump(mode="json"), workspace=str(ws)), json_output)


@mcp_workbench_app.command("session-stop")
def workbench_session_stop(
    session_id: str = typer.Argument(..., help="Session ID to stop"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Stop a persistent MCP session (kill process group)."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    stopped = stop_session(ws, session_id)
    if not stopped:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Session not found: {session_id}"), json_output)
        raise typer.Exit(1)
    _out(ok({"stopped": True, "session_id": session_id}, workspace=str(ws)), json_output)


@mcp_workbench_app.command("session-list")
def workbench_session_list(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List all registered MCP sessions."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    sessions = list_sessions(ws)
    _out(ok({"sessions": sessions, "count": len(sessions)}, workspace=str(ws)), json_output)


@mcp_workbench_app.command("session-show")
def workbench_session_show(
    session_id: str = typer.Argument(..., help="Session ID to show"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show one MCP session details."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    session = show_session(ws, session_id)
    if not session:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Session not found: {session_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(session, workspace=str(ws)), json_output)


@mcp_workbench_app.command("session-cleanup")
def workbench_session_cleanup(
    timeout: int = typer.Option(3600, "--timeout", help="Idle timeout in seconds"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Clean up stale MCP sessions beyond idle timeout."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    cleaned = cleanup_stale_sessions(ws, timeout=timeout)
    _out(ok({"cleaned": cleaned, "count": len(cleaned)}, workspace=str(ws)), json_output)


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


# ── MCP outbound risk gate commands (Item 2) ────────────────────────────────


@mcp_app.command("risk-scan")
def mcp_risk_scan(
    server_id: str = typer.Argument(..., help="MCP server ID to scan"),
    tool: str = typer.Argument(..., help="Tool name to score"),
    arguments: Optional[str] = typer.Option(None, "--args", help="JSON arguments string"),
    policy: str = typer.Option("strict", "--policy", help="Policy: strict or permissive"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Score an MCP tool call for risk without executing it.

    Examples:
        arc mcp risk-scan my-server write_file --args '{"path":"/tmp/x"}'
        arc mcp risk-scan my-server read_file --policy permissive
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    perf_start = time.perf_counter()

    from ..mcp.manifests import ManifestStore
    from ..mcp.sandbox import McpPolicy, decide_call

    args_dict = None
    if arguments:
        try:
            args_dict = json.loads(arguments)
        except json.JSONDecodeError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid JSON arguments: {exc}"), json_output)
            raise typer.Exit(2) from exc

    # Check manifest for tool risk
    store = ManifestStore(workspace=ws)
    manifest = store.load(server_id)
    manifest_risk = "low"
    if manifest:
        for tr in manifest.tool_risks:
            if tr.tool_name == tool:
                manifest_risk = tr.risk_level
                break

    pol = McpPolicy.STRICT if policy == "strict" else McpPolicy.PERMISSIVE
    decision = decide_call(
        server_id=server_id,
        tool_name=tool,
        arguments=args_dict,
        manifest_risk=manifest_risk,
        policy=pol,
    )
    elapsed = round((time.perf_counter() - perf_start) * 1000, 3)
    _out(
        ok(
            {
                "server_id": server_id,
                "tool_name": tool,
                "decision": decision.decision.value,
                "risk_level": decision.risk_score.level.value,
                "reasons": decision.risk_score.reasons,
                "policy": decision.policy.value,
                "reason": decision.reason,
            },
            workspace=str(ws),
            duration_ms=elapsed,
        ),
        json_output,
    )


@mcp_app.command("decisions")
def mcp_decisions(
    limit: int = typer.Option(50, "--limit", help="Max decisions to show"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List recent MCP call risk decisions from workspace audit log.

    Reads .arc/mcp/decisions.jsonl in the current workspace.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    perf_start = time.perf_counter()

    from ..mcp.sandbox import load_decisions

    decisions = load_decisions(ws, limit=limit)
    elapsed = round((time.perf_counter() - perf_start) * 1000, 3)
    _out(
        ok(
            {"decisions": decisions, "count": len(decisions)},
            workspace=str(ws),
            duration_ms=elapsed,
        ),
        json_output,
    )


@mcp_app.command("policy-explain")
def mcp_policy_explain(
    server_id: str = typer.Argument(..., help="MCP server ID"),
    tool: str = typer.Argument(..., help="Tool name"),
    arguments: Optional[str] = typer.Option(None, "--args", help="JSON arguments string"),
    policy: str = typer.Option("strict", "--policy", help="Policy: strict or permissive"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain what policy decision would apply to an MCP tool call.

    Like risk-scan, but includes full signal breakdown and manifest context.

    Examples:
        arc mcp policy-explain my-server write_file --args '{"content":"hello"}'
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    perf_start = time.perf_counter()

    from ..mcp.manifests import ManifestStore
    from ..mcp.risk import RiskSignals, scan_call_arguments, score_call
    from ..mcp.sandbox import McpPolicy

    args_dict = None
    if arguments:
        try:
            args_dict = json.loads(arguments)
        except json.JSONDecodeError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid JSON arguments: {exc}"), json_output)
            raise typer.Exit(2) from exc

    store = ManifestStore(workspace=ws)
    manifest = store.load(server_id)
    manifest_risk = "low"
    tool_meta = None
    if manifest:
        for tr in manifest.tool_risks:
            if tr.tool_name == tool:
                manifest_risk = tr.risk_level
                tool_meta = tr.model_dump()
                break

    drift_report = store.check_drift(server_id, []) if manifest else None
    inj_sev = scan_call_arguments(args_dict)
    signals = RiskSignals(manifest_risk=manifest_risk, injection_severity=inj_sev)
    score = score_call(signals)

    pol = McpPolicy.STRICT if policy == "strict" else McpPolicy.PERMISSIVE
    elapsed = round((time.perf_counter() - perf_start) * 1000, 3)
    _out(
        ok(
            {
                "server_id": server_id,
                "tool_name": tool,
                "manifest_pinned": manifest is not None,
                "manifest_risk": manifest_risk,
                "tool_meta": tool_meta,
                "injection_severity": inj_sev,
                "drift": drift_report,
                "risk_level": score.level.value,
                "reasons": score.reasons,
                "policy": pol.value,
                "explanation": f"With policy={pol.value} and risk={score.level.value}: "
                + (
                    "DENY"
                    if (pol == McpPolicy.STRICT and score.level.value in ("high", "critical"))
                    or (pol == McpPolicy.PERMISSIVE and score.level.value == "critical")
                    else "WARN"
                    if score.level.value in ("medium", "high")
                    else "ALLOW"
                ),
            },
            workspace=str(ws),
            duration_ms=elapsed,
        ),
        json_output,
    )


@mcp_app.command("proxy")
def mcp_proxy(
    server: str = typer.Argument(..., help="Upstream MCP server command"),
    policy: str = typer.Option("strict", "--policy", help="Policy: strict or permissive"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run stdio MCP proxy with per-call risk gating.

    Sits between client and upstream MCP server. Intercepts tools/call,
    scores risk, denies high/critical calls under strict policy.

    Examples:
        arc mcp proxy "python -m my_server" --policy strict
    """
    import shlex

    _setup_logging(debug)
    ws = _workspace(workspace)

    from ..mcp.proxy import run_proxy
    from ..mcp.sandbox import McpPolicy

    server_cmd = shlex.split(server)
    pol = McpPolicy.STRICT if policy == "strict" else McpPolicy.PERMISSIVE

    try:
        asyncio.run(run_proxy(server_cmd, workspace=ws, policy=pol))
    except KeyboardInterrupt:
        pass
