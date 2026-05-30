"""Minimal MCP session registry — tracks persistent stdio MCP sessions.

Each session tracks:
- session_id (UUID)
- server command
- PID and process group ID
- started_at, last_used_at
- timeout/cleanup state
- audit events

No HTTP listener. No auto-start. No daemon persistence.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


SESSION_DIR = ".arc/mcp/sessions"
_AUDIT_DIR = ".arc/audit"
_DEFAULT_TIMEOUT = 3600
_CLEANUP_INTERVAL = 300


class McpSessionRecord(BaseModel):
    session_id: str
    server_cmd: list[str]
    pid: int
    pgid: int
    started_at: str
    last_used_at: str
    status: str = "running"
    error: Optional[str] = None
    workspace: str = ""


class McpSessionStore(BaseModel):
    version: int = 1
    sessions: dict[str, McpSessionRecord] = {}


def _session_dir(workspace: Path) -> Path:
    return workspace / SESSION_DIR


def _audit_dir(workspace: Path) -> Path:
    return workspace / _AUDIT_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_store(workspace: Path) -> McpSessionStore:
    path = _session_dir(workspace) / "sessions.json"
    if path.exists():
        try:
            return McpSessionStore.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return McpSessionStore()


def _save_store(workspace: Path, store: McpSessionStore) -> None:
    path = _session_dir(workspace) / "sessions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(store.model_dump_json(indent=2), encoding="utf-8")


def _persist_audit(workspace: Path, event: dict) -> None:
    try:
        ad = _audit_dir(workspace)
        ad.mkdir(parents=True, exist_ok=True)
        path = ad / "mcp.events.jsonl"
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(event, sort_keys=True, separators=(",", ":"), default=str) + "\n")
    except Exception:
        pass


def _session_alive(session: McpSessionRecord) -> bool:
    try:
        os.kill(session.pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def start_session(
    workspace: Path,
    server_cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> McpSessionRecord:
    """Start a new MCP session: spawn subprocess, register, return record.

    The subprocess is spawned with start_new_session=True to create a process group.
    The session registry writes a PID file under .arc/mcp/sessions/<session_id>/.
    """
    session_id = uuid.uuid4().hex[:16]
    started_at = _now()
    launch_cwd = cwd or workspace
    from ..isolation.subprocess import SubprocessIsolationProvider

    launch_env = SubprocessIsolationProvider(workspace_root=workspace).filter_env(env)

    proc = subprocess.Popen(
        server_cmd,
        cwd=str(launch_cwd),
        env=launch_env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    pgid = os.getpgid(proc.pid)

    record = McpSessionRecord(
        session_id=session_id,
        server_cmd=server_cmd,
        pid=proc.pid,
        pgid=pgid,
        started_at=started_at,
        last_used_at=started_at,
        workspace=str(workspace),
    )

    store = _load_store(workspace)
    store.sessions[session_id] = record
    _save_store(workspace, store)

    _persist_audit(
        workspace,
        {
            "type": "mcp_session_started",
            "session_id": session_id,
            "server_cmd": " ".join(server_cmd),
            "pid": proc.pid,
            "pgid": pgid,
            "workspace": str(workspace),
            "timestamp": started_at,
        },
    )

    return record


def stop_session(workspace: Path, session_id: str) -> bool:
    """Stop an MCP session: kill process group, update registry, persist audit.

    Uses SIGTERM first, then SIGKILL after timeout. Returns True if stopped.
    """
    store = _load_store(workspace)
    record = store.sessions.get(session_id)
    if not record:
        return False

    try:
        os.killpg(record.pgid, signal.SIGTERM)
        for _ in range(20):
            if not _session_alive(record):
                break
            time.sleep(0.1)
        else:
            try:
                os.killpg(record.pgid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
    except (OSError, ProcessLookupError):
        pass

    record.status = "stopped"
    record.last_used_at = _now()
    _save_store(workspace, store)

    _persist_audit(
        workspace,
        {
            "type": "mcp_session_stopped",
            "session_id": session_id,
            "workspace": str(workspace),
            "timestamp": record.last_used_at,
        },
    )

    return True


def list_sessions(workspace: Path) -> list[dict]:
    """List all registered MCP sessions with alive/dead status."""
    store = _load_store(workspace)
    results = []
    for sid, rec in store.sessions.items():
        alive = _session_alive(rec) if rec.status == "running" else False
        results.append(
            {
                "session_id": sid,
                "server_cmd": " ".join(rec.server_cmd),
                "pid": rec.pid,
                "alive": alive,
                "status": rec.status,
                "started_at": rec.started_at,
                "last_used_at": rec.last_used_at,
                "error": rec.error,
            }
        )
    return sorted(results, key=lambda s: s["started_at"], reverse=True)


def show_session(workspace: Path, session_id: str) -> Optional[dict]:
    """Show one MCP session."""
    store = _load_store(workspace)
    rec = store.sessions.get(session_id)
    if not rec:
        return None
    alive = _session_alive(rec) if rec.status == "running" else False
    return {
        "session_id": rec.session_id,
        "server_cmd": " ".join(rec.server_cmd),
        "pid": rec.pid,
        "pgid": rec.pgid,
        "alive": alive,
        "status": rec.status,
        "started_at": rec.started_at,
        "last_used_at": rec.last_used_at,
        "error": rec.error,
        "workspace": rec.workspace,
    }


def cleanup_stale_sessions(workspace: Path, timeout: int = _DEFAULT_TIMEOUT) -> list[str]:
    """Clean up stale sessions that have exceeded idle timeout."""
    store = _load_store(workspace)
    now_time = time.time()
    cleaned: list[str] = []

    for sid, rec in store.sessions.items():
        if rec.status != "running":
            continue
        try:
            last_used = datetime.fromisoformat(rec.last_used_at).timestamp()
        except (ValueError, TypeError):
            last_used = 0
        if now_time - last_used > timeout or not _session_alive(rec):
            try:
                os.killpg(rec.pgid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            rec.status = "timed_out"
            rec.error = "idle_timeout"
            rec.last_used_at = _now()
            cleaned.append(sid)

    _save_store(workspace, store)

    for sid in cleaned:
        _persist_audit(
            workspace,
            {
                "type": "mcp_session_cleaned",
                "session_id": sid,
                "workspace": str(workspace),
                "timestamp": _now(),
            },
        )

    return cleaned
