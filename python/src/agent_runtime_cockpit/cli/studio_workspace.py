"""Studio, sessions, workspace, context, adapter commands (Phase 25)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from ._app import console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)
from ._subapps import adapter_app, context_app, studio_app, studio_sessions_app, workspace_app

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok


# ─── context pack ─────────────────────────────────────────────────────────────


@context_app.command("pack")
def context_pack(
    task: str = typer.Option(..., "--task", "-t", help="Task description for context retrieval"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate a context pack for a task."""
    _setup_logging(debug)
    from ..context.pack import ContextPackGenerator

    ws = _workspace(workspace)
    gen = ContextPackGenerator()
    entries = gen.generate(task, ws, save=True)
    _out(ok([e.model_dump() for e in entries]), json_output)
    if not json_output:
        console.print(f"[green]Context pack:[/green] {len(entries)} entries for task: {task!r}")


# ─── adapter test ─────────────────────────────────────────────────────────────


@adapter_app.command("test")
def adapter_test(
    adapter_id: str = typer.Argument(..., help="Adapter ID: swarmgraph | langgraph"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run conformance tests against an adapter."""
    _setup_logging(debug)
    from ..adapters.conformance import run_conformance
    from ..adapters.registry import default_registry

    ws = _workspace(workspace)
    registry = default_registry()
    adapter = registry.get(adapter_id)

    if not adapter:
        _out(
            err(ArcErrorCode.ADAPTER_NOT_SUPPORTED, f"Adapter not found: {adapter_id!r}"),
            json_output,
        )
        raise typer.Exit(1)

    result = run_conformance(adapter, ws)

    summary = {
        "adapter": adapter_id,
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "ok": result.ok,
        "errors": result.errors,
        "details": result.details,
    }
    _out(ok(summary), json_output)

    if not json_output:
        table = Table(title=f"Conformance: {adapter_id}")
        table.add_column("Test")
        table.add_column("Result")
        table.add_column("Reason")
        for d in result.details:
            color = {"PASS": "green", "FAIL": "red", "SKIP": "yellow"}.get(d["result"], "white")
            table.add_row(d["test"], f"[{color}]{d['result']}[/{color}]", d.get("reason", ""))
        console.print(table)
        status = "[green]ALL PASS[/green]" if result.ok else f"[red]{result.failed} FAILED[/red]"
        console.print(
            f"Summary: {result.passed} passed · {result.failed} failed · {result.skipped} skipped → {status}"
        )

    if not result.ok:
        raise typer.Exit(1)


@adapter_app.command("list")
def adapter_list(debug: bool = DEBUG_FLAG) -> None:
    """List all registered adapters."""
    _setup_logging(debug)
    from ..adapters.registry import default_registry

    registry = default_registry()
    table = Table(title="Registered Adapters")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Capabilities")
    for a in registry.all():
        caps = a.capabilities()
        cap_str = " ".join(k.replace("can_", "") for k, v in caps.model_dump().items() if v)
        table.add_row(a.adapter_id, a.adapter_name, cap_str)
    console.print(table)


# ─── studio (Chat REPL) ──────────────────────────────────────────────────────


@studio_app.command("chat")
def studio_chat(
    prompt: Optional[str] = typer.Argument(None, help="Initial prompt"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Resume session ID"),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n", help="Run once and exit"
    ),
    debug: bool = DEBUG_FLAG,
) -> None:
    """Launch the ARC Studio chat REPL with the native SwarmGraph runtime.

    Starts an interactive chat session. Provide an initial prompt to run
    once, or omit it to enter the REPL loop.
    """
    _setup_logging(debug)
    from ..cli_repl.chat_repl import run_chat_repl

    run_chat_repl(
        initial_prompt=prompt,
        session_id=session,
        non_interactive=non_interactive,
    )


@studio_sessions_app.callback(invoke_without_command=True)
def studio_sessions(
    ctx: typer.Context,
    json_output: bool = JSON_FLAG,
) -> None:
    """List saved chat sessions."""
    if ctx.invoked_subcommand is not None:
        return
    from ..cli_repl.session import ChatSession

    sessions = ChatSession.list_sessions()
    if json_output:
        _out(ok([s.model_dump() for s in sessions]), json_output)
        return
    if not sessions:
        console.print("[dim]No saved sessions.[/dim]")
        return
    table = Table("ID", "Messages", "Updated")
    for s in sessions[:20]:
        table.add_row(s.id[:16], str(len(s.history)), s.updated_at[:19])
    console.print(table)


@studio_sessions_app.command("migrate")
def studio_sessions_migrate(
    json_output: bool = JSON_FLAG,
) -> None:
    """Migrate legacy flat sessions to canonical format."""
    from ..cli_repl.session import (
        _get_sessions_dir,
        _list_legacy_session_ids,
        migrate_legacy_session,
    )

    legacy_ids = _list_legacy_session_ids()
    newly_migrated: list[str] = []
    failed: list[str] = []
    for sid in legacy_ids:
        canonical_path = _get_sessions_dir() / sid / "session.json"
        if canonical_path.exists():
            continue
        result = migrate_legacy_session(sid)
        if result is not None:
            newly_migrated.append(sid)
        else:
            failed.append(sid)

    if json_output:
        _out(
            ok(
                {
                    "total_legacy": len(legacy_ids),
                    "newly_migrated": len(newly_migrated),
                    "already_migrated": len(legacy_ids) - len(newly_migrated) - len(failed),
                    "failed": len(failed),
                    "session_ids": newly_migrated,
                }
            ),
            json_output,
        )
        return

    if not legacy_ids:
        console.print("[dim]No legacy sessions found to migrate.[/dim]")
        return

    console.print(f"Migration complete: {len(newly_migrated)} migrated, {len(failed)} failed.")
    if newly_migrated:
        console.print(f"  Migrated: {', '.join(newly_migrated[:10])}")
    if failed:
        console.print(f"[yellow]  Failed: {', '.join(failed[:5])}[/yellow]")


@studio_app.command("sessions-migrate")
def studio_sessions_migrate_deprecated(
    json_output: bool = JSON_FLAG,
) -> None:
    """Deprecated alias for `arc studio sessions migrate`."""
    if not json_output:
        console.print("[yellow]Deprecated:[/yellow] use `arc studio sessions migrate`.")
    studio_sessions_migrate(json_output=json_output)


# ─── workspace commands ────────────────────────────────────────────────────────


@workspace_app.command("trust-status")
def workspace_trust_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show workspace trust status used for execution enforcement."""
    _setup_logging(debug)
    from ..security.trust import resolve_trust

    ws = _workspace(workspace)
    resolution = resolve_trust(ws)
    _out(ok(resolution.model_dump(), workspace=str(ws)), json_output)


@workspace_app.command("trust")
def workspace_trust(
    note: str = typer.Option("", "--note", help="Optional note for trust entry"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Mark the workspace as trusted (external DB, outside repo)."""
    _setup_logging(debug)
    from ..security.trust import trust_workspace

    ws = _workspace(workspace)
    resolution = trust_workspace(ws, note=note)
    _out(ok(resolution.model_dump(), workspace=str(ws)), json_output)


@workspace_app.command("untrust")
def workspace_untrust(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Remove workspace from the external trust database."""
    _setup_logging(debug)
    from ..security.trust import untrust_workspace

    ws = _workspace(workspace)
    resolution = untrust_workspace(ws)
    _out(ok(resolution.model_dump(), workspace=str(ws)), json_output)


@workspace_app.command("init")
def workspace_init(
    workspace: Optional[str] = WORKSPACE_FLAG,
    name: Optional[str] = typer.Option(None, "--name", help="Workspace name"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Initialize ARC configuration in a workspace."""
    _setup_logging(debug)
    from ..config.loader import init_config

    ws = _workspace(workspace)
    config_path = ws / ".arc" / "config.yaml"
    if config_path.exists():
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Config already exists at {config_path}"), json_output
        )
        raise typer.Exit(1)
    init_config(ws)
    if name:
        import yaml

        data = yaml.safe_load(config_path.read_text()) or {}
        data.setdefault("workspace", {})["name"] = name
        config_path.write_text(yaml.dump(data, default_flow_style=False))
    payload = {"created": str(config_path), "workspace": str(ws)}
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[green]Created[/green] {config_path}")


@workspace_app.command("info")
def workspace_info(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show workspace information including config and trust status."""
    _setup_logging(debug)
    from ..config.loader import load_config
    from ..security.trust import resolve_trust

    ws = _workspace(workspace)
    config = load_config(workspace=ws)
    trust_status = resolve_trust(ws)
    config_path = ws / ".arc" / "config.yaml"
    payload = {
        "workspace": str(ws),
        "name": config.workspace.name,
        "config_exists": config_path.exists(),
        "trust_level": trust_status.level.value,
        "trust_reason": trust_status.reason,
    }
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[bold]Workspace:[/bold] {ws}")
        if config.workspace.name:
            console.print(f"[bold]Name:[/bold] {config.workspace.name}")
        console.print(f"[bold]Config:[/bold] {'exists' if config_path.exists() else 'not found'}")
        console.print(f"[bold]Trust:[/bold] {trust_status.level.value}")
        console.print(f"[dim]{trust_status.reason}[/dim]")


@workspace_app.command("config")
def workspace_config_cmd(
    workspace: Optional[str] = WORKSPACE_FLAG,
    key: Optional[str] = typer.Option(
        None, "--key", "-k", help="Config key to set (e.g. runtime.default)"
    ),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Config value"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show or update workspace configuration."""
    _setup_logging(debug)
    from ..config.loader import load_config

    ws = _workspace(workspace)
    config_path = ws / ".arc" / "config.yaml"
    if key and value:
        if not config_path.exists():
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Config file not found. Run 'arc workspace init' first.",
                ),
                json_output,
            )
            raise typer.Exit(1)
        import yaml

        data = yaml.safe_load(config_path.read_text()) or {}
        parts = key.split(".")
        target = data
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
        config_path.write_text(yaml.dump(data, default_flow_style=False))
        payload = {"updated": key, "value": value, "config_path": str(config_path)}
        _out(ok(payload), json_output)
        if not json_output:
            console.print(f"[green]Updated[/green] {key} = {value}")
        return
    config = load_config(workspace=ws)
    _out(ok(config.flatten()), json_output)
