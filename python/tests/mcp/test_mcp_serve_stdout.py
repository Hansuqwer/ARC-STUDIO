"""CR-008: `arc mcp serve` must not write to stdout on the stdio transport.

stdout carries the JSON-RPC protocol frames; any human-facing log there
corrupts the stream. Informational output must go to stderr.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from agent_runtime_cockpit.cli.mcp import mcp_serve
from agent_runtime_cockpit.security.trust import trust_workspace


def test_mcp_serve_keeps_stdout_clean(tmp_path: Path, monkeypatch, capsys):
    trust_workspace(tmp_path, note="test")
    fake_server = MagicMock()
    fake_server.run = MagicMock()  # no-op; do not start a real server
    monkeypatch.setattr(
        "agent_runtime_cockpit.mcp.server.create_mcp_server",
        lambda workspace: fake_server,
    )

    mcp_serve(stdio=True, workspace=str(tmp_path), json_output=False, debug=False)

    captured = capsys.readouterr()
    assert captured.out == "", f"stdout must stay empty on stdio transport, got: {captured.out!r}"
    assert "starting on stdio" in captured.err
    fake_server.run.assert_called_once_with(transport="stdio")
