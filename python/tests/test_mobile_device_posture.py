"""R79.3 / Batch 7 T27: device posture / MDM hook interface (fixtures-only, deterministic)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.mobile import (
    DevicePosture,
    FixtureDevicePostureHook,
    PosturePolicy,
    evaluate_posture,
)


def test_default_fixture_posture_allowed() -> None:
    decision = evaluate_posture(FixtureDevicePostureHook().read())
    assert decision.allowed is True
    assert decision.violations == []
    assert decision.simulator_preview is True  # never real device data


def test_jailbroken_denied() -> None:
    decision = evaluate_posture(DevicePosture(jailbroken=True))
    assert decision.allowed is False
    assert "device_jailbroken" in decision.violations


def test_require_mdm_denies_unenrolled() -> None:
    decision = evaluate_posture(DevicePosture(mdm_enrolled=False), PosturePolicy(require_mdm=True))
    assert decision.allowed is False
    assert "not_mdm_enrolled" in decision.violations


def test_unencrypted_denied_by_default() -> None:
    decision = evaluate_posture(DevicePosture(storage_encrypted=False))
    assert decision.allowed is False
    assert "storage_not_encrypted" in decision.violations


def test_cli_posture_check() -> None:
    from agent_runtime_cockpit.cli._subapps import mobile_app

    res = CliRunner().invoke(mobile_app, ["posture", "check", "--require-mdm", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)["data"]
    assert data["allowed"] is False  # default fixture is not MDM-enrolled
    assert data["simulator_preview"] is True
