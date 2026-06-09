"""arc git-native — git-native agent workflow commands (R88a/R88b)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from ._subapps import git_native_app

console = Console()

# Branch name must be git-safe
_BRANCH_RE = re.compile(r"^[A-Za-z0-9_.\-/]{1,120}$")


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


@git_native_app.command("init")
def git_init(
    workspace: str = typer.Option("", "--workspace", "-w", help="Workspace root (default: cwd)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON"),
) -> None:
    """Initialize git in the workspace if not already initialized."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    git_dir = ws / ".git"

    if git_dir.exists():
        msg = {"ok": True, "message": f"git already initialized at {ws}", "workspace": str(ws)}
    else:
        result = _run_git(["init"], ws)
        if result.returncode != 0:
            typer.echo(f"[red]git init failed:[/red] {result.stderr.strip()}", err=True)
            raise typer.Exit(1)
        msg = {"ok": True, "message": f"git initialized at {ws}", "workspace": str(ws)}

    if json_output:
        print(json.dumps(msg))
    else:
        typer.echo(msg["message"])


@git_native_app.command("branch")
def git_branch(
    session_id: str = typer.Argument(..., help="Session ID to create a branch for"),
    workspace: str = typer.Option("", "--workspace", "-w", help="Workspace root (default: cwd)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON"),
) -> None:
    """Create or switch to an auto-branch for a session (arc/session-<id>)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()

    # Sanitize session_id to a safe branch suffix
    safe = re.sub(r"[^A-Za-z0-9_.\-]", "-", session_id)[:60]
    branch = f"arc/session-{safe}"

    # Verify it's a valid branch name
    if not _BRANCH_RE.match(branch):
        console.print(
            f"[red]Invalid branch name derived from session_id: {branch!r}[/red]", err=True
        )
        raise typer.Exit(1)

    # Ensure git repo exists
    if not (ws / ".git").exists():
        console.print("[red]Not a git repo. Run `arc git-native init` first.[/red]", err=True)
        raise typer.Exit(1)

    # Check if branch already exists
    check = _run_git(["rev-parse", "--verify", branch], ws)
    if check.returncode == 0:
        # Already exists — switch
        switch = _run_git(["checkout", branch], ws)
        existed = True
    else:
        # Create and switch
        switch = _run_git(["checkout", "-b", branch], ws)
        existed = False

    if switch.returncode != 0:
        typer.echo(
            f"[red]Failed to {'switch to' if existed else 'create'} branch:[/red] {switch.stderr.strip()}",
            err=True,
        )
        raise typer.Exit(1)

    msg = {
        "ok": True,
        "branch": branch,
        "session_id": session_id,
        "existed": existed,
        "workspace": str(ws),
    }

    if json_output:
        print(json.dumps(msg))
    else:
        action = "Switched to existing" if existed else "Created and switched to"
        console.print(f"{action} branch: [bold]{branch}[/bold]")


@git_native_app.command("auto-commit")
def git_auto_commit(
    message: str = typer.Option("arc: agent file edit", "--message", "-m", help="Commit message"),
    workspace: str = typer.Option("", "--workspace", "-w", help="Workspace root (default: cwd)"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Stage all changes and commit — called after every agent file edit (R88b)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()

    if not (ws / ".git").exists():
        console.print("[red]Not a git repo.[/red]", err=True)
        raise typer.Exit(1)

    stage = _run_git(["add", "-A"], ws)
    if stage.returncode != 0:
        typer.echo(f"[red]git add failed:[/red] {stage.stderr.strip()}", err=True)
        raise typer.Exit(1)

    # Check if there's anything to commit
    diff = _run_git(["diff", "--cached", "--quiet"], ws)
    if diff.returncode == 0:
        msg = {"ok": True, "committed": False, "message": "nothing to commit"}
        if json_output:
            print(json.dumps(msg))
        else:
            typer.echo("[dim]Nothing to commit.[/dim]")
        return

    commit = _run_git(["commit", "-m", message], ws)
    if commit.returncode != 0:
        console.print(f"[red]git commit failed:[/red] {commit.stderr.strip()}", err=True)
        raise typer.Exit(1)

    # Extract commit SHA
    sha_result = _run_git(["rev-parse", "--short", "HEAD"], ws)
    sha = sha_result.stdout.strip() if sha_result.returncode == 0 else "unknown"

    msg = {"ok": True, "committed": True, "sha": sha, "message": message}
    if json_output:
        print(json.dumps(msg))
    else:
        typer.echo(f"Committed [bold]{sha}[/bold]: {message}")


@git_native_app.command("auto-revert")
def git_auto_revert(
    workspace: str = typer.Option("", "--workspace", "-w", help="Workspace root (default: cwd)"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Revert uncommitted changes on run failure — discard unstaged edits (R88b)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()

    if not (ws / ".git").exists():
        console.print("[red]Not a git repo.[/red]", err=True)
        raise typer.Exit(1)

    # Reset staged changes
    reset = _run_git(["reset", "--hard", "HEAD"], ws)
    if reset.returncode != 0:
        typer.echo(f"[red]git reset failed:[/red] {reset.stderr.strip()}", err=True)
        raise typer.Exit(1)

    # Clean untracked files (-fd: force + directories)
    clean = _run_git(["clean", "-fd"], ws)

    msg = {"ok": True, "reverted": True, "clean_output": clean.stdout.strip()}
    if json_output:
        print(json.dumps(msg))
    else:
        console.print("[yellow]Reverted uncommitted changes.[/yellow]")
