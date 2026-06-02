"""Approval bar — HITL prompt bar shown when pending_approval is set."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label

from ..data import DataStore


class ApprovalBar(Container):
    """Shown when data.pending_approval is set. Keys: y/n/a/Esc."""

    def __init__(self, data: DataStore, prompt_id: str, **kwargs) -> None:
        super().__init__(id="approval-bar", **kwargs)
        self.data = data
        self.prompt_id = prompt_id

    def compose(self) -> ComposeResult:
        yield Label(
            f"⚠ Approval required: {self.prompt_id}\n"
            "  [y] Yes (once)   [n] No   [a] Always allow   [Esc] No",
            id="approval-text",
        )

    def on_key(self, event: events.Key) -> None:
        answer = None
        if event.key == "y":
            answer = "approved"
        elif event.key == "n" or event.key == "escape":
            answer = "rejected"
        elif event.key == "a":
            answer = "always"
        if answer is not None:
            event.stop()
            self._respond(answer)

    def _respond(self, decision: str) -> None:
        try:
            from agent_runtime_cockpit.audit.hitl_sqlite_store import HitlSqliteStore

            db_path = self.data.workspace / ".arc" / "hitl.db"
            store = HitlSqliteStore(db_path)
            store.respond(self.prompt_id, decision)
        except Exception:
            pass
        self.data.pending_approval = None
        self.data.add_entry("system", f"Approval: {decision}")
        self.remove()
