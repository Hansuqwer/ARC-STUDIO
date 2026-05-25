"""Tests for Smolagents adapter."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.smolagents import SmolagentsAdapter
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities


def test_adapter_identity():
    adapter = SmolagentsAdapter()
    assert adapter.adapter_id == "smolagents"
    assert adapter.adapter_name == "Smolagents"


def test_capabilities_are_honest():
    caps = SmolagentsAdapter().capabilities()
    assert isinstance(caps, RuntimeCapabilities)
    assert caps.can_inspect is True
    assert caps.can_export_workflow is True
    assert caps.can_run is False
    assert caps.requires_network is True
    assert caps.requires_shell is True


def test_detect_not_detected(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.smolagents.detect.detect_smolagents_import",
        return_value=(False, None),
    ):
        detected, confidence, evidence = SmolagentsAdapter().detect(tmp_path)
    assert detected is False
    assert confidence == 0.0
    assert evidence == []


def test_export_workflow(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from smolagents import CodeAgent\nagent = CodeAgent(tools=[], model=model)\n"
    )
    workflows = SmolagentsAdapter().export_workflow(tmp_path)
    assert len(workflows) == 1
    assert workflows[0].runtime == "smolagents"


def test_capability_report_not_detected(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.smolagents.detect.detect_smolagents_import",
        return_value=(False, None),
    ):
        report = SmolagentsAdapter().capability_report(tmp_path)
    assert report.detected is False
    assert report.availability == "not_detected"
    assert report.doctor_actions[0].id == "install-smolagents"


def test_capability_report_detected_mentions_gate(tmp_path):
    (tmp_path / "agent.py").write_text("from smolagents import CodeAgent\n")
    with patch(
        "agent_runtime_cockpit.adapters.smolagents.detect.detect_smolagents_import",
        return_value=(False, None),
    ):
        report = SmolagentsAdapter().capability_report(tmp_path)
    assert report.detected is True
    assert report.can_run is False
    assert report.local_real_gated is True
    assert "ARC_ALLOW_LIVE_PROVIDER_TESTS=true" in (report.reason or "")
    assert "CodeAgent" in (report.reason or "")


def test_run_workflow_not_implemented():
    with pytest.raises(NotImplementedError):
        asyncio.run(SmolagentsAdapter().run_workflow("wf"))
