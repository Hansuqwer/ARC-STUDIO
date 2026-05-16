"""Shared pytest cleanup hooks."""

from __future__ import annotations

import gc
import socket


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Close unreachable Docker SDK Unix sockets before pytest's final GC pass."""
    for obj in gc.get_objects():
        if isinstance(obj, socket.socket) and obj.family == socket.AF_UNIX and obj.fileno() != -1:
            obj.close()
