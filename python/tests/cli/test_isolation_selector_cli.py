"""CLI contract tests for the isolation backend selector (arc isolation use/off/status)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def _cfg(ws: Path) -> Path:
    return ws / ".arc" / "config.yaml"


def test_isolation_use_persists_backend(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app, ["isolation", "use", "microvm", "--workspace", str(tmp_path), "--json"]
    )
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["data"]["isolation"] == "microvm"
    assert "isolation: microvm" in _cfg(tmp_path).read_text()


def test_isolation_use_rejects_unknown_backend(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app, ["isolation", "use", "bogus", "--workspace", str(tmp_path), "--json"]
    )
    assert r.exit_code == 2
    assert json.loads(r.output)["error"]["code"] == "INVALID_INPUT"


def test_isolation_use_none_hints_off(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app, ["isolation", "use", "none", "--workspace", str(tmp_path), "--json"]
    )
    assert r.exit_code == 2
    assert "off" in json.loads(r.output)["error"]["message"]


def test_isolation_off_requires_yes_in_json(tmp_path: Path) -> None:
    r = CliRunner().invoke(app, ["isolation", "off", "--workspace", str(tmp_path), "--json"])
    assert r.exit_code == 2
    assert json.loads(r.output)["error"]["code"] == "INVALID_INPUT"
    assert not _cfg(tmp_path).exists()


def test_isolation_off_yes_persists_none(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app, ["isolation", "off", "--yes", "--workspace", str(tmp_path), "--json"]
    )
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["data"]["isolation"] == "none"
    assert "isolation: none" in _cfg(tmp_path).read_text()


def test_isolation_status_reports_configured_and_active(tmp_path: Path) -> None:
    CliRunner().invoke(app, ["isolation", "use", "microvm", "--workspace", str(tmp_path), "--json"])
    r = CliRunner().invoke(app, ["isolation", "status", "--workspace", str(tmp_path), "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)["data"]
    assert data["configured"] == "microvm"
    assert data["active"] == "microvm"
    assert {p["provider_id"] for p in data["providers"]} == {"none", "subprocess", "docker"}


def test_isolation_use_auto_resolves_subprocess(tmp_path: Path) -> None:
    CliRunner().invoke(app, ["isolation", "use", "auto", "--workspace", str(tmp_path), "--json"])
    r = CliRunner().invoke(app, ["isolation", "status", "--workspace", str(tmp_path), "--json"])
    data = json.loads(r.output)["data"]
    assert data["configured"] == "auto"
    assert data["active"] == "subprocess"
