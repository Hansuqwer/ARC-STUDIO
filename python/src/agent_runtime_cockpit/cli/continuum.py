"""arc continuum — list and resume persisted sessions (R86b)."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from ..auth.manager import _load_key
from ._subapps import continuum_app

console = Console()


@continuum_app.command("list")
def continuum_list(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON array"),
    sessions_dir: str = typer.Option("", "--sessions-dir", help="Override sessions directory"),
) -> None:
    """List all persisted ARC sessions."""
    import os

    if sessions_dir:
        os.environ["ARC_STUDIO_SESSIONS_DIR"] = sessions_dir

    from ..continuum.store import SessionStore

    base = SessionStore._get_sessions_dir()
    if not base.exists():
        if json_output:
            console.print("[]")
        else:
            console.print("[dim]No sessions found.[/dim]")
        return

    rows = []
    for session_dir in sorted(base.iterdir()):
        if not session_dir.is_dir():
            continue
        db = session_dir / "state.db"
        if not db.exists():
            continue
        rows.append({"session_id": session_dir.name, "db_path": str(db)})

    if json_output:
        print(json.dumps(rows, indent=2))
        return

    if not rows:
        console.print("[dim]No sessions found.[/dim]")
        return

    table = Table(title="ARC Sessions", show_header=True)
    table.add_column("Session ID")
    table.add_column("DB Path")
    for row in rows:
        table.add_row(row["session_id"], row["db_path"])
    console.print(table)


@continuum_app.command("resume")
def continuum_resume(
    session_id: str = typer.Argument(..., help="Session ID to resume"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON summary"),
    sessions_dir: str = typer.Option("", "--sessions-dir", help="Override sessions directory"),
) -> None:
    """Show transcript and state for a persisted session (resume point)."""
    import os

    if sessions_dir:
        os.environ["ARC_STUDIO_SESSIONS_DIR"] = sessions_dir

    from ..continuum.store import SessionStore

    key = _load_key()
    db_path = SessionStore._get_sessions_dir() / session_id / "state.db"
    if not db_path.exists():
        console.print(f"[red]Session '{session_id}' not found.[/red]", err=True)
        raise typer.Exit(1)

    store = SessionStore(session_id, key)
    transcript = store.load_transcript()
    ui_state = store.load_ui_state()
    run_ids = store.list_runs()

    if json_output:
        data = {
            "session_id": session_id,
            "transcript_entries": len(transcript),
            "run_ids": run_ids,
            "ui_state_keys": list(ui_state.keys()),
        }
        print(json.dumps(data, indent=2))
        return

    console.print(f"[bold]Session:[/bold] {session_id}")
    console.print(f"  Transcript entries : {len(transcript)}")
    console.print(f"  Runs               : {run_ids or '(none)'}")
    console.print(f"  UI state keys      : {list(ui_state.keys()) or '(empty)'}")
    if transcript:
        console.print("\n[bold]Last message:[/bold]")
        last = transcript[-1]
        console.print(f"  [{last.role}] {last.content[:120]}")
