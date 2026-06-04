from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def test_serve_generates_process_local_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ARC_DAEMON_TOKEN", raising=False)
    monkeypatch.delenv("ARC_DAEMON_ALLOW_UNAUTHENTICATED", raising=False)
    calls: list[tuple[str, int, Path | None, str | None]] = []

    def fake_run_server(host: str, port: int, workspace: Path | None = None) -> None:
        calls.append((host, port, workspace, os.environ.get("ARC_DAEMON_TOKEN")))

    monkeypatch.setattr("agent_runtime_cockpit.web.server.run_server", fake_run_server)

    try:
        result = CliRunner().invoke(app, ["serve", "--workspace", str(tmp_path)])
    finally:
        os.environ.pop("ARC_DAEMON_TOKEN", None)

    assert result.exit_code == 0, result.output
    assert calls
    token = calls[0][3]
    assert token
    assert f"ARC_DAEMON_TOKEN={token}" in result.output


def test_serve_preserves_existing_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ARC_DAEMON_TOKEN", "existing-token")
    monkeypatch.delenv("ARC_DAEMON_ALLOW_UNAUTHENTICATED", raising=False)
    calls: list[str | None] = []

    def fake_run_server(host: str, port: int, workspace: Path | None = None) -> None:
        calls.append(os.environ.get("ARC_DAEMON_TOKEN"))

    monkeypatch.setattr("agent_runtime_cockpit.web.server.run_server", fake_run_server)

    result = CliRunner().invoke(app, ["serve", "--workspace", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert calls == ["existing-token"]
    assert "generated a process-local token" not in result.output
