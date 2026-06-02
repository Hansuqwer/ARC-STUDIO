"""HITL view — list and respond to pending human-in-the-loop prompts."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Label, ListItem, ListView

from .side_panel import SidePanel


class HitlView(SidePanel):
    """List pending HITL prompts; approve or reject."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, workspace: Path, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label("HITL Pending Prompts")
        yield ListView(id="hitl-list")

    def on_mount(self) -> None:
        lv = self.query_one("#hitl-list", ListView)
        db_path = self.workspace / ".arc" / "hitl.db"
        if not db_path.exists():
            lv.append(ListItem(Label("No HITL database found. Start a run first.")))
            return
        try:
            from agent_runtime_cockpit.audit.hitl_sqlite_store import HitlSqliteStore

            store = HitlSqliteStore(db_path)
            prompts = store.list_prompts()
            if not prompts:
                lv.append(ListItem(Label("No pending HITL prompts.")))
                return
            for p in prompts:
                pid = getattr(p, "id", str(p))
                msg = getattr(p, "message", pid)[:80]
                lv.append(ListItem(Label(f"{pid}: {msg}"), id=f"hitl-{pid}"))
        except Exception as e:
            lv.append(ListItem(Label(f"Error: {e}")))
