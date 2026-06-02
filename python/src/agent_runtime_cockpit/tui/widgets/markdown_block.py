"""Markdown block helper for Rich-rendered assistant messages."""

from __future__ import annotations


def render_markdown(content: str, code_theme: str = "monokai") -> object:
    """Return a Rich Markdown renderable for use with RichLog.write()."""
    from rich.markdown import Markdown

    return Markdown(content, code_theme=code_theme)
