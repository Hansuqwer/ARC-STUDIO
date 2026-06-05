"""Sessions view — list, switch, and fork chat sessions (R-019)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Label, ListItem, ListView

from ..data import DataStore
from .side_panel import SidePanel


def _last_user_snippet(session: object) -> str:
    """Return a short snippet of the last user message in the session."""
    history = getattr(session, "history", None) or []
    for item in reversed(history):
        if isinstance(item, dict) and item.get("role") == "user":
            return str(item.get("content", ""))[:70]
    return ""


class SessionsView(SidePanel):
    """List sessions; select to switch; `f` forks; New creates a fresh one."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("f", "fork", "Fork"),
    ]

    def __init__(self, data: DataStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = data
        self._sessions: list[object] = []

    def compose(self) -> ComposeResult:
        yield Label("Sessions  (Enter switch · f fork · Esc close)", id="sessions-header")
        yield ListView(id="sessions-list")
        yield Button("New Session", id="new-session-btn")

    def on_mount(self) -> None:
        lv = self.query_one("#sessions-list", ListView)
        try:
            from agent_runtime_cockpit.cli_repl.session import ChatSession

            self._sessions = ChatSession.list_sessions()
            if not self._sessions:
                lv.append(ListItem(Label("No sessions found.")))
                return
            for i, s in enumerate(self._sessions[:50]):
                sid = getattr(s, "id", str(s))
                mode = getattr(s, "mode", "")
                updated = (getattr(s, "updated_at", "") or "")[:19]
                snippet = _last_user_snippet(s)
                meta = f"{sid}"
                if mode:
                    meta += f" · {mode}"
                if updated:
                    meta += f" · {updated}"
                line2 = f"\n    [dim]{snippet}[/]" if snippet else ""
                lv.append(ListItem(Label(f"[bold]{meta}[/]{line2}", markup=True), id=f"sess-{i}"))
        except Exception as e:
            lv.append(ListItem(Label(f"Error: {e}")))

    def _selected_session(self) -> object | None:
        lv = self.query_one("#sessions-list", ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._sessions):
            return self._sessions[idx]
        return None

    def action_fork(self) -> None:
        """Fork the highlighted session into a new id, copying its transcript."""
        import uuid

        src = self._selected_session()
        if src is None:
            return
        new_id = f"s-{uuid.uuid4().hex[:12]}"
        history = list(getattr(src, "history", []) or [])
        try:
            # Persist the fork so it survives restart, then switch to it.
            forked = src.model_copy(
                update={"id": new_id, "history": history, "metadata": {"forked_from": src.id}}
            )
            forked.save()
        except Exception:
            pass  # persistence is best-effort; still switch the live session

        self._data.session_id = new_id
        self._data.clear_transcript()
        for item in history:
            if isinstance(item, dict):
                self._data.add_entry(item.get("role", "user"), item.get("content", ""))
        self._data.add_entry("system", f"Forked from {getattr(src, 'id', '?')} → {new_id}")
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-session-btn":
            import uuid

            self._data.session_id = f"s-{uuid.uuid4().hex[:12]}"
            self._data.clear_transcript()
            self.dismiss()
