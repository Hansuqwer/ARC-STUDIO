"""Sessions view — list and switch chat sessions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Label, ListItem, ListView

from ..data import DataStore
from .side_panel import SidePanel


class SessionsView(SidePanel):
    """List sessions; select to switch; New to create a fresh one."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, data: DataStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = data

    def compose(self) -> ComposeResult:
        yield Label("Sessions")
        yield ListView(id="sessions-list")
        yield Button("New Session", id="new-session-btn")

    def on_mount(self) -> None:
        lv = self.query_one("#sessions-list", ListView)
        try:
            from agent_runtime_cockpit.cli_repl.session import ChatSession

            sessions = ChatSession.list_sessions()
            if not sessions:
                lv.append(ListItem(Label("No sessions found.")))
                return
            for s in sessions[:50]:
                sid = getattr(s, "id", str(s))
                lv.append(ListItem(Label(sid), id=f"sess-{sid}"))
        except Exception as e:
            lv.append(ListItem(Label(f"Error: {e}")))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-session-btn":
            import uuid

            self._data.session_id = f"s-{uuid.uuid4().hex[:12]}"
            self._data.clear_transcript()
            self.dismiss()
