"""Slash command dropdown menu."""

from __future__ import annotations

from textual.widgets import Label, ListItem, ListView


class SlashMenu(ListView):
    """Fuzzy-filtered slash command dropdown."""

    def __init__(self, **kwargs) -> None:
        super().__init__(id="slash-menu", **kwargs)
        self._all_commands: list[str] = []
        self._load_commands()

    def _load_commands(self) -> None:
        try:
            from agent_runtime_cockpit.cli_repl.commands import get_registry

            self._all_commands = [c.name for c in get_registry().list_commands()]
        except Exception:
            self._all_commands = [
                "help",
                "clear",
                "exit",
                "theme",
                "version",
                "status",
                "runs",
                "sessions",
                "hitl",
                "runtimes",
                "doctor",
            ]

    def filter(self, prefix: str) -> list[str]:
        p = prefix.lstrip("/").lower()
        return [c for c in self._all_commands if c.startswith(p)]

    def show_for(self, prefix: str) -> None:
        self.clear()
        matches = self.filter(prefix)
        for name in matches[:10]:
            self.append(ListItem(Label(f"/{name}"), id=f"slash-{name}"))
        if matches:
            self.add_class("visible")
        else:
            self.remove_class("visible")

    def hide(self) -> None:
        self.remove_class("visible")
        self.clear()
