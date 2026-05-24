"""ARC Daemon — PyInstaller entry point.

This module serves as the main script for PyInstaller bundling.
When frozen, it starts the ARC daemon server directly.
In normal development, users use `arc serve` via the CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the package root is on sys.path when frozen
if getattr(sys, "frozen", False):
    # PyInstaller bundles packages under sys._MEIPASS
    meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    pkg_root = meipass / "agent_runtime_cockpit"
    if pkg_root.is_dir():
        sys.path.insert(0, str(meipass))


def main() -> None:
    """Parse CLI-style args and start the daemon."""
    import argparse

    parser = argparse.ArgumentParser(description="ARC Studio Daemon")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port to bind (default: 7777)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace path",
    )
    args = parser.parse_args()

    from agent_runtime_cockpit.daemon import start

    start(host=args.host, port=args.port, workspace=args.workspace)


if __name__ == "__main__":
    main()
