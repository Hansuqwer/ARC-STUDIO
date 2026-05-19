from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def _get_sessions_dir() -> Path:
    override = os.environ.get("ARC_STUDIO_SESSIONS_DIR")
    base = Path(override).expanduser() if override else Path.home() / ".arc" / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: f"s-{uuid.uuid4().hex[:12]}")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    history: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()})
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def save(self) -> Path:
        sess_dir = _get_sessions_dir() / self.id
        sess_dir.mkdir(parents=True, exist_ok=True)
        path = sess_dir / "session.json"
        path.write_text(self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, session_id: str) -> ChatSession | None:
        path = _get_sessions_dir() / session_id / "session.json"
        if not path.exists():
            return None
        return cls.model_validate_json(path.read_text())

    @classmethod
    def list_sessions(cls) -> list[ChatSession]:
        sessions: list[ChatSession] = []
        sess_dir = _get_sessions_dir()
        if not sess_dir.exists():
            return sessions
        for d in sorted(sess_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            sess_path = d / "session.json"
            if sess_path.exists():
                try:
                    sessions.append(cls.model_validate_json(sess_path.read_text()))
                except Exception:
                    pass
        return sessions

    @classmethod
    def latest(cls) -> ChatSession | None:
        all_sessions = cls.list_sessions()
        return all_sessions[0] if all_sessions else None
