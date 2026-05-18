"""
Tests: RuntimeCapabilities and CapabilityReport cockpit primitive flags.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.adapters.base import CapabilityReport
from agent_runtime_cockpit.adoption.langgraph_runner import LangGraphAdoptionRunner
from agent_runtime_cockpit.adoption.protocol import AdoptionStatus
from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.orchestration.runtime_router import LangGraphSwarmGraphFakeAdapter
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities


class TestRuntimeCapabilitiesCockpitPrimitives:
    """RuntimeCapabilities carries cockpit primitive emission flags."""

    def test_defaults_are_false(self):
        caps = RuntimeCapabilities()
        assert caps.can_emit_contract is False
        assert caps.can_emit_receipt is False
        assert caps.can_emit_autopsy is False
        assert caps.can_emit_evidence is False
        assert caps.has_stable_ids is False

    def test_set_contract_flag(self):
        caps = RuntimeCapabilities(can_emit_contract=True)
        assert caps.can_emit_contract is True

    def test_set_receipt_flag(self):
        caps = RuntimeCapabilities(can_emit_receipt=True)
        assert caps.can_emit_receipt is True

    def test_set_autopsy_flag(self):
        caps = RuntimeCapabilities(can_emit_autopsy=True)
        assert caps.can_emit_autopsy is True

    def test_set_evidence_flag(self):
        caps = RuntimeCapabilities(can_emit_evidence=True)
        assert caps.can_emit_evidence is True

    def test_set_stable_ids_flag(self):
        caps = RuntimeCapabilities(has_stable_ids=True)
        assert caps.has_stable_ids is True

    def test_all_cockpit_flags(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            can_emit_receipt=True,
            can_emit_autopsy=True,
            can_emit_evidence=True,
            has_stable_ids=True,
        )
        assert caps.can_emit_contract is True
        assert caps.can_emit_receipt is True
        assert caps.can_emit_autopsy is True
        assert caps.can_emit_evidence is True
        assert caps.has_stable_ids is True

    def test_serialization_includes_flags(self):
        caps = RuntimeCapabilities(can_emit_contract=True, has_stable_ids=True)
        data = caps.model_dump()
        assert "can_emit_contract" in data
        assert data["can_emit_contract"] is True
        assert "has_stable_ids" in data
        assert data["has_stable_ids"] is True


class TestCapabilityReportCockpitPrimitives:
    """CapabilityReport carries cockpit primitive flags."""

    def test_defaults_are_false(self):
        report = CapabilityReport(
            runtime_id="test", detected=False, can_run=False,
            availability="not_detected",
        )
        assert report.can_emit_contract is False
        assert report.can_emit_receipt is False
        assert report.can_emit_autopsy is False
        assert report.can_emit_evidence is False
        assert report.has_stable_ids is False
        assert report.test_level == "unknown"
        assert report.fake_offline_supported is False
        assert report.local_real_gated is False
        assert report.local_real_available is False
        assert report.provider_backed is False

    def test_set_cockpit_flags(self):
        report = CapabilityReport(
            runtime_id="test", detected=True, can_run=True,
            availability="runnable",
            can_emit_contract=True,
            can_emit_receipt=True,
            can_emit_autopsy=True,
            can_emit_evidence=True,
            has_stable_ids=True,
        )
        assert report.can_emit_contract is True
        assert report.can_emit_receipt is True
        assert report.can_emit_autopsy is True
        assert report.can_emit_evidence is True
        assert report.has_stable_ids is True

    def test_serialization_includes_flags(self):
        report = CapabilityReport(
            runtime_id="test", detected=True, can_run=True,
            availability="runnable",
            can_emit_contract=True,
        )
        data = report.model_dump()
        assert "can_emit_contract" in data
        assert data["can_emit_contract"] is True
        assert "can_emit_receipt" in data
        assert data["can_emit_receipt"] is False

    def test_serialization_includes_evidence_classification_defaults(self):
        report = CapabilityReport(
            runtime_id="test", detected=True, can_run=True,
            availability="runnable",
        )
        data = report.model_dump()
        assert data["test_level"] == "unknown"
        assert data["fake_offline_supported"] is False
        assert data["local_real_gated"] is False
        assert data["local_real_available"] is False
        assert data["provider_backed"] is False

    def test_langgraph_swarmgraph_fake_offline_classification(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
        monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)
        data = LangGraphSwarmGraphFakeAdapter().capability_report(tmp_path).model_dump()

        assert data["runtime_id"] == "langgraph+swarmgraph"
        assert data["can_run"] is True
        assert data["test_level"] == "fake_offline"
        assert data["fake_offline_supported"] is True
        assert data["local_real_gated"] is True
        assert data["local_real_available"] is False
        assert data["provider_backed"] is False
        assert data["requires_paid_calls"] is False
        assert data["required_env"] == ["ARC_REAL_RUNTIME_SMOKE", "ARC_LANGGRAPH_SWARMGRAPH_REAL"]

    def test_langgraph_swarmgraph_partial_gate_remains_gated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", "1")
        monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
        data = LangGraphSwarmGraphFakeAdapter().capability_report(tmp_path).model_dump()

        assert data["test_level"] == "fake_offline"
        assert data["local_real_gated"] is True
        assert data["local_real_available"] is False
        assert data["provider_backed"] is False
        assert data["requires_paid_calls"] is False
        assert data["required_env"] == ["ARC_REAL_RUNTIME_SMOKE"]

    def test_langgraph_swarmgraph_local_real_gate_classification(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
        monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", "1")
        data = LangGraphSwarmGraphFakeAdapter().capability_report(tmp_path).model_dump()

        assert data["test_level"] == "gated_local_real"
        assert data["fake_offline_supported"] is True
        assert data["local_real_gated"] is False
        assert data["local_real_available"] is True
        assert data["provider_backed"] is False
        assert data["requires_paid_calls"] is False
        assert data["required_env"] == []
        assert "local-real" in data["reason"]
        assert "no provider-backed claim" in data["reason"]
        assert "local-real gates ARC_REAL_RUNTIME_SMOKE=1 + ARC_LANGGRAPH_SWARMGRAPH_REAL=1" in data["detected_artifacts"]

    def test_runtimes_cli_default_keeps_langgraph_swarmgraph_fake_offline(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
        monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)

        result = CliRunner().invoke(app, [
            "runtimes", "--workspace", str(tmp_path), "--capabilities", "--json",
        ])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)["data"]
        langgraph_sg = next(
            runtime for runtime in payload["runtimes"]
            if runtime["runtime_id"] == "langgraph+swarmgraph"
        )
        assert langgraph_sg["test_level"] == "fake_offline"
        assert langgraph_sg["fake_offline_supported"] is True
        assert langgraph_sg["local_real_gated"] is True
        assert langgraph_sg["local_real_available"] is False
        assert langgraph_sg["provider_backed"] is False
        assert langgraph_sg["requires_paid_calls"] is False
        assert langgraph_sg["required_env"] == [
            "ARC_REAL_RUNTIME_SMOKE",
            "ARC_LANGGRAPH_SWARMGRAPH_REAL",
        ]

    def test_runtimes_cli_requires_both_local_real_gates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
        monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)

        result = CliRunner().invoke(app, [
            "runtimes", "--workspace", str(tmp_path), "--capabilities", "--json",
        ])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)["data"]
        langgraph_sg = next(
            runtime for runtime in payload["runtimes"]
            if runtime["runtime_id"] == "langgraph+swarmgraph"
        )
        assert langgraph_sg["test_level"] == "fake_offline"
        assert langgraph_sg["local_real_gated"] is True
        assert langgraph_sg["local_real_available"] is False
        assert langgraph_sg["provider_backed"] is False
        assert langgraph_sg["requires_paid_calls"] is False
        assert langgraph_sg["required_env"] == ["ARC_LANGGRAPH_SWARMGRAPH_REAL"]

    def test_langgraph_runner_reports_missing_dependency(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "agent_runtime_cockpit.adoption.langgraph_runner.importlib.util.find_spec",
            lambda name: None if name == "langgraph" else object(),
        )

        capability = LangGraphAdoptionRunner().check_availability(tmp_path)

        assert capability.status is AdoptionStatus.NOT_RUNNABLE
        assert capability.reason == "LangGraph package not installed."
        assert capability.doctor_actions[0]["id"] == "install-langgraph"


def test_real_runtime_smoke_workflow_is_dual_gated_and_provider_env_free():
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "real-runtime-smoke.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "ARC_REAL_RUNTIME_SMOKE: '1'" in text
    assert "ARC_LANGGRAPH_SWARMGRAPH_REAL: '1'" in text
    assert "ARC_SWARMGRAPH_RUN_BACKEND: ''" in text
    assert "ARC_SWARMGRAPH_ALLOW_COSTS: ''" in text
    assert "OPENAI_API_KEY" not in text
    assert "ANTHROPIC_API_KEY" not in text
    assert "ARC_SWARMGRAPH_ALLOW_COSTS: '1'" not in text
