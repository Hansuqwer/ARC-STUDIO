"""Truth-label tests for ``arc mobile doctor`` payload construction."""

from __future__ import annotations


def test_mobile_doctor_truth_payload(monkeypatch):
    from agent_runtime_cockpit.cli import mobile as mobile_cli

    captured = {}

    def fake_out(payload, json_output):
        captured["payload"] = payload
        captured["json_output"] = json_output

    monkeypatch.setattr(mobile_cli, "_out", fake_out)
    monkeypatch.setattr(mobile_cli, "_setup_logging", lambda debug: None)

    mobile_cli.mobile_doctor_cmd(json_output=True, debug=False)

    data = captured["payload"].data
    assert data["runtime_mode"] == "simulator_preview"
    assert data["mock_only"] is True
    assert data["native_bridges"] is False
    assert data["production_ready"] is False
    assert data["enterprise_ready"] is False
    assert data["mcp_gateway"] is False
    assert "No production native mobile bridges" in data["note"]
