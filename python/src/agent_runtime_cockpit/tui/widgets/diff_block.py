"""Diff block widget — colored unified diff rendering."""

from __future__ import annotations

from textual.widgets import Static


class DiffBlock(Static):
    """Renders unified diff text with colored line annotations."""

    def __init__(self, diff_text: str, filename: str = "diff", **kwargs) -> None:
        super().__init__(**kwargs)
        self._diff_text = diff_text
        self._filename = filename

    def render(self) -> str:
        lines: list[str] = []
        lines.append(f"── {self._filename} ──")
        for i, line in enumerate(self._diff_text.splitlines(), 1):
            prefix = f"{i:4d} "
            if line.startswith("+"):
                lines.append(f"{prefix}{line}")
            elif line.startswith("-"):
                lines.append(f"{prefix}{line}")
            else:
                lines.append(f"{prefix}{line}")
        return "\n".join(lines)
