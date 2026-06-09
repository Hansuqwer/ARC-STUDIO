"""arc index — local codebase index build + search (R84)."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ._subapps import index_app

console = Console()


@index_app.command("build")
def index_build(
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Build a local SQLite codebase index for the workspace (R84a)."""
    from ..index import CodebaseIndex

    ws = Path(workspace).resolve() if workspace else Path.cwd()
    if not json_output:
        console.print(f"[dim]Indexing {ws} ...[/dim]")

    idx = CodebaseIndex(ws)
    stats = idx.build()

    if json_output:
        print(json.dumps({"ok": True, "workspace": str(ws), **stats}))
    else:
        console.print(
            f"[green]Indexed[/green] {stats['indexed']} files "
            f"({stats['skipped']} skipped) in {stats['elapsed_s']}s"
        )


@index_app.command("search")
def index_search(
    query: str = typer.Argument(..., help="Search query"),
    workspace: str = typer.Option("", "--workspace", "-w"),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Search the local codebase index (R84b). Build first with `arc index build`."""
    from ..index import CodebaseIndex

    ws = Path(workspace).resolve() if workspace else Path.cwd()
    idx = CodebaseIndex(ws)
    stats = idx.stats()

    if stats["file_count"] == 0:
        typer.echo("Index is empty. Run `arc index build` first.", err=True)
        raise typer.Exit(1)

    results = idx.search(query, limit=limit)

    if json_output:
        print(
            json.dumps(
                {
                    "ok": True,
                    "query": query,
                    "results": [
                        {
                            "path": r.path,
                            "language": r.language,
                            "score": r.score,
                            "symbols": r.symbols_preview,
                            "preview": r.content_preview,
                        }
                        for r in results
                    ],
                }
            )
        )
        return

    if not results:
        console.print(f"[dim]No results for '{query}'[/dim]")
        return

    table = Table(title=f"Index search: {query!r}", show_header=True)
    table.add_column("Path")
    table.add_column("Lang")
    table.add_column("Symbols")
    for r in results:
        table.add_row(r.path, r.language, r.symbols_preview[:40])
    console.print(table)


@index_app.command("stats")
def index_stats(
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show index statistics."""
    from ..index import CodebaseIndex
    import time

    ws = Path(workspace).resolve() if workspace else Path.cwd()
    idx = CodebaseIndex(ws)
    stats = idx.stats()

    if json_output:
        print(json.dumps({"ok": True, "workspace": str(ws), **stats}))
        return

    console.print(f"Files indexed : {stats['file_count']}")
    if stats["last_built"]:
        age = time.time() - stats["last_built"]
        console.print(f"Last built    : {age:.0f}s ago")
    console.print(f"DB path       : {stats['db_path']}")
