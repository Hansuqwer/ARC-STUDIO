"""Diff block widget — colored unified diff rendering.

Implements UX_AUDIT R-009:
- + lines green, - lines red, @@ lines dim cyan
- n/p keys jump between hunks
- NO_COLOR: uses +/- prefix only (no color codes)
"""

from __future__ import annotations

from textual import events
from textual.widgets import Static


class DiffBlock(Static):
    """Renders unified diff text with colored line annotations.

    Keys: n = next hunk, p = previous hunk.
    """

    DEFAULT_CSS = """
    DiffBlock {
        height: auto;
        margin-bottom: 1;
    }
    """

    def __init__(
        self, diff_text: str, filename: str = "diff", no_color: bool = False, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._diff_text = diff_text
        self._filename = filename
        self._no_color = no_color
        self._hunk_idx = 0
        self._hunks: list[int] = []  # line indices of @@ markers
        self._side_by_side: bool = False

    def _compute_hunks(self, lines: list[str]) -> list[int]:
        return [i for i, l in enumerate(lines) if l.startswith("@@")]

    def on_key(self, event: events.Key) -> None:
        lines = self._diff_text.splitlines()
        self._hunks = self._compute_hunks(lines)
        if event.key == "n" and self._hunks:
            event.stop()
            self._hunk_idx = (self._hunk_idx + 1) % len(self._hunks)
            self.refresh()
        elif event.key == "p" and self._hunks:
            event.stop()
            self._hunk_idx = (self._hunk_idx - 1) % len(self._hunks)
            self.refresh()
        elif event.key == "s":
            event.stop()
            self._side_by_side = not self._side_by_side
            self.refresh()

    def _render_side_by_side(self) -> str:
        out: list[str] = [f"── {self._filename} ──"]
        removed: list[str] = []
        added: list[str] = []

        def _flush(r: list[str], a: list[str]) -> list[str]:
            rows: list[str] = []
            for left, right in zip(
                r + [""] * max(0, len(a) - len(r)), a + [""] * max(0, len(r) - len(a))
            ):
                rows.append(f"{left:<40} │ {right}")
            return rows

        for line in self._diff_text.splitlines():
            if line.startswith("@@"):
                out.extend(_flush(removed, added))
                removed, added = [], []
                out.append(line)
            elif line.startswith("---") or line.startswith("+++"):
                out.extend(_flush(removed, added))
                removed, added = [], []
                out.append(line)
            elif line.startswith("-"):
                removed.append(line[1:])
            elif line.startswith("+"):
                added.append(line[1:])
            else:
                out.extend(_flush(removed, added))
                removed, added = [], []
                out.append(line)
        out.extend(_flush(removed, added))
        return "\n".join(out)

    def render(self) -> str:
        if self._side_by_side:
            return self._render_side_by_side()
        out: list[str] = []
        out.append(f"── {self._filename} ──")
        for line in self._diff_text.splitlines():
            if self._no_color:
                out.append(line)
            elif line.startswith("+") and not line.startswith("+++"):
                out.append(f"[bold green]{line}[/]")
            elif line.startswith("-") and not line.startswith("---"):
                out.append(f"[bold red]{line}[/]")
            elif line.startswith("@@"):
                out.append(f"[dim cyan]{line}[/]")
            elif line.startswith("+++") or line.startswith("---"):
                out.append(f"[bold]{line}[/]")
            else:
                out.append(line)
        if not self._no_color and self._diff_text:
            out.append("[dim]n = next hunk  p = prev hunk[/]")
        return "\n".join(out)
