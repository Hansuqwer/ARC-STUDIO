"""Reactive data store for the ARC TUI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TranscriptEntry:
    """A single entry in the transcript."""

    id: str
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_time(self) -> str:
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%H:%M:%S")
        except Exception:
            return ""


@dataclass
class DataStore:
    """Central reactive state for the ARC TUI."""

    # ── session ──────────────────────────────────────────────────────────
    session_id: str = ""
    seed: int | None = None  # if set, session_id is derived deterministically (for tests)
    mode: str = "build"  # plan | build | auto
    runtime_mode: str = "fake"
    profile_id: str = "default"
    workspace: Path = field(default_factory=Path.cwd)

    # ── transcript ───────────────────────────────────────────────────────
    entries: list[TranscriptEntry] = field(default_factory=list)

    # ── daemon ───────────────────────────────────────────────────────────
    daemon_online: bool = False
    daemon_host: str = "127.0.0.1"
    daemon_port: int = 7777

    # ── cost ─────────────────────────────────────────────────────────────
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    # UX R-002: context-window size for the currently selected model.
    # 0 means unknown — ContextMeter falls back to a conservative default.
    context_limit: int = 0

    # ── agent state ──────────────────────────────────────────────────────
    is_streaming: bool = False
    pending_approval: str | None = None
    approval_options: list[str] = field(default_factory=list)
    # Paid provider calls are ON by default in the TUI; opt out with
    # ARC_TUI_NO_PAID=1. This flips only the paid default — provider-key,
    # workspace-trust, and dual-gate checks still apply downstream.
    allow_paid: bool = True

    # ── domain caches ────────────────────────────────────────────────────
    run_count: int = 0
    hitl_pending_count: int = 0
    current_provider: str | None = None  # active provider id
    current_model: str | None = None  # active model id

    # ── input history ────────────────────────────────────────────────────
    input_history: list[str] = field(default_factory=list)
    _history_index: int = -1

    # ── budget/quota ─────────────────────────────────────────────────────
    quota_warnings: list = field(default_factory=list)
    # Optional budget limit in USD; None means no budget set.
    wallet_budget_usd: float | None = None

    @property
    def allow_paid_warning(self) -> str | None:
        """Return a warning string if paid calls are on with no budget set, else None."""
        if (
            getattr(self, "allow_paid", False)
            and self.wallet_budget_usd is not None
            and self.wallet_budget_usd <= 0
        ):
            return "⚠ Paid calls unrestricted — set a budget with /wallet"
        return None

    def __post_init__(self) -> None:
        if not self.session_id:
            if self.seed is not None:
                import random

                rng = random.Random(self.seed)
                self.session_id = f"s-{rng.getrandbits(48):012x}"
            else:
                import uuid

                self.session_id = f"s-{uuid.uuid4().hex[:12]}"
        self.daemon_host = os.environ.get("ARC_DAEMON_HOST", "127.0.0.1")
        self.daemon_port = int(os.environ.get("ARC_DAEMON_PORT", "7777"))
        if os.environ.get("ARC_TUI_NO_PAID"):
            self.allow_paid = False

    def add_entry(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> TranscriptEntry:
        import uuid

        entry = TranscriptEntry(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        # Increment running token estimate (approximation; exact counts come from provider responses).
        try:
            from agent_runtime_cockpit.context.token_counter import estimate_tokens

            self.total_tokens += estimate_tokens(content, provider=self.current_provider)
        except Exception:
            pass
        return entry

    def append_to_last(self, text: str) -> None:
        if self.entries and self.entries[-1].role == "assistant":
            self.entries[-1].content += text
        else:
            self.add_entry("assistant", text)

    def update_last_metadata(self, key: str, value: Any) -> None:
        if self.entries:
            self.entries[-1].metadata[key] = value

    def clear_transcript(self) -> None:
        self.entries.clear()

    def add_to_history(self, text: str) -> None:
        if not self.input_history or self.input_history[-1] != text:
            self.input_history.append(text)
        self._history_index = -1

    def history_up(self, current: str) -> str | None:
        if not self.input_history:
            return None
        if self._history_index == -1:
            self._history_index = len(self.input_history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        return self.input_history[self._history_index]

    def history_down(self) -> str | None:
        if self._history_index == -1 or not self.input_history:
            return None
        if self._history_index < len(self.input_history) - 1:
            self._history_index += 1
            return self.input_history[self._history_index]
        self._history_index = -1
        return ""

    def status_line(self, width: int = 80) -> str:
        ws = str(self.workspace)
        home = str(Path.home())
        if ws.startswith(home):
            ws = "~" + ws[len(home) :]
        if len(ws) > 30:
            ws = "…" + ws[-29:]
        cost = f"${self.total_cost_usd:.4f}" if self.total_cost_usd > 0 else "$0"
        session_short = self.session_id[:8] if self.session_id else "--------"
        segments = [
            f" {self.mode} ",
            f" {self.runtime_mode} ",
            f" {ws} ",
            f" {session_short} ",
            f" {cost} ",
            " Esc:cancel  /:commands ",
        ]
        line = "│".join(segments)
        if len(line) > width:
            line = line[: width - 1] + "…"
        return line
