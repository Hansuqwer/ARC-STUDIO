"""Tests for Semantic Kernel adapter class."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.registry import default_registry
from agent_runtime_cockpit.adapters.semantic_kernel import SemanticKernelAdapter
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities
from agent_runtime_cockpit.protocol.schemas import WorkflowInfo


class TestSemanticKernelAdapter:
    def test_adapter_id_and_name(self):
        adapter = SemanticKernelAdapter()
        assert adapter.adapter_id == "semantic_kernel"
        assert adapter.adapter_name == "Semantic Kernel"

    def test_capabilities(self):
        caps = SemanticKernelAdapter().capabilities()
        assert isinstance(caps, RuntimeCapabilities)
        assert caps.can_inspect is True
        assert caps.can_export_workflow is True
        assert caps.can_run is False
        assert caps.can_stream_events is False

    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_detect_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        detected, confidence, evidence = SemanticKernelAdapter().detect(tmp_path)
        assert detected is False
        assert confidence == 0.0
        assert evidence == []

    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_detect_detected(self, mock_import, tmp_path):
        mock_import.return_value = (True, "1.35.0")
        (tmp_path / "app.py").write_text("from semantic_kernel import Kernel\nkernel = Kernel()\n")
        detected, confidence, evidence = SemanticKernelAdapter().detect(tmp_path)
        assert detected is True
        assert confidence > 0.0
        assert evidence

    def test_export_returns_workflow_list(self, tmp_path):
        workflows = SemanticKernelAdapter().export_workflow(tmp_path)
        assert isinstance(workflows, list)
        assert all(isinstance(workflow, WorkflowInfo) for workflow in workflows)

    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_capability_report_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        report = SemanticKernelAdapter().capability_report(tmp_path)
        assert report.detected is False
        assert report.can_run is False
        assert report.availability == "not_detected"
        assert report.doctor_actions[0].id == "install-semantic-kernel"

    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_capability_report_detected_t1_t2_only(self, mock_import, tmp_path):
        mock_import.return_value = (True, "1.35.0")
        (tmp_path / "app.py").write_text("from semantic_kernel import Kernel\nkernel = Kernel()\n")
        report = SemanticKernelAdapter().capability_report(tmp_path)
        assert report.detected is True
        assert report.can_run is False
        assert report.availability == "detected_not_runnable"
        assert report.provider_backed is False
        assert "T1" in report.reason
        assert "T2" in report.reason

    def test_default_registry_includes_semantic_kernel(self):
        adapter = default_registry().get("semantic_kernel")
        assert isinstance(adapter, SemanticKernelAdapter)

    def test_run_workflow_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            asyncio.run(SemanticKernelAdapter().run_workflow("wf"))
