"""arc diff — inline diff viewer and interactive patch apply (R89a)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax

from ._subapps import diff_app

console = Console()

# Hunk header pattern: @@ -a,b +c,d @@
_HUNK_RE = re.compile(r"^@@[^@]*@@.*$", re.MULTILINE)


def _parse_hunks(patch: str) -> list[str]:
    """Split a unified diff into individual hunks."""
    lines = patch.splitlines(keepends=True)
    hunks: list[str] = []
    header_lines: list[str] = []
    current: list[str] = []
    in_header = True

    for line in lines:
        if line.startswith("diff --git") or line.startswith("--- ") or line.startswith("+++ "):
            if in_header:
                header_lines.append(line)
            else:
                if current:
                    hunks.append("".join(header_lines + current))
                header_lines = [line]
                current = []
            in_header = True
        elif line.startswith("@@"):
            if current:
                hunks.append("".join(header_lines + current))
            current = [line]
            in_header = False
        else:
            if not in_header:
                current.append(line)
            else:
                header_lines.append(line)

    if current:
        hunks.append("".join(header_lines + current))

    return hunks if hunks else [patch]


@diff_app.command("apply")
def diff_apply(
    patch_file: str = typer.Argument(..., help="Path to unified diff file to apply"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Ask per-hunk accept/reject"
    ),
    workspace: str = typer.Option("", "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Apply a unified diff patch file, optionally interactively per-hunk.

    Non-interactive: applies the whole patch via git apply.
    Interactive: shows each hunk and asks y/n/q.
    """
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    patch_path = Path(patch_file)

    if not patch_path.exists():
        console.print(f"[red]Patch file not found: {patch_path}[/red]", err=True)
        raise typer.Exit(1)

    patch_text = patch_path.read_text()

    if not interactive:
        # Non-interactive: apply whole patch
        result = subprocess.run(
            ["git", "apply", str(patch_path)],
            cwd=str(ws),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]git apply failed:[/red] {result.stderr.strip()}", err=True)
            raise typer.Exit(1)
        msg = {"ok": True, "applied": True, "patch": str(patch_path)}
        if json_output:
            print(json.dumps(msg))
        else:
            console.print(f"[green]Applied:[/green] {patch_path}")
        return

    # Interactive: present each hunk
    hunks = _parse_hunks(patch_text)
    applied = []
    skipped = []

    for i, hunk in enumerate(hunks, 1):
        console.print(f"\n[bold]Hunk {i}/{len(hunks)}:[/bold]")
        console.print(Syntax(hunk, "diff", theme="monokai", line_numbers=False))

        if not sys.stdin.isatty():
            # Non-TTY (test/pipe): auto-apply all
            choice = "y"
        else:
            choice = typer.prompt("Apply this hunk? [y/n/q]", default="y").strip().lower()

        if choice == "q":
            console.print("[yellow]Aborted.[/yellow]")
            break
        elif choice == "y":
            # Write hunk to temp file and apply
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".patch", mode="w", delete=False) as f:
                f.write(hunk)
                tmp = Path(f.name)
            try:
                r = subprocess.run(
                    ["git", "apply", str(tmp)], cwd=str(ws), capture_output=True, text=True
                )
                if r.returncode == 0:
                    applied.append(i)
                else:
                    console.print(f"[red]Hunk {i} failed:[/red] {r.stderr.strip()}")
                    skipped.append(i)
            finally:
                tmp.unlink(missing_ok=True)
        else:
            skipped.append(i)

    msg = {"ok": True, "applied_hunks": applied, "skipped_hunks": skipped}
    if json_output:
        print(json.dumps(msg))
    else:
        console.print(f"\nApplied {len(applied)} hunk(s), skipped {len(skipped)}.")
