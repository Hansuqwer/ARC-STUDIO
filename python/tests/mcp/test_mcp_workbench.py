"""Tests for ``arc mcp workbench`` CLI commands (Phase 78 / R48).

Tests cover:
1. status with no config is stable not error
2. status with trusted workspace shows server state
3. status with untrusted workspace shows blocker
4. inspect with fixture server (in-process) works
5. inspect missing server argument
6. inspect timed-out server
7. read-only diagnostic flag in response
8. no HTTP listener
9. audit event emitted for inspect
10. trust state included in status

No live network, no Docker, no external MCP servers in CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.security.trust import trust_workspace

runner = CliRunner()


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def trusted_workspace(tmp_path: Path) -> Path:
    trust_workspace(tmp_path, note="mcp-workbench-test")
    return tmp_path


# ── Helpers ──────────────────────────────────────────────────────────────────


def _invoke_status(tmp_path: Path) -> dict:
    """Run the workbench status command and return parsed output."""
    from agent_runtime_cockpit.cli._app import app

    local_runner = CliRunner()
    result = local_runner.invoke(
        app,
        ["mcp", "workbench", "status", "--json", "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0, f"CLI failed: {result.stdout} {result.stderr}"
    return json.loads(result.stdout)


_MOCK_FIXTURE_SERVER_SCRIPT = """
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fixture-server", json_response=True)

@mcp.tool()
def greet(name: str) -> str:
    \"\"\"Greet someone.\"\"\"
    return f"Hello, {name}!"

@mcp.tool()
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

@mcp.resource("fixture://greetings/{name}")
def greet_resource(name: str) -> str:
    \"\"\"Greeting resource.\"\"\"
    return f"Hello, {name}!"

@mcp.resource("fixture://info")
def info_resource() -> str:
    \"\"\"Static info resource.\"\"\"
    return '{"version": "1.0.0"}'

@mcp.prompt()
def greeting_prompt(name: str) -> str:
    \"\"\"Greeting prompt template.\"\"\"
    return f"Please greet {name} politely."

