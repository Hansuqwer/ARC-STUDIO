"""HITL view — list pending human-in-the-loop prompts (R-018).

This is a *viewer*. Responding to a prompt requires the per-prompt token that
is held only by the entity that created the prompt (it is never returned by
``list_prompts``), so approvals are intentionally routed through the
token-authenticated CLI path rather than faked here. This keeps HITL a
deterministic, token-gated decision.
"""

from __future__ import annotations

import time
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Label, ListItem, ListView

from .side_panel import SidePanel


def _age(created_at: object) -> str:
    """Best-effort human age from a numeric epoch or ISO string."""
    try:
        if isinstance(created_at, (int, float)):
            secs = max(0, int(time.time() - created_at))
        else:
            return ""
    except Exception:
        return ""
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    return f"{secs // 3600}h ago"


class HitlView(SidePanel):
    """List pending HITL prompts. Respond via `arc hitl respond <id> --token`."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, workspace: Path, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label("HITL — Pending Prompts", id="hitl-header")
        yield ListView(id="hitl-list")
        yield Label(
            "Respond (token-gated):  arc hitl respond <id> --token <token>",
            id="hitl-footer",
        )

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
            for i, p in enumerate(prompts):
                # Correct field names: HitlPrompt exposes hitl_id / prompt_text /
                # run_id / step_id (the old .id / .message attributes never
                # existed, so rows silently rendered as a repr fallback).
                meta = f"{p.hitl_id[:16]} · run {p.run_id[:12]} · step {p.step_id}"
                age = _age(p.created_at)
                if age:
                    meta += f" · {age}"
                text = (p.prompt_text or "")[:100]
                lv.append(
                    ListItem(
                        Label(f"[bold]{meta}[/]\n    [dim]{text}[/]", markup=True), id=f"hitl-{i}"
                    )
                )
        except Exception as e:
            lv.append(ListItem(Label(f"Error: {e}")))
