"""ARC Daemon — programmatic entry point (not CLI).

Used when embedding the daemon in Electron or running as a service.
"""

from __future__ import annotations

from pathlib import Path

from .web.server import run_server


def start(host: str = "localhost", port: int = 7777, workspace: Path | None = None) -> None:
    """Start the ARC daemon (blocking)."""
    run_server(host=host, port=port, workspace=workspace)
