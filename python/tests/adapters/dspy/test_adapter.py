"""Tests for DSPy adapter class and capability report (Phase 30)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.dspy import DSPyAdapter


class TestDSPyAdapter:
    """Test DSPyAdapter class."""

    def test_adapter_id(self):
        adapter = DSPyAdapter()
        assert adapter.adapter_id == "dspy"

    def test_adapter_name(self):
        adapter = DSPyAdapter()
        assert adapter.adapter_name == "DSPy"

    def test_capabilities(self):
        adapter = DSPyAdapter()
        caps = adapter.capabilities()

        assert caps.can_inspect is True
        assert caps.can_export_workflow is True
        assert caps.can_run is False
        assert caps.can_stream_events is False

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_detect_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        adapter = DSPyAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        assert detected is False
        assert confidence == 0.0
        assert evidence == []

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_detect_detected(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "program.py").write_text("import dspy\n")

        adapter = DSPyAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        assert detected is True
        assert confidence > 0.0
        assert len(evidence) > 0

    def test_export_empty_workspace(self, tmp_path):
        adapter = DSPyAdapter()
        workflows = adapter.export_workflow(tmp_path)
        assert workflows == []

    def test_export_with_signature(self, tmp_path):
        (tmp_path / "sig.py").write_text(
            "import dspy\n"
            "class QA(dspy.Signature):\n"
            "    question: str = dspy.InputField()\n"
            "    answer: str = dspy.OutputField()\n"
        )

        adapter = DSPyAdapter()
        workflows = adapter.export_workflow(tmp_path)

        assert len(workflows) == 1
        assert workflows[0].runtime == "dspy"

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_capability_report_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        adapter = DSPyAdapter()
        report = adapter.capability_report(tmp_path)

        assert report.detected is False
        assert report.can_run is False
        assert report.availability == "not_detected"
        assert len(report.doctor_actions) == 1
        assert report.doctor_actions[0].id == "install-dspy"

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_capability_report_detected(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "program.py").write_text("import dspy\n")

        adapter = DSPyAdapter()
        report = adapter.capability_report(tmp_path)

        assert report.detected is True
        assert report.can_run is False
        assert report.availability == "detected_not_runnable"
        assert report.version == "2.5.0"
        assert "T1" in report.reason
        assert "T2" in report.reason
        assert "gated" in report.reason.lower()

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_capability_report_honest_t3_status(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "program.py").write_text("import dspy\n")

        adapter = DSPyAdapter()
        report = adapter.capability_report(tmp_path)

        assert report.local_real_gated is True
        assert report.local_real_available is False
        assert report.provider_backed is False
        assert report.fake_offline_supported is False


class TestDSPyAdapterConformance:
    """Test DSPy adapter against conformance checks."""

    def test_no_false_positive_on_empty_dir(self, tmp_path):
        adapter = DSPyAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        if detected:
            assert len(evidence) > 0, "Detected with no evidence"
        else:
            assert confidence == 0.0

    def test_detect_returns_valid_types(self, tmp_path):
        adapter = DSPyAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        assert isinstance(detected, bool)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert isinstance(evidence, list)

    def test_capabilities_returns_valid_type(self):
        from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities

        adapter = DSPyAdapter()
        caps = adapter.capabilities()

        assert isinstance(caps, RuntimeCapabilities)

    def test_export_returns_list(self, tmp_path):
        from agent_runtime_cockpit.protocol.schemas import WorkflowInfo

        adapter = DSPyAdapter()
        workflows = adapter.export_workflow(tmp_path)

        assert isinstance(workflows, list)
        assert all(isinstance(w, WorkflowInfo) for w in workflows)

    def test_run_workflow_raises_not_implemented(self, tmp_path):
        import asyncio

        adapter = DSPyAdapter()

        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.run_workflow("test-wf"))
