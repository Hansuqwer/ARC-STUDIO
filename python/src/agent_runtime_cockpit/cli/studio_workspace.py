"""Studio, sessions, workspace, context, adapter commands (Phase 25)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..workspace import iter_workspace_files
from ..workspace.symbols import collect_workspace_symbols
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


@studio_sessions_app.command("show")
def studio_sessions_show(
    session_id: str = typer.Argument(..., help="Session ID"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Show a saved session without modifying it."""
    from ..cli_repl.session import ChatSession
    from ..cli_repl.session_bundle import export_session_bundle

    session = ChatSession.load(session_id)
    if session is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Session not found: {session_id}"), json_output)
        raise typer.Exit(1)
    data = export_session_bundle(session).session
    if json_output:
        _out(ok(data), True)
        return
    console.print(f"Session: {data['id']}")
    console.print(f"Mode: {data['mode']} Runtime: {data['runtime_mode']}")
    console.print(f"Messages: {len(data.get('history', []))}")


@studio_sessions_app.command("export")
def studio_sessions_export(
    session_id: str = typer.Argument(..., help="Session ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path, or stdout"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Export a redacted session bundle."""
    from pathlib import Path

    from ..cli_repl.session import ChatSession
    from ..cli_repl.session_bundle import export_session_bundle, write_session_bundle

    session = ChatSession.load(session_id)
    if session is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Session not found: {session_id}"), json_output)
        raise typer.Exit(1)
    bundle = export_session_bundle(session)
    if output:
        path = Path(output).expanduser()
        write_session_bundle(path, bundle)
        _out(ok({"path": str(path), "session_id": session.id}), json_output)
        return
    console.print(bundle.model_dump_json(indent=2))


@studio_sessions_app.command("import")
def studio_sessions_import(
    bundle_path: str = typer.Argument(..., help="Session bundle path"),
    new_id: bool = typer.Option(False, "--new-id", help="Assign a new session ID"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing session"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Validate and import a session bundle atomically."""
    from pathlib import Path

    from ..cli_repl.session_bundle import import_session_bundle

    try:
        session = import_session_bundle(
            Path(bundle_path).expanduser(), new_id=new_id, overwrite=overwrite
        )
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1) from exc
    _out(ok({"session_id": session.id, "messages": len(session.history)}), json_output)


@studio_sessions_app.command("write")
def studio_sessions_write(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Import a session payload from stdin (IDE write bridge).

    Reads a JSON session payload from stdin, validates it against the
    ChatSession schema, strips secret-looking fields, and writes atomically
    via write_text_atomic(lock=True). Requires workspace trust.

    The payload must be a valid ChatSession JSON object.
    History is capped at 200 entries. Payload size is capped at 512 KB.
    Returns a stable ok/err JSON envelope.
    """
    import sys

    _setup_logging(debug)

    from ..cli_repl.session import (
        SESSION_ID_RE,
        ChatSession,
        is_safe_session_id,
    )
    from ..cli_repl.session_bundle import _contains_secret
    from ..protocol.errors import ArcErrorCode
    from ..security.enforcement import TrustEnforcementError, enforce_workspace_trust
    from ..storage.advisory_lock import AdvisoryLockUnavailable

    ws = _workspace(workspace)

    # Workspace trust check
    try:
        enforce_workspace_trust(ws, "session_write", "ide-bridge", 0)
    except TrustEnforcementError as exc:
        _out(err(ArcErrorCode.PERMISSION_DENIED, str(exc)), json_output)
        raise typer.Exit(1) from exc

    # Read payload from stdin
    raw = sys.stdin.read()
    if len(raw.encode("utf-8")) > 512 * 1024:
        _out(err(ArcErrorCode.INVALID_INPUT, "payload exceeds 512 KB limit"), json_output)
        raise typer.Exit(1)

    try:
        import json as _json

        data = _json.loads(raw)
    except (ValueError, TypeError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"invalid JSON: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # Secret scan on raw payload
    if _contains_secret(data):
        _out(err(ArcErrorCode.INVALID_INPUT, "payload contains secret-looking data"), json_output)
        raise typer.Exit(1)

    # Cap history
    if isinstance(data.get("history"), list) and len(data["history"]) > 200:
        data["history"] = data["history"][-200:]

    # Validate ChatSession schema
    try:
        session = ChatSession.model_validate(data)
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"invalid session payload: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # ID validation
    if not is_safe_session_id(session.id) or not SESSION_ID_RE.match(session.id):
        _out(err(ArcErrorCode.INVALID_INPUT, f"unsafe session id: {session.id!r}"), json_output)
        raise typer.Exit(1)

    # Write atomically under advisory lock
    try:
        session.save()
    except AdvisoryLockUnavailable as exc:
        _out(err(ArcErrorCode.LOCK_CONTENTION, str(exc)), json_output)
        raise typer.Exit(1) from exc
    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, str(exc)), json_output)
        raise typer.Exit(1) from exc

    _out(ok({"session_id": session.id, "messages": len(session.history)}), json_output)


@studio_sessions_app.command("delete")
def studio_sessions_delete(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a session by ID (IDE write bridge).

    Validates the session ID, deletes the session file (and directory if empty)
    under advisory lock. Requires workspace trust.
    Returns a stable ok/err JSON envelope.
    """
    _setup_logging(debug)

    from ..cli_repl.session import SESSION_ID_RE, _get_sessions_dir, is_safe_session_id
    from ..protocol.errors import ArcErrorCode
    from ..security.enforcement import TrustEnforcementError, enforce_workspace_trust
    from ..storage.advisory_lock import AdvisoryLockUnavailable, advisory_lock

    ws = _workspace(workspace)

    # ID validation
    if not is_safe_session_id(session_id) or not SESSION_ID_RE.match(session_id):
        _out(err(ArcErrorCode.INVALID_INPUT, f"unsafe session id: {session_id!r}"), json_output)
        raise typer.Exit(1)

    # Workspace trust check
    try:
        enforce_workspace_trust(ws, "session_delete", "ide-bridge", 0)
    except TrustEnforcementError as exc:
        _out(err(ArcErrorCode.PERMISSION_DENIED, str(exc)), json_output)
        raise typer.Exit(1) from exc

    sess_dir = _get_sessions_dir()
    session_path = sess_dir / session_id / "session.json"

    if not session_path.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"session not found: {session_id}"), json_output)
        raise typer.Exit(1)

    try:
        with advisory_lock(session_path):
            session_path.unlink(missing_ok=True)
            # Remove empty parent dir
            parent = session_path.parent
            try:
                parent.rmdir()
            except OSError:
                pass  # Directory not empty or already gone — non-critical
    except AdvisoryLockUnavailable as exc:
        _out(err(ArcErrorCode.LOCK_CONTENTION, str(exc)), json_output)
        raise typer.Exit(1) from exc
    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, str(exc)), json_output)
        raise typer.Exit(1) from exc

    _out(ok({"session_id": session_id, "deleted": True}), json_output)


