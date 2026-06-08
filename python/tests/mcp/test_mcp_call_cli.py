"""arc mcp call — in-process risk-gated tool invocation (Batch 7 T12 / B2P-04a)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._subapps import mcp_app
from agent_runtime_cockpit.security.trust import trust_workspace

runner = CliRunner()


def _call(args: list[str]) -> dict:
    res = runner.invoke(mcp_app, args)
    return json.loads(res.stdout)


def test_mcp_call_invokes_tool_through_risk_gate(tmp_path: Path) -> None:
    trust_workspace(tmp_path, note="test")
    data = _call(
        [
            "call",
            "arc_swarmgraph_plan",
            "--args",
            json.dumps({"task": "build a REST API and write tests"}),
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert data["ok"] is True
    assert data["data"]["planner"] == "deterministic"
    assert data["data"]["provider_backed"] is False


def test_mcp_call_unknown_tool(tmp_path: Path) -> None:
    trust_workspace(tmp_path, note="test")
    res = runner.invoke(mcp_app, ["call", "no_such_tool", "--workspace", str(tmp_path), "--json"])
    assert res.exit_code == 1
    assert json.loads(res.stdout)["ok"] is False


def test_mcp_call_untrusted_workspace_denied(tmp_path: Path) -> None:
    # No trust marker → must fail closed with a clean envelope (not a traceback).
    res = runner.invoke(mcp_app, ["call", "arc_doctor", "--workspace", str(tmp_path), "--json"])
    assert res.exit_code == 1
    assert json.loads(res.stdout)["ok"] is False


def test_mcp_call_invalid_args_json(tmp_path: Path) -> None:
    trust_workspace(tmp_path, note="test")
    res = runner.invoke(
        mcp_app,
        ["call", "arc_doctor", "--args", "{not json", "--workspace", str(tmp_path), "--json"],
    )
    assert res.exit_code == 2
