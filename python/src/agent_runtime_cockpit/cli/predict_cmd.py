"""arc predict — next-edit autocomplete stub (R83a).

Predicts the next likely edit given a file and cursor position.
Currently a research-grade stub: uses simple heuristic (last function/class
call site pattern matching). No live provider call unless explicitly gated.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import _out
from ._subapps import predict_app

console = Console()

_CALL_RE = re.compile(r"(\w+)\s*\(")


def _heuristic_next_edit(text: str, line: int) -> list[str]:
    """Simple heuristic: suggest identifiers seen near the cursor line."""
    lines = text.splitlines()
    window = lines[max(0, line - 5) : line + 5]
    seen: list[str] = []
    for ln in window:
        seen.extend(m.group(1) for m in _CALL_RE.finditer(ln))
    # deduplicate preserving order
    uniq: list[str] = []
    for s in seen:
        if s not in uniq and s not in {"if", "for", "while", "def", "class", "return"}:
            uniq.append(s)
    return uniq[:5]


@predict_app.command("next-edit")
def predict_next_edit(
    file: str = typer.Argument(..., help="File path to predict next edit for"),
    line: int = typer.Option(1, "--line", "-l", help="Cursor line (1-indexed)", min=1),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Predict the next likely edit at a cursor position (research-grade stub).

    This is a heuristic autocomplete stub. A future version will call a
    local LM (requires ARC_REAL_RUNTIME_SMOKE=1 and a configured provider).
    """
    path = Path(file)
    if not path.exists():
        _out(err(ArcErrorCode.WORKSPACE_NOT_FOUND, f"File not found: {file}"), json_output)
        raise typer.Exit(1)

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot read file: {exc}"), json_output)
        raise typer.Exit(1)

    total_lines = len(text.splitlines())
    state = "success"
    details: dict[str, object] = {}
    if total_lines == 0:
        state = "empty"
    elif line > total_lines:
        state = "degraded"
        details["reason"] = "line_out_of_range"
        details["line_count"] = total_lines
        line = total_lines

    suggestions = _heuristic_next_edit(text, max(0, line - 1))
    payload = {
        "file": str(path),
        "line": line,
        "suggestions": suggestions,
        "mode": "heuristic-stub",
        "state": state,
        **details,
    }

    if json_output:
        _out(ok(payload), json_output)
        return

    if not suggestions:
        console.print("[dim]No predictions at this position.[/dim]")
    else:
        console.print(f"[bold]Next-edit predictions[/bold] (heuristic) at {file}:{line}")
        for i, s in enumerate(suggestions, 1):
            console.print(f"  {i}. {s}")
        console.print("[dim](stub — live LM requires ARC_REAL_RUNTIME_SMOKE=1)[/dim]")