# Allowed safe fields for IDE-initiated session updates.
# History mutation and secret fields are deliberately excluded.
_SESSION_UPDATE_ALLOWED_FIELDS = frozenset({"mode", "runtime_mode", "profile_id", "isolation_id"})


@studio_sessions_app.command("update")
def studio_sessions_update(
    session_id: str = typer.Argument(..., help="Session ID"),
    field: str = typer.Option(..., "--field", help="Field to update"),
    value: str = typer.Option(..., "--value", help="New value"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Update a single safe field on a session (IDE write bridge).

    Allowed fields: mode, runtime_mode, profile_id, isolation_id.
    History mutation and secret fields are rejected.
    Loads, validates, and re-saves the session atomically under advisory lock.
    Requires workspace trust.
    Returns a stable ok/err JSON envelope.
    """
    _setup_logging(debug)

    from ..cli_repl.session import SESSION_ID_RE, ChatSession, is_safe_session_id
    from ..cli_repl.session_bundle import _contains_secret
    from ..protocol.errors import ArcErrorCode
    from ..security.enforcement import TrustEnforcementError, enforce_workspace_trust
    from ..storage.advisory_lock import AdvisoryLockUnavailable

    ws = _workspace(workspace)

    # ID validation
    if not is_safe_session_id(session_id) or not SESSION_ID_RE.match(session_id):
        _out(err(ArcErrorCode.INVALID_INPUT, f"unsafe session id: {session_id!r}"), json_output)
        raise typer.Exit(1)

    # Field allowlist check
    if field not in _SESSION_UPDATE_ALLOWED_FIELDS:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"field {field!r} is not updatable via IDE bridge; "
                f"allowed: {sorted(_SESSION_UPDATE_ALLOWED_FIELDS)}",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Secret scan on value
    if _contains_secret(value):
        _out(err(ArcErrorCode.INVALID_INPUT, "value contains secret-looking data"), json_output)
        raise typer.Exit(1)

    # Workspace trust check
    try:
        enforce_workspace_trust(ws, "session_update", "ide-bridge", 0)
    except TrustEnforcementError as exc:
        _out(err(ArcErrorCode.PERMISSION_DENIED, str(exc)), json_output)
        raise typer.Exit(1) from exc

    # Load existing session
    session = ChatSession.load(session_id)
    if session is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"session not found: {session_id}"), json_output)
        raise typer.Exit(1)

    # Apply field update
    try:
        # Validate by constructing updated dict and re-validating
        data = session.model_dump(mode="json")
        data[field] = value
        updated = ChatSession.model_validate(data)
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"invalid value for {field!r}: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # Save atomically
    try:
        updated.save()
    except AdvisoryLockUnavailable as exc:
        _out(err(ArcErrorCode.LOCK_CONTENTION, str(exc)), json_output)
        raise typer.Exit(1) from exc
    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, str(exc)), json_output)
        raise typer.Exit(1) from exc

    _out(ok({"session_id": session_id, "field": field, "updated": True}), json_output)


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
    isolation: Optional[str] = typer.Option(
        None,
        "--isolation",
        help="Isolation backend: auto, subprocess, docker, microvm "
        "(use `arc isolation off` to disable). Prompts when omitted interactively.",
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Initialize ARC configuration in a workspace."""
    _setup_logging(debug)
    from ..config.loader import init_config, set_isolation_backend

    ws = _workspace(workspace)
    config_path = ws / ".arc" / "config.yaml"
    if config_path.exists():
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Config already exists at {config_path}"), json_output
        )
        raise typer.Exit(1)

    # First-run isolation chooser: offer the alternatives at setup time.
    selectable = ("auto", "subprocess", "docker", "microvm")
    chosen = isolation.strip().lower() if isolation else None
    if chosen is None and not json_output:
        console.print("[bold]Choose an isolation backend[/bold] for sandboxed command execution:")
        console.print("  [cyan]auto[/cyan]       recommended — hardened subprocess sandbox")
        console.print(
            "  [cyan]subprocess[/cyan] explicit subprocess sandbox (env scrub + path confinement)"
        )
        console.print(
            "  [cyan]docker[/cyan]     container isolation (needs ARC_ENABLE_CONTAINER_SANDBOX + docker)"
        )
        console.print("  [cyan]microvm[/cyan]    experimental macOS VZ microVM (gated, unproven)")
        console.print("  [dim]run `arc isolation off` later to disable isolation entirely[/dim]")
        chosen = typer.prompt("Isolation backend", default="auto").strip().lower()
    if chosen and chosen not in selectable:
        hint = " (use `arc isolation off` to disable isolation)" if chosen == "none" else ""
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid isolation backend {chosen!r}; choose one of {', '.join(selectable)}.{hint}",
            ),
            json_output,
        )
        raise typer.Exit(2)

    init_config(ws)
    if name:
        import yaml

        data = yaml.safe_load(config_path.read_text()) or {}
        data.setdefault("workspace", {})["name"] = name
        config_path.write_text(yaml.dump(data, default_flow_style=False))
    if chosen and chosen != "auto":
        set_isolation_backend(chosen, config_path=config_path)
    payload = {"created": str(config_path), "workspace": str(ws), "isolation": chosen or "auto"}
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[green]Created[/green] {config_path}")
        console.print(f"[bold]Isolation:[/bold] {chosen or 'auto'}")


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


