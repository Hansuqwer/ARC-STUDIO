"""Safety test: forbidden primitives must not appear in runtime_packs source.

This test scans every Python file under ``agent_runtime_cockpit/runtime_packs/``
and asserts that none of the tokens that would imply dynamic code execution,
network I/O, or server start-up appear anywhere in the source.

The list of forbidden tokens lives in this test only (not in the SDK) so that
the SDK source itself cannot be used to bypass the check.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ── Forbidden substrings (must not appear in source) ────────────────────────
# These indicate dynamic import, network, shell-exec, or server activity.
FORBIDDEN: list[str] = [
    "subprocess",
    "os.system",
    "Popen",
    "importlib.import_module",
    "importlib.util.spec_from",
    "__import__(",
    "urlopen",
    "urllib.request",
    "aiohttp",
    "httpx",
    ".listen(",
    ".serve(",
    "asyncio.start_server",
    "socket.socket",
    "socket.bind",
    "socket.listen",
    "SocketServer",
    "BaseHTTPServer",
    "http.server",
    "xmlrpc.server",
]


def _source_files() -> list[Path]:
    """Locate the runtime_packs package on disk."""
    spec = importlib.util.find_spec("agent_runtime_cockpit.runtime_packs")
    assert spec is not None, "agent_runtime_cockpit.runtime_packs not importable"
    pkg_path = Path(spec.origin).parent  # …/runtime_packs/
    return sorted(pkg_path.glob("*.py"))


@pytest.mark.parametrize(
    "forbidden",
    FORBIDDEN,
    ids=FORBIDDEN,
)
def test_source_does_not_contain_forbidden(forbidden: str):
    """Each forbidden token must not appear in any runtime_packs source file."""
    for src in _source_files():
        text = src.read_text(encoding="utf-8")
        assert forbidden not in text, (
            f"Forbidden token {forbidden!r} found in {src.name}.\n"
            "The Runtime Pack SDK must not use dynamic execution, network I/O, "
            "or server primitives."
        )
