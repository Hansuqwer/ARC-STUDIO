from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# POSIX advisory locking via fcntl.flock; Windows: documented no-op fallback.
_HAVE_FCNTL = sys.platform != "win32"
if _HAVE_FCNTL:
    import fcntl


class AdvisoryLockUnavailable(Exception):
    """Raised when the lock file cannot be acquired within the timeout."""


@contextmanager
def advisory_lock(path: Path, *, timeout_ms: int = 5_000) -> Generator[None, None, None]:
    """Acquire an advisory lock on ``path.lock`` before entering the block.

    Semantics:
    - POSIX (macOS/Linux): uses ``fcntl.flock(LOCK_EX | LOCK_NB)`` with a
      spin-wait up to *timeout_ms* milliseconds.
    - Windows: lock file is created but no OS-level locking is applied.
      This is documented behaviour; concurrent writes on Windows are single-
      writer by the single-user CLI assumption documented in
      ``docs/research/cli-session-sharing-protocol.md``.

    The ``.lock`` file is created adjacent to *path* and always removed on
    exit, even on exception.  The ``.lock`` file must **not** be the data
    file itself.
    """
    lock_path = path.parent / f"{path.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if not _HAVE_FCNTL:
        # Windows: best-effort, single-writer assumption documented.
        lock_path.touch(exist_ok=True)
        try:
            yield
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
        return

    # POSIX path
    import time

    deadline = time.monotonic() + timeout_ms / 1000.0
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise AdvisoryLockUnavailable(
                        f"Could not acquire advisory lock for {path} within {timeout_ms}ms"
                    )
                time.sleep(0.02)
        try:
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
    finally:
        os.close(fd)
