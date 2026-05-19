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


# ─── status ────────────────────────────────────────────────────────────────────


def test_status_text(run_cli, workspace):
    """`arc status` prints status info as text."""
    result = run_cli(f"status --workspace {workspace}")
    assert result.exit_code == 0
    assert "workspace" in result.stdout.lower() or "runtime" in result.stdout.lower()


def test_status_json(run_cli, workspace):
    """`arc status --json` returns valid JSON envelope."""
    result = run_cli(f"status --workspace {workspace} --json")
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert "workspace" in data["data"]
    assert "runtimes" in data["data"]
    assert "runtime_count" in data["data"]
    assert "trace_count" in data["data"]


def test_status_json_empty_workspace(run_cli, workspace):
    """`arc status --json` on empty workspace shows zero traces."""
    result = run_cli(f"status --workspace {workspace} --json")
    data = json.loads(result.stdout)
    assert data["data"]["trace_count"] == 0


def test_status_json_with_runtimes(run_cli, workspace):
    """`arc status --json` reports runtime detection results."""
    result = run_cli(f"status --workspace {workspace} --json")
    data = json.loads(result.stdout)
    assert isinstance(data["data"]["runtimes"], list)
    for rt in data["data"]["runtimes"]:
        assert "id" in rt
        assert "detected" in rt
        assert "can_run" in rt


# ─── doctor all ────────────────────────────────────────────────────────────────


def test_doctor_all_text(run_cli):
    """`arc doctor all` prints diagnostic output."""
    result = run_cli("doctor all")
    assert result.exit_code in (0, 1)  # may exit 1 if offline, that's fine
    assert "checks" in result.stdout.lower() or "python" in result.stdout.lower()


def test_doctor_all_json(run_cli):
    """`arc doctor all --json` returns valid JSON envelope with checks."""
    result = run_cli("doctor all --json")
    assert result.exit_code in (0, 1)
    data = json.loads(result.stdout)
    assert "ok" in data
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    check_names = {c["check"] for c in checks}
    assert "python" in check_names
    assert "cli" in check_names
    assert "runtimes" in check_names
    assert "workspace_storage" in check_names
    assert len(checks) >= 5  # python, cli, runtimes, daemon, swarmgraph_cli, providers, workspace_storage


def test_doctor_all_json_python_check(run_cli):
    """`arc doctor all --json` includes python version check."""
    result = run_cli("doctor all --json")
    data = json.loads(result.stdout)
    for check in data["data"]["checks"]:
        if check["check"] == "python":
            assert check["ok"] is True
            assert re.match(r"\d+\.\d+\.\d+", check["version"])
            return
    assert False, "No python check found"


def test_doctor_all_json_runtime_check(run_cli):
    """`arc doctor all --json` detects runtimes in workspace."""
    result = run_cli("doctor all --json")
    data = json.loads(result.stdout)
    for check in data["data"]["checks"]:
        if check["check"] == "runtimes":
            assert "detected" in check
            assert "count" in check
            return
    assert False, "No runtimes check found"


def test_doctor_all_offline_daemon(run_cli):
    """`arc doctor all --json` reports daemon as unreachable when not running."""
    result = run_cli("doctor all --json")
    data = json.loads(result.stdout)
    for check in data["data"]["checks"]:
        if check["check"] == "daemon":
            # Daemon is likely not running in test context
            assert "reachable" in check
            return
    assert False, "No daemon check found"
    """`arc health --json` cli check reports version."""
    result = run_cli("health --json")
    data = json.loads(result.stdout)
    for check in data["data"]["checks"]:
        if check["check"] == "cli":
            assert check["ok"] is True
            assert check["version"] == "0.1.0a0"
            return
    assert False, "No cli check found in health output"
