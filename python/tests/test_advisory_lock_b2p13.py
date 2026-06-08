"""B2P-13a: explicit contended + stale semantics for the advisory lock primitive."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agent_runtime_cockpit.storage.advisory_lock import AdvisoryLockUnavailable, advisory_lock


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl advisory locking is POSIX-only")
def test_contended_lock_times_out(tmp_path: Path) -> None:
    """A second acquire while the lock is held raises AdvisoryLockUnavailable within the timeout."""
    import fcntl
    import os

    target = tmp_path / "data.json"
    lock_path = tmp_path / "data.json.lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)  # hold the lock
    try:
        with pytest.raises(AdvisoryLockUnavailable):
            with advisory_lock(target, timeout_ms=50):
                pass
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def test_no_stale_lock_reacquire_after_release(tmp_path: Path) -> None:
    """fcntl locks auto-release on fd close/process death — there is no stale lock to clear."""
    target = tmp_path / "d.json"
    with advisory_lock(target, timeout_ms=200):
        pass
    # Immediately re-acquiring must succeed (no lingering/stale lock).
    with advisory_lock(target, timeout_ms=200):
        pass


def test_lockfile_is_adjacent_not_the_data_file(tmp_path: Path) -> None:
    target = tmp_path / "d.json"
    with advisory_lock(target, timeout_ms=200):
        assert (tmp_path / "d.json.lock").exists()
        assert not target.exists()  # the lock file is never the data file
