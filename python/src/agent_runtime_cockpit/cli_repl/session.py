from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


SESSION_SCHEMA_VERSION = 1
MODE_PLAN = "plan"
MODE_BUILD = "build"
MODE_AUTO = "auto"
VALID_MODES = {MODE_PLAN, MODE_BUILD, MODE_AUTO}


def _get_sessions_dir() -> Path:
    override = os.environ.get("ARC_STUDIO_SESSIONS_DIR")
    base = Path(override).expanduser() if override else Path.home() / ".arc" / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _detect_legacy_sessions(sess_dir: Path | None = None) -> list[dict[str, Any]]:
    """Detect and read legacy flat StudioSession JSON files.

    Scans the given session directory (or default) for flat .json files
    that match the legacy StudioSession format.
    These are NOT written back; only read for migration/listing purposes.
    """
    target = sess_dir or _get_sessions_dir()
    if not target.exists():
        return []
    sessions: list[dict[str, Any]] = []
    for f in sorted(target.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.stem == "latest":
            continue
        # Skip if this looks like a session.json inside a subdirectory
        if f.parent.stem != f.parent.name and f.name == "session.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return sessions


def _read_legacy_session(session_id: str) -> dict[str, Any] | None:
    """Read a single legacy flat session by ID from the canonical sessions dir."""
    sess_dir = _get_sessions_dir()
    path = sess_dir / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _list_legacy_session_ids(sess_dir: Path | None = None) -> list[str]:
    """List legacy session IDs (flat JSON files without version field)."""
    sessions = _detect_legacy_sessions(sess_dir)
    return [s.get("session_id", "") for s in sessions if s.get("session_id")]


def migrate_legacy_session(session_id: str) -> ChatSession | None:
    """Migrate a single legacy session to canonical format.

    Returns the migrated ChatSession, or None if the legacy session
    doesn't exist or can't be read. Idempotent: if the canonical format
    already exists, returns the existing session without re-migrating.
    """
    canonical_path = _get_sessions_dir() / session_id / "session.json"
    if canonical_path.exists():
        return ChatSession.load(session_id)

    legacy_data = _read_legacy_session(session_id)
    if legacy_data is None:
        return None

    legacy_messages = legacy_data.get("messages", [])
    legacy_mode = legacy_data.get("mode", MODE_BUILD)

    session = ChatSession(
        id=legacy_data.get("session_id", session_id),
        mode=legacy_mode,
    )
    for msg in legacy_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        session.add_message(role, content)

    session.save()
    return session


def migrate_all_legacy_sessions() -> list[tuple[str, bool]]:
    """Migrate all legacy sessions to canonical format.

    Returns a list of (session_id, success) tuples.
    """
    legacy_ids = _list_legacy_session_ids()
    results: list[tuple[str, bool]] = []
    for sid in legacy_ids:
        canonical_path = _get_sessions_dir() / sid / "session.json"
        if canonical_path.exists():
            # Already migrated
            results.append((sid, True))
            continue
        migrated = migrate_legacy_session(sid)
        results.append((sid, migrated is not None))
    return results


class ChatSession(BaseModel):
    """Canonical chat session schema (version 1)."""

    version: int = Field(default=SESSION_SCHEMA_VERSION)
    id: str = Field(default_factory=lambda: f"s-{uuid.uuid4().hex[:12]}")
    mode: str = Field(default=MODE_BUILD)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    history: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_mode(self, mode: str) -> None:
        if mode in VALID_MODES:
            self.mode = mode

    def save(self) -> Path:
        sess_dir = _get_sessions_dir() / self.id
        sess_dir.mkdir(parents=True, exist_ok=True)
        path = sess_dir / "session.json"
        path.write_text(self.model_dump_json(indent=2))

        # Update latest symlink
        latest = _get_sessions_dir() / "latest"
        if latest.is_symlink() or latest.exists():
            latest.unlink(missing_ok=True)
        try:
            latest.symlink_to(self.id)
        except OSError:
            pass  # symlink may fail on some platforms; non-critical

        return path

    @classmethod
    def load(cls, session_id: str) -> ChatSession | None:
        """Load a canonical session. Falls back to legacy flat format."""
        # Try canonical first (subdirectory with session.json)
        path = _get_sessions_dir() / session_id / "session.json"
        if path.exists():
            try:
                return cls.model_validate_json(path.read_text())
            except Exception:
                pass

        # Fallback: try legacy flat format (.json file in sessions dir)
        legacy = _read_legacy_session(session_id)
        if legacy is not None:
            return cls(
                id=legacy.get("session_id", session_id),
                mode=legacy.get("mode", MODE_BUILD),
            )
        return None

    @classmethod
    def list_sessions(cls) -> list[ChatSession]:
        """List all canonical sessions plus legacy flat sessions."""
        sessions: list[ChatSession] = []

        # Canonical sessions
        sess_dir = _get_sessions_dir()
        if sess_dir.exists():
            for d in sorted(sess_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if d.is_dir():
                    sess_path = d / "session.json"
                    if sess_path.exists():
                        try:
                            sessions.append(cls.model_validate_json(sess_path.read_text()))
                        except Exception:
                            pass
                elif d.suffix == ".json" and d.stem != "latest":
                    # Legacy flat file in canonical dir
                    try:
                        data = json.loads(d.read_text(encoding="utf-8"))
                        sessions.append(cls(
                            id=data.get("session_id", d.stem),
                            mode=data.get("mode", MODE_BUILD),
                        ))
                    except Exception:
                        pass

        return sessions

    @classmethod
    def latest(cls) -> ChatSession | None:
        all_sessions = cls.list_sessions()
        return all_sessions[0] if all_sessions else None
