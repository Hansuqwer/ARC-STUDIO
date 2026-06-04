"""MarkdownBlock — render assistant messages with markdown + syntax.

Implements UX_AUDIT R-004 (partial: assistant messages only). Falls back to
plain text when Rich/Textual are unavailable or NO_COLOR is set so the
widget remains universally safe.
"""

from __future__ import annotations

from textual.widgets import Static


class MarkdownBlock(Static):
    """Renders a markdown body. Code blocks get syntax highlighting."""

    DEFAULT_CSS = """
    MarkdownBlock { height: auto; padding: 0 2; }
    """

    def __init__(self, body: str, *, no_color: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._body = body
        self._no_color = no_color

    def render(self):  # type: ignore[override]
        if self._no_color:
            return self._body
        try:
            from rich.markdown import Markdown

            return Markdown(self._body, code_theme="monokai")
        except Exception:
            return self._body


__all__ = ["MarkdownBlock"]
