"""arc context — automatic context retrieval for prompts (R85)."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import _out
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
        payload = {
            "prompt": prompt,
            "suggestions": [],
            "state": "degraded",
            "reason": "index_empty",
        }
        if json_output:
            _out(ok(payload), json_output)
            return
        _out(
            err(
                ArcErrorCode.CONTEXT_PROVIDER_ERROR,
                "Index empty. Run `arc index build` first.",
                payload,
            ),
            json_output,
        )
        raise typer.Exit(1)

    results = idx.search(prompt, limit=limit)

    if json_output:
        _out(
            ok(
                {
                    "prompt": prompt,
                    "suggestions": [
                        {"path": r.path, "language": r.language, "relevance": abs(r.score)}
                        for r in results
                    ],
                    "state": "empty" if not results else "success",
                }
            ),
            json_output,
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

    msg = {"attached": added, "total": len(existing), "file": str(ctx_file)}
    if json_output:
        _out(ok(msg), json_output)
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
        _out(
            ok({"attached": attached, "state": "empty" if not attached else "success"}), json_output
        )
        return

    if not attached:
        console.print("[dim]No context attached.[/dim]")
    else:
        for p in attached:
            console.print(f"  [cyan]{p}[/cyan]")


@context_app.command("clear")
def context_clear(
    workspace: str = typer.Option("", "--workspace", "-w"),
    yes: bool = typer.Option(False, "--yes", help="Confirm clearing attached context"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Clear all attached context."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    ctx_file = _context_file(ws)
    if not yes:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                "Clearing attached context requires --yes.",
                {"workspace": str(ws)},
            ),
            json_output,
        )
        raise typer.Exit(1)
    if ctx_file.exists():
        ctx_file.unlink()
    msg = {"cleared": True, "state": "empty"}
    if json_output:
        _out(ok(msg), json_output)
    else:
        console.print("[dim]Context cleared.[/dim]")
