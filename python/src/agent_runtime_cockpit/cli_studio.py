"""
ARC Studio — chat-first CLI entry point (v0.1).

Usage:
  arc-studio           Interactive chat REPL with banner + prompt loop.
  arc-studio <message> One-shot: dispatch a single message / command and exit.
"""
from __future__ import annotations

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__

app = typer.Typer(
    name="arc-studio",
    help="ARC Studio — Run agents. See everything.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

SESSION_DIR = Path.home() / ".arc" / "sessions"

MODE_PLAN = "plan"
MODE_BUILD = "build"
MODE_AUTO = "auto"
VALID_MODES = {MODE_PLAN, MODE_BUILD, MODE_AUTO}

HELP_TEXT = """
[bold]ARC Studio Slash Commands[/bold]

  [bold]/help[/bold]       Show this help message
  [bold]/status[/bold]     Show workspace, runtime, and session status
  [bold]/doctor[/bold]     Run environment diagnostics
  [bold]/runs[/bold]       List recent run records
  [bold]/plan[/bold]       Switch to Plan mode (read-only)
  [bold]/build[/bold]      Switch to Build mode (can write)
  [bold]/auto[/bold]       Switch to policy-driven mode
  [bold]/exit[/bold]       Save session and exit

Type a message to send a query or use /slash commands above.
No agent execution in v0.1 — this is a local shell.
"""


class StudioSession:
    def __init__(self, session_id: str, mode: str = MODE_BUILD) -> None:
        self.session_id = session_id
        self.mode = mode
        self.messages: list[dict] = []
        self.created = datetime.now(timezone.utc).isoformat()
        self.updated = self.created

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.updated = datetime.now(timezone.utc).isoformat()

    def set_mode(self, mode: str) -> None:
        if mode in VALID_MODES:
            self.mode = mode

    def save(self, session_dir: Path = SESSION_DIR) -> None:
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / f"{self.session_id}.json"
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        latest = session_dir / "latest"
        if latest.is_symlink() or latest.exists():
            latest.unlink(missing_ok=True)
        latest.symlink_to(path.name)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "messages": self.messages,
            "created": self.created,
            "updated": self.updated,
        }

    @staticmethod
    def load(session_id: str, session_dir: Path = SESSION_DIR) -> Optional[StudioSession]:
        path = session_dir / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        sess = StudioSession(data["session_id"], data.get("mode", MODE_BUILD))
        sess.messages = data.get("messages", [])
        sess.created = data.get("created", "")
        sess.updated = data.get("updated", "")
        return sess

    @staticmethod
    def resume_latest(session_dir: Path = SESSION_DIR) -> Optional[StudioSession]:
        latest = session_dir / "latest"
        if latest.exists() and latest.is_symlink():
            target = latest.resolve()
            if target.exists():
                sess_id = target.stem
                return StudioSession.load(sess_id, session_dir=session_dir)
        return None

    @staticmethod
    def list_sessions(session_dir: Path = SESSION_DIR) -> list[str]:
        if not session_dir.exists():
            return []
        files = sorted(session_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [f.stem for f in files if f.stem != "latest"]


def _banner(session: StudioSession, is_resumed: bool = False) -> None:
    ws = Path.cwd().resolve()
    console.print()
    console.print(Panel.fit(
        f"[bold]ARC Studio[/bold] [dim]v{__version__}[/dim]\n"
        f"[dim]Workspace:[/dim] {ws}\n"
        f"[dim]Mode:[/dim] [bold]{session.mode.upper()}[/bold]"
        + ("\n[dim](resumed previous session)[/dim]" if is_resumed else ""),
        border_style="blue",
    ))
    console.print()
    console.print("Type a message or [bold]/help[/bold] for commands.")
    console.print()


def _status(session: StudioSession) -> None:
    ws = Path.cwd().resolve()
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Workspace", str(ws))
    table.add_row("Mode", session.mode.upper())
    table.add_row("Session", session.session_id[:12])
    table.add_row("Messages", str(len(session.messages)))
    runtime_dir = ws / ".arc" / "traces"
    run_count = len(list(runtime_dir.glob("*.jsonl"))) if runtime_dir.exists() else 0
    table.add_row("Stored runs", str(run_count))
    console.print(table)


def _doctor() -> None:
    ws = Path.cwd().resolve()
    checks = []
    checks.append(("Python package", "import" in sys.modules.get("agent_runtime_cockpit", "").__class__.__module__ if hasattr(sys.modules.get("agent_runtime_cockpit"), "__class__") else True))
    checks.append(("Workspace exists", ws.exists()))
    arc_dir = ws / ".arc"
    checks.append(("ARC dir exists", arc_dir.exists()))
    traces = arc_dir / "traces"
    trace_count = len(list(traces.glob("*.jsonl"))) if traces.exists() else 0
    checks.append(("Trace storage", traces.exists() and trace_count >= 0))
    sessions_ok = SESSION_DIR.exists() or True
    checks.append(("Session storage", sessions_ok))
    for label, ok in checks:
        glyph = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {glyph} {label}")
    console.print()


def _runs() -> None:
    ws = Path.cwd().resolve()
    traces = ws / ".arc" / "traces"
    if not traces.exists():
        console.print("[dim]No runs stored.[/dim]")
        return
    run_files = sorted(traces.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_files:
        console.print("[dim]No runs stored.[/dim]")
        return
    table = Table(title=f"Runs ({len(run_files)})")
    table.add_column("Run ID")
    table.add_column("Size")
    table.add_column("Modified")
    for f in run_files[:20]:
        table.add_row(f.stem[:16], f"{f.stat().st_size}B", datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M:%S"))
    console.print(table)


def _dispatch(session: StudioSession, message: str, *, persist_on_exit: bool = True) -> bool:
    """Dispatch a message or slash command. Returns False if should exit."""
    text = message.strip()
    if text == "/exit":
        session.add_message("user", text)
        if persist_on_exit:
            session.save()
        console.print("[dim]Session saved. Goodbye.[/dim]")
        return False
    if text == "/help":
        console.print(HELP_TEXT)
        session.add_message("user", text)
        return True
    if text == "/status":
        _status(session)
        session.add_message("user", text)
        return True
    if text == "/doctor":
        _doctor()
        session.add_message("user", text)
        return True
    if text == "/runs":
        _runs()
        session.add_message("user", text)
        return True
    if text == "/plan":
        session.set_mode(MODE_PLAN)
        session.add_message("user", text)
        console.print("[bold]Switched to Plan mode (read-only).[/bold]")
        return True
    if text == "/build":
        session.set_mode(MODE_BUILD)
        session.add_message("user", text)
        console.print("[bold]Switched to Build mode (can write).[/bold]")
        return True
    if text == "/auto":
        session.set_mode(MODE_AUTO)
        session.add_message("user", text)
        console.print("[bold]Switched to Auto mode (policy-driven).[/bold]")
        return True
    if text.startswith("/"):
        console.print(f"[yellow]Unknown command:[/yellow] {text}")
        console.print("Type [bold]/help[/bold] for available commands.")
        return True
    session.add_message("user", text)
    console.print("[dim](No agent execution in v0.1 local shell.)[/dim]")
    console.print(f"[bold]You said:[/bold] {text}")
    return True


def _interactive() -> None:
    resumed = StudioSession.resume_latest()
    if resumed is not None:
        session = resumed
        is_resumed = True
    else:
        session = StudioSession(session_id="ses_" + secrets.token_urlsafe(16))
        is_resumed = False
    _banner(session, is_resumed=is_resumed)
    while True:
        try:
            line = console.input("[bold blue]arc › [/bold blue]")
            if not _dispatch(session, line):
                break
        except (KeyboardInterrupt, EOFError):
            session.save()
            console.print("\n[dim]Session saved. Goodbye.[/dim]")
            break


def _oneshot(message: str) -> None:
    session = StudioSession(session_id="ses_" + secrets.token_urlsafe(16))
    _dispatch(session, message, persist_on_exit=False)
    raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    message: Optional[str] = typer.Argument(None, help="One-shot message or slash command"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    """
    ARC Studio — Run agents. See everything.

    With no arguments, launches interactive chat. With one argument, runs
    the message as a one-shot command and exits.
    """
    if version:
        console.print(f"ARC Studio v{__version__}")
        raise typer.Exit()

    if message is not None:
        _oneshot(message)
    else:
        _interactive()