@workspace_app.command("inventory")
def workspace_inventory(
    suffix: Optional[str] = typer.Option(
        None,
        "--suffix",
        "-s",
        help="Comma-separated file suffixes to include (default: .py,.ts,.tsx,.json,.yaml,.md)",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Deterministic local context inventory — files, git, traces, MCP."""
    import subprocess as _subprocess

    _setup_logging(debug)
    ws = _workspace(workspace)

    suffixes_list = (
        tuple(f".{s.strip().lstrip('.')}" for s in suffix.split(",") if s.strip())
        if suffix
        else (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".md")
    )

    files: list[dict] = []
    total_size = 0
    for path in iter_workspace_files(ws, suffixes_list):
        try:
            stat = path.stat()
            files.append(
                {
                    "path": str(path.relative_to(ws)),
                    "size": stat.st_size,
                    "suffix": path.suffix,
                    "provenance": "workspace_file",
                }
            )
            total_size += stat.st_size
        except OSError:
            files.append(
                {
                    "path": str(path.relative_to(ws)),
                    "size": None,
                    "suffix": path.suffix,
                    "provenance": "workspace_file",
                    "error": "stat_failed",
                }
            )

    symbol_inventory = collect_workspace_symbols(ws, files)

    git_meta: dict = {"provenance": "git"}
    git_dir = ws / ".git"
    if git_dir.is_dir():
        git_meta["present"] = True
        try:
            branch = _subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=ws,
                check=False,
            ).stdout.strip()
            commit = _subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=ws,
                check=False,
            ).stdout.strip()
            commit_count = _subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=ws,
                check=False,
            ).stdout.strip()
            status = _subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=ws,
                check=False,
            ).stdout.strip()
            git_meta.update(
                {
                    "branch": branch or None,
                    "commit": commit or None,
                    "commit_count": int(commit_count) if commit_count.isdigit() else None,
                    "dirty": bool(status),
                    "git_dir": str(git_dir),
                }
            )
        except Exception:
            git_meta["degraded"] = True
            git_meta["reason"] = "git_command_failed"
    else:
        git_meta["present"] = False
        git_meta["reason"] = "no_git_dir"

    traces_dir = ws / ".arc" / "traces"
    traces: list[dict] = []
    if traces_dir.is_dir():
        for tpath in sorted(traces_dir.iterdir()):
            if tpath.is_file() and tpath.suffix == ".jsonl":
                try:
                    tstat = tpath.stat()
                    traces.append(
                        {
                            "name": tpath.name,
                            "size": tstat.st_size,
                            "provenance": "trace_store",
                        }
                    )
                except OSError:
                    pass

    mcp_dir = ws / ".arc" / "mcp"
    mcp_resources: list[dict] = []
    if mcp_dir.is_dir():
        for mpath in sorted(mcp_dir.iterdir()):
            if mpath.suffix in (".json", ".yaml", ".yml"):
                mcp_resources.append(
                    {
                        "name": mpath.name,
                        "provenance": "mcp_resource",
                    }
                )
    if not mcp_resources:
        mcp_resources.append(
            {
                "provenance": "mcp_resource",
                "present": False,
                "reason": "no_mcp_config_found",
            }
        )

    payload = {
        "workspace": str(ws),
        "files": {
            "count": len(files),
            "total_size": total_size,
            "entries": files,
        },
        "git": git_meta,
        "traces": {
            "count": len(traces),
            "entries": traces,
        },
        "mcp_resources": mcp_resources,
        "symbols": symbol_inventory.model_dump(mode="json", by_alias=True),
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@workspace_app.command("search")
def workspace_search(
    query: str = typer.Argument(..., help="Text to search for in workspace files"),
    path: Optional[str] = typer.Option(None, "--path", help="Sub-path to restrict search"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Search workspace files for a text pattern (ripgrep with pathlib fallback)."""
    import json as _json
    import shutil
    import subprocess

    ws = _workspace(workspace)
    search_root = ws
    if path:
        candidate = (ws / path).resolve()
        # Path confinement: reject symlink escapes and out-of-workspace paths
        try:
            candidate.relative_to(ws.resolve())
        except ValueError:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Path escapes workspace: {path}"), json_output)
            return
        if not candidate.exists():
            _out(err(ArcErrorCode.INVALID_INPUT, f"Path not found: {path}"), json_output)
            return
        search_root = candidate

    results: list[dict] = []

    # Try ripgrep first
    if shutil.which("rg"):
        try:
            proc = subprocess.run(
                ["rg", "--json", "--", query, str(search_root)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    obj = _json.loads(line)
                    if obj.get("type") == "match":
                        data = obj.get("data", {})
                        results.append(
                            {
                                "file": data.get("path", {}).get("text", ""),
                                "line": data.get("line_number", 0),
                                "match": data.get("lines", {}).get("text", "").rstrip("\n"),
                            }
                        )
                except _json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, OSError):
            pass  # fall through to pathlib

    # Pathlib fallback
    if not results:
        for f in search_root.rglob("*"):
            if not f.is_file():
                continue
            try:
                text = f.read_text(errors="replace")
            except OSError:
                continue
            for i, line_text in enumerate(text.splitlines(), start=1):
                if query in line_text:
                    results.append(
                        {
                            "file": str(f.relative_to(ws)),
                            "line": i,
                            "match": line_text.strip(),
                        }
                    )

    payload = {"workspace": str(ws), "query": query, "results": results}
    if json_output:
        _out(ok(payload, workspace=str(ws)), json_output)
        return
    if not results:
        console.print(f"No matches for {query!r}")
        return
    for r in results:
        console.print(f"{r['file']}:{r['line']}: {r['match']}")
