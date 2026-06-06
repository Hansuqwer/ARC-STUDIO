"""Command palette modal screen — searches name + description (R-011)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from agent_runtime_cockpit.cli_repl.commands import CommandDef


class CommandPalette(ModalScreen):
    """Modal command palette: fuzzy-filter commands by name + description, Enter executes."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    #palette-detail {
        height: auto;
        color: $text-muted;
        margin-top: 1;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Command Palette — type to filter", id="palette-title")
        yield Input(placeholder="Search commands…", id="palette-input")
        yield ListView(id="palette-list")
        yield Static("", id="palette-detail")

    def on_mount(self) -> None:
        self._cmds: list[CommandDef] = []
        try:
            from agent_runtime_cockpit.cli_repl.commands import get_registry

            self._cmds = get_registry().list_commands()
        except Exception:
            pass
        self._populate(self._cmds)
        self.query_one("#palette-input", Input).focus()

    def _populate(self, cmds: list[CommandDef]) -> None:
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for cmd in cmds[:20]:
            label_text = f"/{cmd.name}"
            if cmd.help_text:
                label_text += f"  [dim]{cmd.help_text[:60]}[/dim]"
            lv.append(ListItem(Label(label_text, markup=True), id=f"pal-{cmd.name}"))

    def on_input_changed(self, event: Input.Changed) -> None:
        q = event.value.lstrip("/").lower()
        if q:
            filtered = [c for c in self._cmds if q in c.name or q in c.help_text.lower()]
        else:
            filtered = self._cmds
        self._populate(filtered)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        detail = self.query_one("#palette-detail", Static)
        if event.item is None:
            detail.update("")
            return
        name = (event.item.id or "").replace("pal-", "", 1)
        cmd = next((c for c in self._cmds if c.name == name), None)
        if cmd is None:
            detail.update("")
            return
        parts = [cmd.help_text]
        if cmd.usage:
            parts.append(cmd.usage)
        for ex in cmd.examples[:2]:
            parts.append(f"  {ex}")
        detail.update("\n".join(parts))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        cmd = item_id.replace("pal-", "", 1)
        self.dismiss(f"/{cmd}")
