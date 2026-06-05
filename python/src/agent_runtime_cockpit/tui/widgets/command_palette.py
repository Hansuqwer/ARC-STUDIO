"""Command palette modal screen — searches name + description (R-011)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView


class CommandPalette(ModalScreen):
    """Modal command palette: fuzzy-filter commands by name + description, Enter executes."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Label("Command Palette — type to filter", id="palette-title")
        yield Input(placeholder="Search commands…", id="palette-input")
        yield ListView(id="palette-list")

    def on_mount(self) -> None:
        # Each entry is (name, help_text, category) for searching + display.
        self._cmds: list[tuple[str, str, str]] = []
        try:
            from agent_runtime_cockpit.cli_repl.commands import get_registry

            self._cmds = [(c.name, c.help_text, c.category) for c in get_registry().list_commands()]
        except Exception:
            pass
        self._populate(self._cmds)
        self.query_one("#palette-input", Input).focus()

    def _populate(self, cmds: list[tuple[str, str, str]]) -> None:
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for name, help_text, category in cmds[:20]:
            label_text = f"/{name}"
            if help_text:
                label_text += f"  [dim]{help_text[:60]}[/dim]"
            lv.append(ListItem(Label(label_text, markup=True), id=f"pal-{name}"))

    def on_input_changed(self, event: Input.Changed) -> None:
        q = event.value.lstrip("/").lower()
        if q:
            filtered = [(n, h, c) for n, h, c in self._cmds if q in n or q in h.lower()]
        else:
            filtered = self._cmds
        self._populate(filtered)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        cmd = item_id.replace("pal-", "", 1)
        self.dismiss(f"/{cmd}")
