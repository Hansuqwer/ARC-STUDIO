"""Tests for advisory locking in storage.atomic and storage.advisory_lock."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from agent_runtime_cockpit.storage.advisory_lock import advisory_lock
from agent_runtime_cockpit.storage.atomic import write_text_atomic
from agent_runtime_cockpit.cli_repl.aliases import set_alias, _read_aliases, workspace_alias_path
from agent_runtime_cockpit.cli_repl.session import ChatSession


class TestAdvisoryLock:
    def test_lock_creates_and_removes_lockfile(self, tmp_path: Path) -> None:
        target = tmp_path / "data.json"
        lock_file = tmp_path / "data.json.lock"
        with advisory_lock(target):
            # lock file should exist inside the context
            assert lock_file.exists()
        # lock file removed after context exits
        assert not lock_file.exists()

    def test_lock_released_on_exception(self, tmp_path: Path) -> None:
        target = tmp_path / "data.json"
        lock_file = tmp_path / "data.json.lock"
        try:
            with advisory_lock(target):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert not lock_file.exists()

    def test_write_atomic_with_lock_no_partial(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        write_text_atomic(path, '{"v":1}', lock=True)
        assert json.loads(path.read_text()) == {"v": 1}
        # lock file cleaned up
        assert not (tmp_path / "out.json.lock").exists()

    def test_write_atomic_without_lock_still_works(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        write_text_atomic(path, '{"v":2}', lock=False)
        assert json.loads(path.read_text()) == {"v": 2}

    def test_concurrent_alias_writes_do_not_corrupt(self, monkeypatch, tmp_path: Path) -> None:
        """Two threads writing aliases concurrently must not corrupt the file."""
        monkeypatch.setenv("ARC_STUDIO_ALIASES_FILE", str(tmp_path / "user-aliases.json"))
        errors: list[Exception] = []

        def writer(name: str) -> None:
            try:
                set_alias(name, f"/status {name}", scope="workspace", workspace=tmp_path)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(f"alias{i}",)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent writes: {errors}"
        aliases = _read_aliases(workspace_alias_path(tmp_path))
        # No corruption: result must be valid JSON with at least 1 alias
        # (last-writer-wins on read→merge→write cycles is expected behaviour;
        # advisory lock prevents partial writes, not merge races)
        assert isinstance(aliases, dict)
        assert len(aliases) >= 1

    def test_session_save_uses_lock(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        session = ChatSession(id="s-locktest")
        path = session.save()
        assert path.exists()
        assert not path.parent.joinpath("session.json.lock").exists()

    def test_concurrent_session_saves_do_not_corrupt(self, monkeypatch, tmp_path: Path) -> None:
        """Two threads saving the same session must not produce corrupted JSON."""
        monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
        session = ChatSession(id="s-concurrent")
        errors: list[Exception] = []

        def saver() -> None:
            try:
                session.add_message("user", "ping")
                session.save()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=saver) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent saves: {errors}"
        # File must be valid JSON after concurrent writes
        path = tmp_path / "sessions" / "s-concurrent" / "session.json"
        data = json.loads(path.read_text())
        assert data["id"] == "s-concurrent"
