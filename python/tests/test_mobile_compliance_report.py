"""Tests for Phase 12d: aggregated compliance report generator."""

from __future__ import annotations

from typer.testing import CliRunner

from agent_runtime_cockpit.cli.mobile import mobile_app
from agent_runtime_cockpit.mobile import build_default_manifest, list_capabilities
from agent_runtime_cockpit.mobile.compliance import generate_compliance_report

runner = CliRunner()


def _manifest():
    caps = [
        c
        for c in list_capabilities()
        if c.id in ("device.camera.capture.mock", "app.memory.write.mock")
    ]
    return build_default_manifest("test.compliance", "Compliance Test", capabilities=caps)


def test_report_aggregates_all_sections() -> None:
    report = generate_compliance_report(_manifest())
    assert report["advisory"] is True and report["requires_human_review"] is True
    assert set(report["ios"]) == {"usage_strings", "privacy_manifest"}
    assert set(report["android"]) == {"manifest_permissions", "data_safety"}
    assert "review_notes" in report
    assert report["summary"]["capability_count"] == 2
    assert "device.camera.capture.mock" in report["summary"]["sensitive_capabilities"]


def test_report_is_deterministic() -> None:
    assert generate_compliance_report(_manifest()) == generate_compliance_report(_manifest())


def test_cli_compliance_report() -> None:
    res = runner.invoke(mobile_app, ["generate", "compliance-report", "--json"])
    assert res.exit_code == 0, res.output
    assert "requires_human_review" in res.output
