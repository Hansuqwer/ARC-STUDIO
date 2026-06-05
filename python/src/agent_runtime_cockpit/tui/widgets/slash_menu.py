"""Slash command dropdown menu (R-010).

Category chips + two-line items + MRU-first ordering on an empty query.
The (name, help_text) 2-tuple shape of ``_commands`` and ``filter`` is part of
the public contract consumed by ``screen.py`` (best_match) and the test-suite,
so category metadata is kept in a parallel ``_category_of`` dict.
"""

from __future__ import annotations

import os

from textual.widgets import Label, ListItem, ListView

_FALLBACK = [
    ("help", "Show help"),
    ("clear", "Clear transcript"),
    ("exit", "Exit ARC Studio"),
    ("theme", "Toggle dark/light theme"),
    ("version", "Show version"),
    ("status", "Show workspace status"),
    ("runs", "List stored runs"),
    ("sessions", "List & switch sessions"),
    ("hitl", "HITL pending prompts"),
    ("runtimes", "List detected runtimes"),
]

# Semantic color per command category. ASCII fallback drops the glyph.
_CATEGORY_COLOR: dict[str, str] = {
    "session": "cyan",
    "runtime": "green",
    "run": "green",
    "provider": "magenta",
    "workspace": "yellow",
    "meta": "blue",
    "context": "cyan",
    "memory": "blue",
    "planning": "yellow",
    "compliance": "red",
    "passthrough": "bright_black",
}

_MAX_VISIBLE = 8  # two-line items take more vertical space than one-liners


def _no_color() -> bool:
    return bool(os.environ.get("NO_COLOR"))


def _category_chip(category: str) -> str:
    """Return a small inline chip for a command category."""
    if not category:
        return ""
    if _no_color():
        return f"({category}) "
    color = _CATEGORY_COLOR.get(category, "white")
    return f"[{color}]●[/] [{color}]{category}[/] "


class SlashItem(ListItem):
    """A slash-menu row that carries its command name (no colliding DOM id).

    Renders two lines: ``{chip} /name`` then a dim help line.
    """

    def __init__(self, name: str, help_text: str, category: str = "") -> None:
        chip = _category_chip(category)
        desc = help_text[:60] if help_text else ""
        if _no_color() or not desc:
            label = f"{chip}/{name}"
            if desc:
                label += f"\n    {desc}"
        else:
            label = f"{chip}[bold]/{name}[/]\n    [dim]{desc}[/]"
        super().__init__(Label(label, markup=not _no_color()))
        self.command_name = name


class SlashMenu(ListView):
    """Fuzzy-filtered slash command dropdown with category chips + MRU ordering."""

    def __init__(self, **kwargs) -> None:
        super().__init__(id="slash-menu", **kwargs)
        self._commands: list[tuple[str, str]] = []
        self._category_of: dict[str, str] = {}
        self._load_commands()
        self._last_prefix: str | None = None
        self._mru: list[str] = []  # most-recently-used command names, newest first

    def _load_commands(self) -> None:
        """Populate ``_commands`` (name, help) and ``_category_of`` (name->category)."""
        try:
            # Use the populated registry (the bare global get_registry() may be
            # empty until a SlashCommandHandler is built).
            from agent_runtime_cockpit.cli_repl.slash_commands import _build_registry

            reg = _build_registry()
            cmds = [c for c in reg.list_commands() if c.popup_visible]
            if cmds:
                self._commands = [(c.name, c.help_text) for c in cmds]
                self._category_of = {c.name: c.category for c in cmds}
                return
        except Exception:
            pass
        self._commands = list(_FALLBACK)
        self._category_of = {}

    def filter(self, prefix: str) -> list[tuple[str, str]]:
        p = prefix.lstrip("/").lower()
        return [(n, h) for (n, h) in self._commands if n.startswith(p)]

    def best_match(self, prefix: str) -> str | None:
        matches = self.filter(prefix)
        return matches[0][0] if matches else None

    def record_use(self, name: str) -> None:
        """Record a command as used so it sorts first on an empty query."""
        name = name.lstrip("/").lower()
        if name in self._mru:
            self._mru.remove(name)
        self._mru.insert(0, name)
        del self._mru[16:]  # bound the MRU list

    def _ordered(self, matches: list[tuple[str, str]], prefix: str) -> list[tuple[str, str]]:
        """On an empty query, surface MRU commands first; otherwise keep order."""
        if prefix.lstrip("/") or not self._mru:
            return matches
        rank = {name: i for i, name in enumerate(self._mru)}
        return sorted(matches, key=lambda nh: rank.get(nh[0], len(self._mru) + 1))

    def show_for(self, prefix: str) -> None:
        # Skip redundant rebuilds: clear() is async (AwaitRemove), so rebuilding
        # on every keystroke for the same prefix is wasteful.
        if prefix == self._last_prefix and self.has_class("visible"):
            return
        self._last_prefix = prefix
        self.clear()
        matches = self._ordered(self.filter(prefix), prefix)
        for name, help_text in matches[:_MAX_VISIBLE]:
            self.append(SlashItem(name, help_text, self._category_of.get(name, "")))
        if matches:
            self.add_class("visible")
        else:
            self.remove_class("visible")

    def hide(self) -> None:
        self._last_prefix = None
        self.remove_class("visible")
        self.clear()
