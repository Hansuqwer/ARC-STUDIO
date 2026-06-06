from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agent_runtime_cockpit.runtime.mode import RuntimeMode
from agent_runtime_cockpit.storage.atomic import write_text_atomic

SESSION_SCHEMA_VERSION = 4

# Strict session ID regex shared between Python CLI and TypeScript IDE bridge.
# Mirrors the pattern used in SessionBridgeService.getChatSession().
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
MODE_PLAN = "plan"
MODE_BUILD = "build"
MODE_AUTO = "auto"
VALID_MODES = {MODE_PLAN, MODE_BUILD, MODE_AUTO}


def is_safe_session_id(session_id: str) -> bool:
    return (
        bool(session_id) and "/" not in session_id and "\\" not in session_id and session_id != ".."
    )


def is_valid_session_id(session_id: str) -> bool:
    return (
        session_id != "latest"
        and is_safe_session_id(session_id)
        and bool(SESSION_ID_RE.fullmatch(session_id))
    )


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

    session = _session_from_legacy(legacy_data, session_id)

    session.save()
    return session


def _session_from_legacy(data: dict[str, Any], fallback_id: str) -> ChatSession:
    session = ChatSession(
        id=data.get("session_id", fallback_id),
        mode=data.get("mode", MODE_BUILD),
        runtime_mode=RuntimeMode.from_legacy(data.get("runtime_mode", RuntimeMode.FAKE)),
        profile_id=str(data.get("profile_id") or "default"),
        isolation_id=str(data.get("isolation_id") or "none"),
        allow_paid_calls=bool(data.get("allow_paid_calls", False)),
        metadata={"source_trust": "workspace", "source_format": "legacy_studio_session"},
    )
    for msg in data.get("messages", []):
        session.history.append(
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", data.get("updated", session.updated_at)),
                "source_trust": "workspace",
            }
        )
    return session


def _migrate_chat_session(data: dict[str, Any]) -> dict[str, Any]:
    version = int(data.get("version", 1))
    if version == SESSION_SCHEMA_VERSION:
        migrated = dict(data)
    elif version in (1, 2, 3):
        migrated = dict(data)
        migrated["version"] = SESSION_SCHEMA_VERSION
    else:
        return data
    migrated["runtime_mode"] = RuntimeMode.from_legacy(
        migrated.get("runtime_mode", RuntimeMode.FAKE)
    ).value
    migrated.setdefault("profile_id", "default")
    migrated.setdefault("isolation_id", "none")
    migrated.setdefault(
        "allow_paid_calls", RuntimeMode(migrated["runtime_mode"]) is RuntimeMode.PROVIDER_BACKED
    )
    migrated.setdefault("tools_enabled", False)
    migrated.setdefault("max_tool_iterations", 10)
    migrated.setdefault("available_tools", None)
    return migrated


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
    """Canonical chat session schema (version 4)."""

    version: int = Field(default=SESSION_SCHEMA_VERSION)
    id: str = Field(default_factory=lambda: f"s-{uuid.uuid4().hex[:12]}")
    mode: str = Field(default=MODE_BUILD)
    runtime_mode: RuntimeMode = RuntimeMode.FAKE
    profile_id: str = "default"
    isolation_id: str = "none"
    allow_paid_calls: bool = False
    tools_enabled: bool = False
    max_tool_iterations: int = Field(default=10, ge=1, le=100)
    available_tools: list[str] | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    history: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def model_validate_json(
        cls, json_data: str | bytes | bytearray, *args: Any, **kwargs: Any
    ) -> ChatSession:
        data = json.loads(json_data)
        return cls.model_validate(_migrate_chat_session(data), *args, **kwargs)

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> ChatSession:
        if isinstance(obj, dict):
            obj = _migrate_chat_session(obj)
        return super().model_validate(obj, *args, **kwargs)

    def add_message(self, role: str, content: str) -> None:
        self.history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_mode(self, mode: str) -> None:
        if mode in VALID_MODES:
            self.mode = mode

    def save(self) -> Path:
        if not is_valid_session_id(self.id):
            raise ValueError("unsafe session id")
        sess_dir = _get_sessions_dir() / self.id
        sess_dir.mkdir(parents=True, exist_ok=True)
        path = sess_dir / "session.json"
        write_text_atomic(path, self.model_dump_json(indent=2) + "\n", lock=True)

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
        if not is_valid_session_id(session_id):
            return None
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
            return _session_from_legacy(legacy, session_id)
        return None

    @classmethod
    def list_sessions(cls) -> list[ChatSession]:
        """List all canonical sessions plus legacy flat sessions."""
        sessions: list[ChatSession] = []

        # Canonical sessions
        sess_dir = _get_sessions_dir()
        if sess_dir.exists():
            for d in sorted(sess_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if d.name == "latest":
                    continue
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
                        sessions.append(_session_from_legacy(data, d.stem))
                    except Exception:
                        pass

        return sessions

    @classmethod
    def latest(cls) -> ChatSession | None:
        all_sessions = cls.list_sessions()
        return all_sessions[0] if all_sessions else None


# ── MT-1 Deterministic Tool-Result Microcompact ───────────────────────────────


@dataclass(frozen=True)
class CompactionReceipt:
    """Audit record for a microcompact operation."""

    cleared_count: int  # number of tool messages replaced
    cleared_chars: int  # total characters removed
    kept_count: int  # tool messages kept verbatim
    sha256: str  # SHA-256 of the cleared content (hex)
    timestamp: str  # ISO-8601 UTC


def microcompact_tool_results(
    session: "ChatSession",
    *,
    keep_last: int = 5,
) -> CompactionReceipt:
    """Replace old tool-role messages with a compact placeholder (in-place).

    Keeps the ``keep_last`` most recent ``role=="tool"`` messages verbatim.
    Older tool messages are replaced with a one-line stub:
        ``[Tool output cleared — N chars removed]``

    A SHA-256 receipt of the removed content is returned so the audit chain
    can verify that compaction was deterministic and nothing was silently lost.

    Returns a :class:`CompactionReceipt`. No-op (receipt with zero counts)
    when ≤ ``keep_last`` tool messages exist.
    """
    import hashlib
    from datetime import datetime, timezone

    # Collect all tool-message positions
    tool_indices = [i for i, m in enumerate(session.history) if m.get("role") == "tool"]
    to_clear = tool_indices[:-keep_last] if len(tool_indices) > keep_last else []

    if not to_clear:
        return CompactionReceipt(
            cleared_count=0,
            cleared_chars=0,
            kept_count=len(tool_indices),
            sha256=hashlib.sha256(b"").hexdigest(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    cleared_content = []
    cleared_chars = 0
    for idx in to_clear:
        content = session.history[idx].get("content", "")
        cleared_content.append(content)
        cleared_chars += len(content)
        session.history[idx] = {
            **session.history[idx],
            "content": f"[Tool output cleared — {len(content)} chars removed]",
        }

    digest = hashlib.sha256("\n---\n".join(cleared_content).encode("utf-8")).hexdigest()
    return CompactionReceipt(
        cleared_count=len(to_clear),
        cleared_chars=cleared_chars,
        kept_count=len(tool_indices) - len(to_clear),
        sha256=digest,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
