"""Tests for the first-run isolation chooser in `arc workspace init`."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def _iso(ws: Path) -> str:
    return yaml.safe_load((ws / ".arc" / "config.yaml").read_text())["execution"]["isolation"]


def test_init_isolation_flag_persists(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app,
        ["workspace", "init", "--workspace", str(tmp_path), "--isolation", "microvm", "--json"],
    )
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["data"]["isolation"] == "microvm"
    assert _iso(tmp_path) == "microvm"


def test_init_isolation_flag_invalid_exits_without_creating(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app,
        ["workspace", "init", "--workspace", str(tmp_path), "--isolation", "bogus", "--json"],
    )
    assert r.exit_code == 2
    assert json.loads(r.output)["error"]["code"] == "INVALID_INPUT"
    assert not (tmp_path / ".arc" / "config.yaml").exists()


def test_init_json_without_flag_defaults_auto(tmp_path: Path) -> None:
    r = CliRunner().invoke(app, ["workspace", "init", "--workspace", str(tmp_path), "--json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["data"]["isolation"] == "auto"
    assert _iso(tmp_path) == "auto"


def test_init_interactive_prompt_persists_choice(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        app, ["workspace", "init", "--workspace", str(tmp_path)], input="subprocess\n"
    )
    assert r.exit_code == 0, r.output
    assert _iso(tmp_path) == "subprocess"


def test_init_interactive_enter_accepts_auto_default(tmp_path: Path) -> None:
    r = CliRunner().invoke(app, ["workspace", "init", "--workspace", str(tmp_path)], input="\n")
    assert r.exit_code == 0, r.output
    assert _iso(tmp_path) == "auto"
