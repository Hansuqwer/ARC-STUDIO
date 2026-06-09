"""arc context — automatic context retrieval for prompts (R85)."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ._subapps import context_app

console = Console()

# Session-scoped context attachment file
_CONTEXT_FILE_NAME = ".arc_context_attach.json"


def _context_file(workspace: Path) -> Path:
    return workspace / _CONTEXT_FILE_NAME


@context_app.command("suggest")
def context_suggest(
    prompt: str = typer.Argument(..., help="Prompt to find context for"),
    workspace: str = typer.Option("", "--workspace", "-w"),
    limit: int = typer.Option(5, "--limit", "-n", min=1, max=20),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Suggest relevant context files for a prompt using the codebase index (R85a)."""
    from ..index import CodebaseIndex

    ws = Path(workspace).resolve() if workspace else Path.cwd()
    idx = CodebaseIndex(ws)
    stats = idx.stats()

    if stats["file_count"] == 0:
        typer.echo("Index empty. Run `arc index build` first.", err=True)
        raise typer.Exit(1)

    results = idx.search(prompt, limit=limit)

    if json_output:
        print(
            json.dumps(
                {
                    "ok": True,
                    "prompt": prompt,
                    "suggestions": [
                        {"path": r.path, "language": r.language, "relevance": abs(r.score)}
                        for r in results
                    ],
                }
            )
        )
        return

    if not results:
        console.print("[dim]No relevant context found.[/dim]")
        return

    console.print(f"[bold]Context suggestions for:[/bold] {prompt!r}")
    for i, r in enumerate(results, 1):
        console.print(f"  {i}. [cyan]{r.path}[/cyan] ({r.language})")


@context_app.command("attach")
def context_attach(
    paths: list[str] = typer.Argument(..., help="File paths to attach as context"),
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Attach files as context for the next agent run (R85b)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    ctx_file = _context_file(ws)

    existing = []
    if ctx_file.exists():
        try:
            existing = json.loads(ctx_file.read_text())
        except Exception:
            existing = []

    added = []
    for p in paths:
        rel = str(Path(p))
        if rel not in existing:
            existing.append(rel)
            added.append(rel)

    ctx_file.write_text(json.dumps(existing, indent=2))

    msg = {"ok": True, "attached": added, "total": len(existing), "file": str(ctx_file)}
    if json_output:
        print(json.dumps(msg))
    else:
        console.print(f"Attached {len(added)} file(s). Total context: {len(existing)}")


@context_app.command("list")
def context_list(
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List currently attached context files."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    ctx_file = _context_file(ws)

    attached = []
    if ctx_file.exists():
        try:
            attached = json.loads(ctx_file.read_text())
        except Exception:
            attached = []

    if json_output:
        print(json.dumps({"ok": True, "attached": attached}))
        return

    if not attached:
        console.print("[dim]No context attached.[/dim]")
    else:
        for p in attached:
            console.print(f"  [cyan]{p}[/cyan]")


@context_app.command("clear")
def context_clear(
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Clear all attached context."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    ctx_file = _context_file(ws)
    if ctx_file.exists():
        ctx_file.unlink()
    msg = {"ok": True, "cleared": True}
    if json_output:
        print(json.dumps(msg))
    else:
        console.print("[dim]Context cleared.[/dim]")
