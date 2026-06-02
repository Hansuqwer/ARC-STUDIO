"""Rich rendering layer for the ARC Studio interactive shell.

The shell's visuals live here so ``chat_repl`` stays orchestration-only. Every
method returns a Rich renderable (or prints via the injected console), which
keeps output deterministic and unit-testable:

    console = Console(record=True, width=80)
    out = Renderer(console)
    out.print(out.startup_panel(session))
    text = console.export_text()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import __version__
from ..runtime.mode import RuntimeMode
from . import theme as _theme

# Slash command -> panel title for commands that read better framed.
_PANEL_TITLES = {
    "help": "Help",
    "status": "Status",
    "session": "Session",
    "model": "Model",
    "tools": "Tools",
}


class Renderer:
    """Builds Rich renderables for the interactive shell."""

    def __init__(self, console: Console | None = None, *, ascii_only: bool | None = None) -> None:
        self._ascii = _theme.ascii_only() if ascii_only is None else ascii_only
        self.console = console or Console(highlight=False)
        self.box = _theme.panel_box(self._ascii)

    def print(self, renderable: RenderableType) -> None:
        self.console.print(renderable)

    def _panel(self, body: str, title: str, style: str) -> Panel:
        return Panel(Text(body), title=title, border_style=style, box=self.box, title_align="left")

    # ── startup ───────────────────────────────────────────────────────────
    def startup_panel(self, session: Any, workspace: Path | None = None) -> Panel:
        ws = (workspace or Path.cwd()).resolve()
        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="left", style="bold")
        grid.add_column(justify="left", overflow="fold")
        for label, value in self._state_rows(session, ws):
            grid.add_row(label, Text(value))
        return Panel(
            grid,
            title=f"ARC Studio v{__version__}",
            border_style="cyan",
            box=self.box,
            title_align="left",
        )

    def command_palette(self) -> Text:
        return Text("  ".join(_theme.PALETTE), style="dim")

    def _state_rows(self, session: Any, ws: Path) -> list[tuple[str, str]]:
        md = session.metadata or {}
        runtime = RuntimeMode.from_legacy(session.runtime_mode).value
        runtime_label = "fake/offline" if runtime == "fake" else runtime
        return [
            ("workspace", str(ws)),
            ("trust", self._trust(ws)),
            ("runtime", runtime_label),
            ("provider", str(md.get("provider") or "none")),
            ("model", str(md.get("provider_model") or "unknown")),
            ("sandbox", "subprocess"),
            ("tools", "on" if session.tools_enabled else "off"),
            ("context", self._context(session)),
            ("session", session.id),
        ]

    @staticmethod
    def _trust(ws: Path) -> str:
        try:
            from ..security.trust import resolve_trust

            return resolve_trust(ws).level.value
        except Exception:  # noqa: BLE001 - startup must stay best-effort
            return "unknown"

    @staticmethod
    def _context(session: Any) -> str:
        ctx = (session.metadata or {}).get("last_context")
        if not isinstance(ctx, dict) or not ctx.get("available"):
            return "unknown"
        pct = ctx.get("usage_pct")
        return f"{pct}%" if pct is not None else "unknown"

    # ── message blocks ──────────────────────────────────────────────────────
    def message_block(self, kind: str, content: str) -> Panel:
        title, style = _theme.BLOCK_STYLES.get(kind, (kind.title(), "white"))
        return self._panel(content, title, style)

    def user_block(self, text: str) -> Panel:
        return self.message_block("user", text)

    def assistant_block(self, text: str) -> Panel:
        return self.message_block("assistant", text)

    def system_block(self, text: str) -> Panel:
        return self.message_block("system", text)

    def warning_block(self, text: str) -> Panel:
        return self.message_block("warning", text)

    def error_block(self, text: str) -> Panel:
        return self.message_block("error", text)

    def tool_block(self, tool: str, summary: str = "", detail: str = "") -> Panel:
        body = summary or tool
        if detail:
            body = f"{body}\n{detail}"
        _title, style = _theme.BLOCK_STYLES["tool"]
        return self._panel(body, f"Tool: {tool}", style)

    def progress_line(self, name: str, payload: dict[str, Any]) -> Text:
        from .chat_repl import _format_progress_event

        return Text(_format_progress_event(name, payload), style="dim")

    def prompt_text(self, session: Any) -> str:
        from .chat_repl import _format_prompt

        return _format_prompt(session)

    # ── command results ─────────────────────────────────────────────────────
    def result_block(self, result: Any) -> RenderableType:
        from .slash_commands import CommandResult

        if not isinstance(result, CommandResult):
            return Text(str(result))
        label, style = _theme.state_style(result.state)
        body = result.output or (
            f"{result.state}: {result.reason}" if result.reason else result.state
        )
        if result.state in {"present", "ok"}:
            return Text(body)
        return self._panel(body, label, style)

    def command_result(self, command: str, result: Any) -> RenderableType:
        """Render a slash command result, framing known commands in a titled panel."""
        from .slash_commands import CommandResult

        name = ""
        clean = command.strip()
        if clean.startswith("/") and len(clean) > 1:
            name = clean[1:].split()[0].lower()
        if isinstance(result, CommandResult):
            state, body = (
                result.state,
                result.output
                or (f"{result.state}: {result.reason}" if result.reason else result.state),
            )
        else:
            state, body = "present", str(result)
        title = _PANEL_TITLES.get(name)
        if title is not None:
            _label, style = _theme.state_style(state)
            return self._panel(body, title, style)
        return self.result_block(result)

    # ── approval + diff ───────────────────────────────────────────────────────
    def approval_panel(self, prompt_text: str) -> Panel:
        return self._panel(prompt_text.strip(), "Approval Required", "yellow")

    def confirm_approval(self, prompt_text: str) -> bool:
        """Render an approval panel and read a y/N answer. Default: deny."""
        self.print(self.approval_panel(prompt_text))
        try:
            answer = input("Approve once? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer == "y"

    def diff_panel(
        self, file: str, diff_text: str, added: int | None = None, removed: int | None = None
    ) -> Panel:
        title = "Proposed Edit"
        if added is not None and removed is not None:
            title = f"Proposed Edit (+{added} -{removed})"
        body = Text()
        body.append(f"file  {file}\n")
        for line in diff_text.splitlines():
            style = "green" if line.startswith("+") else "red" if line.startswith("-") else None
            body.append(line + "\n", style=style)
        return Panel(body, title=title, border_style="blue", box=self.box, title_align="left")
