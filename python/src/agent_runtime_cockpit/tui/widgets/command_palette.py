"""Command palette modal screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView


class CommandPalette(ModalScreen):
    """Modal command palette: fuzzy-filter all commands, Enter executes, Esc dismisses."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Label("Command Palette — type to filter", id="palette-title")
        yield Input(placeholder="Search commands…", id="palette-input")
        yield ListView(id="palette-list")

    def on_mount(self) -> None:
        self._all: list[str] = []
        try:
            from agent_runtime_cockpit.cli_repl.commands import get_registry

            self._all = [c.name for c in get_registry().list_commands()]
        except Exception:
            pass
        self._populate(self._all)
        self.query_one("#palette-input", Input).focus()

    def _populate(self, names: list[str]) -> None:
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for name in names[:20]:
            lv.append(ListItem(Label(f"/{name}"), id=f"pal-{name}"))

    def on_input_changed(self, event: Input.Changed) -> None:
        q = event.value.lstrip("/").lower()
        filtered = [n for n in self._all if q in n] if q else self._all
        self._populate(filtered)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        cmd = item_id.replace("pal-", "", 1)
        self.dismiss(f"/{cmd}")
