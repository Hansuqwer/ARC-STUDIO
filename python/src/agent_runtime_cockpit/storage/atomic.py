from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .advisory_lock import advisory_lock


def write_text_atomic(
    path: Path, text: str, *, encoding: str = "utf-8", lock: bool = False
) -> None:
    """Write text via same-directory temp file and atomic replace.

    When *lock* is True an advisory lock is acquired before writing and
    released only after ``os.replace`` completes.  This prevents partial
    reads by concurrent processes on POSIX systems.  See
    ``storage/advisory_lock.py`` for Windows behaviour.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if lock:
        with advisory_lock(path):
            _do_write(path, text, encoding)
    else:
        _do_write(path, text, encoding)


def _do_write(path: Path, text: str, encoding: str) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
