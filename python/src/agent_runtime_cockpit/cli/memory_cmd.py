"""arc memory — Fernet-encrypted persistent project knowledge store (R90)."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import typer
from cryptography.fernet import Fernet
from rich.console import Console

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import _out
from ._subapps import memory_app

console = Console()

_SCHEMA = """
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS notes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    key       TEXT,
    content   TEXT NOT NULL,  -- Fernet-encrypted
    tags      TEXT,           -- space-separated plaintext tags
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_key ON notes(key);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(key, tags);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""


def _get_memory_path(workspace: Path) -> Path:
    override = os.environ.get("ARC_MEMORY_DIR")
    base = Path(override).expanduser() if override else Path.home() / ".arc" / "memory"
    base.mkdir(parents=True, exist_ok=True)
    import hashlib

    ws_hash = hashlib.sha256(str(workspace.resolve()).encode()).hexdigest()[:16]
    return base / f"{ws_hash}.db"


def _get_fernet() -> Fernet:
    from ..auth.manager import _load_key

    return Fernet(_load_key())


def _init_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_SCHEMA)


@memory_app.command("save")
def memory_save(
    key: str = typer.Argument(..., help="Note key/name"),
    content: str = typer.Argument(..., help="Note content to save"),
    tags: str = typer.Option("", "--tags", help="Space-separated tags"),
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Save an encrypted note to persistent memory (R90a)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    db = _get_memory_path(ws)
    _init_db(db)
    fernet = _get_fernet()
    enc = fernet.encrypt(content.encode()).decode()
    now = time.time()

    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO notes (key, content, tags, created_at, updated_at) VALUES (?,?,?,?,?)",
            (key, enc, tags, now, now),
        )
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO notes_fts(rowid, key, tags) VALUES (?,?,?)", (row_id, key, tags))

    msg = {"key": key, "id": row_id, "state": "success"}
    if json_output:
        _out(ok(msg), json_output)
    else:
        console.print(f"[green]Saved[/green] note: {key!r}")


@memory_app.command("load")
def memory_load(
    key: str = typer.Argument(..., help="Note key to load"),
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Load a note from memory (R90a)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    db = _get_memory_path(ws)
    if not db.exists():
        _out(
            err(ArcErrorCode.RUN_NOT_FOUND, "Memory store empty.", {"state": "empty"}), json_output
        )
        raise typer.Exit(1)

    fernet = _get_fernet()
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, key, content, tags, created_at FROM notes WHERE key=? ORDER BY id DESC LIMIT 1",
            (key,),
        ).fetchall()

    if not rows:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Note '{key}' not found.", {"key": key}), json_output)
        raise typer.Exit(1)

    row_id, rkey, enc, tags, created = rows[0]
    try:
        content = fernet.decrypt(enc.encode()).decode()
    except Exception:
        _out(err(ArcErrorCode.INTERNAL_ERROR, "Decryption failed."), json_output)
        raise typer.Exit(1)

    if json_output:
        _out(
            ok(
                {
                    "id": row_id,
                    "key": rkey,
                    "content": content,
                    "tags": tags,
                    "created_at": created,
                    "state": "success",
                }
            ),
            json_output,
        )
    else:
        console.print(f"[bold]{rkey}[/bold]\n{content}")


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query (matches key + tags)"),
    workspace: str = typer.Option("", "--workspace", "-w"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Search saved notes by key and tags (R90b)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    db = _get_memory_path(ws)
    if not db.exists():
        if json_output:
            _out(ok({"query": query, "results": [], "state": "empty"}), json_output)
        else:
            console.print("[dim]Memory store empty.[/dim]")
        return

    with sqlite3.connect(db) as conn:
        try:
            rows = conn.execute(
                """SELECT n.id, n.key, n.tags, n.created_at
                   FROM notes_fts fts
                   JOIN notes n ON n.id = fts.rowid
                   WHERE notes_fts MATCH ?
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            rows = conn.execute(
                "SELECT id, key, tags, created_at FROM notes WHERE key LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()

    results = [{"id": r[0], "key": r[1], "tags": r[2], "created_at": r[3]} for r in rows]

    if json_output:
        _out(
            ok(
                {"query": query, "results": results, "state": "empty" if not results else "success"}
            ),
            json_output,
        )
        return

    if not results:
        console.print("[dim]No matching notes.[/dim]")
    else:
        for r in results:
            console.print(f"  [{r['id']}] [cyan]{r['key']}[/cyan]  tags: {r['tags'] or '—'}")


@memory_app.command("list")
def memory_list(
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List all saved notes."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    db = _get_memory_path(ws)
    if not db.exists():
        if json_output:
            _out(ok({"notes": [], "state": "empty"}), json_output)
        else:
            console.print("[dim]Memory store empty.[/dim]")
        return

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, key, tags, created_at FROM notes ORDER BY created_at DESC LIMIT 100"
        ).fetchall()

    notes = [{"id": r[0], "key": r[1], "tags": r[2], "created_at": r[3]} for r in rows]
    if json_output:
        _out(ok({"notes": notes, "state": "empty" if not notes else "success"}), json_output)
    else:
        for r in notes:
            console.print(f"  [{r['id']}] [cyan]{r['key']}[/cyan]")


@memory_app.command("clear")
def memory_clear(
    workspace: str = typer.Option("", "--workspace", "-w"),
    yes: bool = typer.Option(False, "--yes", help="Confirm clearing project memory"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Clear all saved notes from persistent memory."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    if not yes:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                "Clearing project memory requires --yes.",
                {"workspace": str(ws)},
            ),
            json_output,
        )
        raise typer.Exit(1)
    db = _get_memory_path(ws)
    deleted = 0
    if db.exists():
        _init_db(db)
        with sqlite3.connect(db) as conn:
            deleted = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            conn.execute("DELETE FROM notes")
            conn.execute("DELETE FROM notes_fts")
    payload = {"cleared": True, "deleted": deleted, "state": "empty"}
    if json_output:
        _out(ok(payload), json_output)
    else:
        console.print(f"[dim]Memory cleared ({deleted} note(s)).[/dim]")
