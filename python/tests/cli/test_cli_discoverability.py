"""Tests for `arc version` and `arc health` CLI commands."""

from __future__ import annotations

import json
import re


def test_version_text(run_cli):
    """`arc version` prints version info as text."""
    result = run_cli("version")
    assert result.exit_code == 0
    assert "0.1.0a0" in result.stdout


def test_version_json(run_cli):
    """`arc version --json` returns valid JSON envelope."""
    result = run_cli("version --json")
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert "version" in data["data"]
    assert data["data"]["version"] == "0.1.0a0"
    assert "python" in data["data"]
    assert "platform" in data["data"]


def test_version_json_python_version(run_cli):
    """`arc version --json` includes Python version string."""
    result = run_cli("version --json")
    data = json.loads(result.stdout)
    py_version = data["data"]["python"]
    assert re.match(r"\d+\.\d+\.\d+", py_version), f"Unexpected python version: {py_version}"


def test_health_text(run_cli):
    """`arc health` prints health info as text."""
    result = run_cli("health")
    assert result.exit_code == 0
    assert "checks" in result.stdout.lower() or "daemon" in result.stdout.lower()


def test_health_json(run_cli):
    """`arc health --json` returns valid JSON envelope with checks."""
    result = run_cli("health --json")
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "ok" in data
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    assert len(checks) >= 2  # at least python + cli checks
    check_names = {c["check"] for c in checks}
    assert "python" in check_names
    assert "cli" in check_names


def test_health_json_python_check(run_cli):
    """`arc health --json` python check reports version."""
    result = run_cli("health --json")
    data = json.loads(result.stdout)
    for check in data["data"]["checks"]:
        if check["check"] == "python":
            assert check["ok"] is True
            assert re.match(r"\d+\.\d+\.\d+", check["version"]), f"Unexpected python version: {check['version']}"
            return
    assert False, "No python check found in health output"


def test_health_json_cli_check(run_cli):
    """`arc health --json` cli check reports version."""
    result = run_cli("health --json")
    data = json.loads(result.stdout)
    for check in data["data"]["checks"]:
        if check["check"] == "cli":
            assert check["ok"] is True
            assert check["version"] == "0.1.0a0"
            return
    assert False, "No cli check found in health output"
