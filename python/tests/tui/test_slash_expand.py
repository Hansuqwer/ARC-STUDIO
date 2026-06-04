"""Tests for /expand slash command (QW-4 Task 3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agent_runtime_cockpit.budget.storage import SQLiteWALStorage
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import cmd_expand
from agent_runtime_cockpit.context.handles import HandleStore


def _session() -> ChatSession:
    return ChatSession()


def _storage(tmp_path: Path) -> SQLiteWALStorage:
    return SQLiteWALStorage(tmp_path / "t.db")


# ── 1. Missing arg returns usage ──────────────────────────────────────────


def test_missing_arg_returns_usage():
    result = cmd_expand("", _session())
    assert result.state == "blocked"
    assert "Usage" in result.remediation


# ── 2. Unknown handle returns not_found ───────────────────────────────────


def test_unknown_handle_not_found(tmp_path):
    result = _call_expand("deadbeef", tmp_path)
    assert result.state == "not_found"
    assert "not found" in result.output


def _call_expand(prefix: str, tmp_path: Path, content: bytes | None = None) -> object:
    """Call cmd_expand with a controlled SQLiteWALStorage at tmp_path."""
    st = _storage(tmp_path)
    if content is not None:
        hs = HandleStore(st)
        hs.store(content)

    original_init = SQLiteWALStorage.__init__

    def patched_init(self, db_path=None):
        original_init(self, tmp_path / "t.db")

    with patch.object(SQLiteWALStorage, "__init__", patched_init):
        return cmd_expand(prefix, _session())


# ── 3. Successful expand returns present + injects into history ───────────


def test_expand_success_injects_history(tmp_path):
    content = b"expanded content here"
    st = _storage(tmp_path)
    hs = HandleStore(st)
    meta = hs.store(content)
    prefix = meta.sha256_hex[:8]

    original_init = SQLiteWALStorage.__init__

    def patched_init(self, db_path=None):
        original_init(self, tmp_path / "t.db")

    session = _session()
    with patch.object(SQLiteWALStorage, "__init__", patched_init):
        result = cmd_expand(prefix, session)

    assert result.state == "present"
    assert str(len(content)) in result.output
    assert any(m["content"] == content.decode() for m in session.history)


# ── 4. Ambiguous prefix returns blocked ───────────────────────────────────


def test_ambiguous_prefix_blocked(tmp_path):
    st = _storage(tmp_path)
    st.handle_store("aa" + "0" * 62, b"c1", "text/plain")
    st.handle_store("aa" + "1" * 62, b"c2", "text/plain")

    original_init = SQLiteWALStorage.__init__

    def patched_init(self, db_path=None):
        original_init(self, tmp_path / "t.db")

    with patch.object(SQLiteWALStorage, "__init__", patched_init):
        result = cmd_expand("aa", _session())
    assert result.state == "blocked"


# ── 5. Full SHA expand works ──────────────────────────────────────────────


def test_expand_full_sha_works(tmp_path):
    content = b"full sha lookup"
    st = _storage(tmp_path)
    hs = HandleStore(st)
    meta = hs.store(content)

    original_init = SQLiteWALStorage.__init__

    def patched_init(self, db_path=None):
        original_init(self, tmp_path / "t.db")

    with patch.object(SQLiteWALStorage, "__init__", patched_init):
        result = cmd_expand(meta.sha256_hex, _session())
    assert result.state == "present"
