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


def test_flags_enable_list_killswitch(tmp_path) -> None:
    store = str(tmp_path / "flags.json")
    en = runner.invoke(mobile_app, ["flags", "enable", "native.camera", "--store", store, "--json"])
    assert en.exit_code == 0, en.output
    assert _json(en)["data"]["flags"]["native.camera"] is True

    lst = runner.invoke(mobile_app, ["flags", "list", "--store", store, "--json"])
    assert _json(lst)["data"]["effective"]["native.camera"] is True

    ks = runner.invoke(mobile_app, ["flags", "kill-switch", "on", "--store", store, "--json"])
    assert _json(ks)["data"]["kill_switch"] is True
    # kill switch overrides effective to off
    assert _json(ks)["data"]["effective"]["native.camera"] is False


def test_flags_killswitch_bad_state(tmp_path) -> None:
    res = runner.invoke(
        mobile_app, ["flags", "kill-switch", "maybe", "--store", str(tmp_path / "f.json")]
    )
    assert res.exit_code == 1


def test_egress_check_allow_deny_block() -> None:
    ok_res = runner.invoke(mobile_app, ["egress", "check", "100", "--budget", "1000", "--json"])
    assert _json(ok_res)["data"]["allowed"] is True

    over = runner.invoke(mobile_app, ["egress", "check", "2000", "--budget", "1000", "--json"])
    assert _json(over)["data"]["allowed"] is False

    crit = runner.invoke(
        mobile_app,
        ["egress", "check", "10", "--budget", "1000", "--classification", "critical", "--json"],
    )
    assert _json(crit)["data"]["allowed"] is False
    assert "blocked" in _json(crit)["data"]["reason"]
