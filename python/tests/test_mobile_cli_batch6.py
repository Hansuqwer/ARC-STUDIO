"""Batch 6 Track C: CLI surfaces for the new mobile modules (gate/flags/egress/queue/...)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli.mobile import mobile_app

runner = CliRunner()


def _json(result):
    return json.loads(result.output)


def test_gate_evaluate_default_denied_fixtures() -> None:
    res = runner.invoke(mobile_app, ["gate", "evaluate", "device.camera.capture.mock", "--json"])
    assert res.exit_code == 0, res.output
    data = _json(res)["data"]
    assert data["eligible"] is False
    assert data["route"] == "fixtures"
    assert "compliance_artifact_missing" in data["missing"]
    assert "signed_plan_invalid" in data["missing"]
