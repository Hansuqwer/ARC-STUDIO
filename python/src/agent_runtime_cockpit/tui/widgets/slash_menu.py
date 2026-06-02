"""Slash command dropdown menu."""

from __future__ import annotations

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


class SlashMenu(ListView):
    """Fuzzy-filtered slash command dropdown with one-line descriptions."""

    def __init__(self, **kwargs) -> None:
        super().__init__(id="slash-menu", **kwargs)
        self._commands: list[tuple[str, str]] = self._load_commands()

    def _load_commands(self) -> list[tuple[str, str]]:
        try:
            # Use the populated registry (the bare global get_registry() may be
            # empty until a SlashCommandHandler is built).
            from agent_runtime_cockpit.cli_repl.slash_commands import _build_registry

            reg = _build_registry()
            cmds = [(c.name, c.help_text) for c in reg.list_commands() if c.popup_visible]
            return cmds or _FALLBACK
        except Exception:
            return _FALLBACK

    def filter(self, prefix: str) -> list[tuple[str, str]]:
        p = prefix.lstrip("/").lower()
        return [(n, h) for (n, h) in self._commands if n.startswith(p)]

    def best_match(self, prefix: str) -> str | None:
        matches = self.filter(prefix)
        return matches[0][0] if matches else None

    def show_for(self, prefix: str) -> None:
        self.clear()
        matches = self.filter(prefix)
        for name, help_text in matches[:12]:
            desc = help_text[:50] if help_text else ""
            self.append(ListItem(Label(f"/{name} — {desc}"), id=f"slash-{name}"))
        if matches:
            self.add_class("visible")
        else:
            self.remove_class("visible")

    def hide(self) -> None:
        self.remove_class("visible")
        self.clear()