mcp.run(transport="stdio")
"""


def _write_fixture_server(tmp_path: Path) -> Path:
    path = tmp_path / "_fixture_server.py"
    path.write_text(_MOCK_FIXTURE_SERVER_SCRIPT)
    return path


# ── Test: status with no config is stable (not error) ────────────────────────


def test_status_no_config_is_stable_not_error(tmp_path: Path):
    """status returns ok even when workspace is untrusted."""
    result = _invoke_status(tmp_path)
    assert result["ok"] is True
    assert result["data"]["workspace"] == str(tmp_path)
    assert result["data"]["server_creatable"] is False
    assert "untrusted" in result["data"]["server_blocker"].lower()
    assert result["data"]["trust"]["level"] == "untrusted"
    assert result["data"]["diagnostic"] == "read-only"


# ── Test: status with trusted workspace shows server state ───────────────────


def test_status_with_trusted_workspace(tmp_path: Path):
    """status shows server state with trusted workspace."""
    trust_workspace(tmp_path, note="test")
    result = _invoke_status(tmp_path)
    assert result["ok"] is True
    assert result["data"]["server_creatable"] is True
    assert result["data"]["server_blocker"] is None
    assert len(result["data"]["tools"]) >= 11
    assert "arc_doctor" in result["data"]["tools"]
    assert "arc_run_status" in result["data"]["tools"]
    assert len(result["data"]["resources"]) >= 3
    assert result["data"]["trust"]["level"] == "trusted"


# ── Test: status with untrusted workspace shows blocker ──────────────────────


def test_status_untrusted_workspace_shows_blocker(tmp_path: Path):
    """status shows server blocker for untrusted workspace."""
    result = _invoke_status(tmp_path)
    assert result["ok"] is True
    assert result["data"]["server_creatable"] is False
    assert result["data"]["server_blocker"] is not None
    assert result["data"]["trust"]["level"] == "untrusted"


# ── Test: inspect with fixture server works ──────────────────────────────────


def test_inspect_with_fixture_server(tmp_path: Path, trusted_workspace: Path):
    """Inspect connects to a fixture MCP server, lists tools/resources/prompts."""
    from agent_runtime_cockpit.cli.mcp import _inspect_server

    script_path = _write_fixture_server(tmp_path)
    result = _inspect_server(
        server_cmd=[sys.executable, str(script_path)],
        workspace=trusted_workspace,
        timeout=10.0,
    )

    assert "error" not in result, f"Inspect failed: {result.get('error')}"
    assert len(result["tools"]) >= 2
    assert len(result["resources"]) >= 1

    tool_names = [t["name"] for t in result["tools"]]
    assert "greet" in tool_names
    assert "add" in tool_names

    uri_templates = [r["uriTemplate"] for r in result["resources"]]
    assert "fixture://greetings/{name}" in uri_templates

    prompt_names = [p["name"] for p in result["prompts"]]
    assert "greeting_prompt" in prompt_names


# ── Test: inspect missing server argument ────────────────────────────────────


def test_inspect_missing_server_argument(tmp_path: Path):
    """inspect without server argument returns error."""
    from agent_runtime_cockpit.cli._app import app

    local_runner = CliRunner()
    result = local_runner.invoke(
        app,
        ["mcp", "workbench", "inspect", "--json", "--workspace", str(tmp_path)],
    )
    assert result.exit_code != 0


# ── Test: inspect timed-out server ───────────────────────────────────────────


def test_inspect_timeout_short(tmp_path: Path):
    """inspect with very short timeout handles error gracefully."""
    from agent_runtime_cockpit.cli.mcp import _inspect_server

    result = _inspect_server(
        server_cmd=[sys.executable, "-c", "import time; time.sleep(60)"],
        workspace=tmp_path,
        timeout=0.1,
    )
    assert "error" in result
    assert "inspect" in result["error"].lower()


# ── Test: read-only diagnostic flag ──────────────────────────────────────────


def test_status_diagnostic_read_only(tmp_path: Path):
    """status response includes diagnostic: read-only."""
    result = _invoke_status(tmp_path)
    assert result["data"]["diagnostic"] == "read-only"


# ── Test: no HTTP listener ───────────────────────────────────────────────────


def test_status_no_http_listener(tmp_path: Path):
    """status does not open any HTTP listener."""
    trust_workspace(tmp_path, note="test")
    result = _invoke_status(tmp_path)
    assert result["ok"] is True
    assert "transport" not in result["data"] or result["data"].get("transport") != "http"


# ── Test: audit event emitted for inspect ────────────────────────────────────


def test_inspect_emits_audit_event(tmp_path: Path):
    """inspect command emits an audit event."""
    from agent_runtime_cockpit.cli.mcp import _inspect_server

    _inspect_server(
        server_cmd=[sys.executable, "-c", "print('not-mcp')"],
        workspace=tmp_path,
        timeout=1.0,
    )

    audit_path = tmp_path / ".arc" / "audit" / "mcp.events.jsonl"
    assert audit_path.exists()

    lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
    events = [json.loads(l) for l in lines if json.loads(l).get("type") == "mcp_workbench_inspect"]
    assert len(events) >= 1

    event = events[-1]
    assert event["type"] == "mcp_workbench_inspect"
    assert "server_cmd" in event
    assert "workspace" in event
    assert event["workspace"] == str(tmp_path)


# ── Test: trust state included in status ─────────────────────────────────────


def test_status_includes_trust_state(tmp_path: Path):
    """status response always includes trust state."""
    result = _invoke_status(tmp_path)
    assert "trust" in result["data"]
    assert "level" in result["data"]["trust"]
    assert "reason" in result["data"]["trust"]
    assert result["data"]["trust"]["level"] in ("trusted", "untrusted", "partial")


def test_workbench_inspect_denies_network_by_default(
    trusted_workspace: Path, monkeypatch: pytest.MonkeyPatch
):
    from agent_runtime_cockpit.cli._app import app

    monkeypatch.chdir(trusted_workspace)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(trusted_workspace / "audit"))
    result = runner.invoke(
        app,
        [
            "mcp",
            "workbench",
            "inspect",
            "curl https://example.com",
            "--json",
            "--workspace",
            str(trusted_workspace),
        ],
    )
    assert result.exit_code == 3
    data = json.loads(result.output)
    assert data["error"]["details"]["classification"] == "network"
    events = (trusted_workspace / "audit" / "sandbox.events.jsonl").read_text(encoding="utf-8")
    assert '"type":"SANDBOX_DENIED"' in events


def test_workbench_inspect_denies_unknown_by_default(
    trusted_workspace: Path, monkeypatch: pytest.MonkeyPatch
):
    from agent_runtime_cockpit.cli._app import app

    monkeypatch.chdir(trusted_workspace)
    result = runner.invoke(
        app,
        [
            "mcp",
            "workbench",
            "inspect",
            "custom-mcp-server",
            "--json",
            "--workspace",
            str(trusted_workspace),
        ],
    )
    assert result.exit_code == 3
    assert json.loads(result.output)["error"]["details"]["classification"] == "unknown"


def test_workbench_inspect_allowed_readonly_emits_sandbox_audit(
    trusted_workspace: Path, monkeypatch: pytest.MonkeyPatch
):
    from agent_runtime_cockpit.cli import mcp as mcp_cli
    from agent_runtime_cockpit.cli._app import app

    monkeypatch.chdir(trusted_workspace)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(trusted_workspace / "audit"))

    def fake_inspect(*args, **kwargs):
        return {"server_cmd": "pwd", "tools": [], "resources": [], "prompts": []}

    monkeypatch.setattr(mcp_cli, "_inspect_server", fake_inspect)
    result = runner.invoke(
        app,
        [
            "mcp",
            "workbench",
            "inspect",
            "pwd",
            "--json",
            "--workspace",
            str(trusted_workspace),
        ],
    )
    assert result.exit_code == 0, result.output
    events = (trusted_workspace / "audit" / "sandbox.events.jsonl").read_text(encoding="utf-8")
    assert '"type":"SANDBOX_COMMAND"' in events
    assert '"classification":"read_only"' in events


def test_workbench_session_start_allowed_readonly_emits_audit(
    trusted_workspace: Path, monkeypatch: pytest.MonkeyPatch
):
    from agent_runtime_cockpit.cli import mcp as mcp_cli
    from agent_runtime_cockpit.cli._app import app
    from agent_runtime_cockpit.mcp.session import McpSessionRecord

    monkeypatch.chdir(trusted_workspace)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(trusted_workspace / "audit"))

    def fake_start_session(*args, **kwargs):
        return McpSessionRecord(
            session_id="fake-session",
            server_cmd=["pwd"],
            pid=123,
            pgid=123,
            started_at="2026-01-01T00:00:00Z",
            last_used_at="2026-01-01T00:00:00Z",
            workspace=str(trusted_workspace),
        )

    monkeypatch.setattr(mcp_cli, "start_session", fake_start_session)
    result = runner.invoke(
        app,
        [
            "mcp",
            "workbench",
            "session-start",
            "pwd",
            "--json",
            "--workspace",
            str(trusted_workspace),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["session_id"] == "fake-session"
    events = (trusted_workspace / "audit" / "sandbox.events.jsonl").read_text(encoding="utf-8")
    assert '"type":"SANDBOX_COMMAND"' in events


# ── Test: CLI help text ──────────────────────────────────────────────────────


def test_workbench_help_contains_commands():
    """arc mcp workbench --help lists subcommands."""
    from agent_runtime_cockpit.cli._app import app

    local_runner = CliRunner()
    result = local_runner.invoke(app, ["mcp", "workbench", "--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout
    assert "inspect" in result.stdout
