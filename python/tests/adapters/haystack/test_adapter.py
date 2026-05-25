"""Tests for Haystack adapter class and capability report (Phase 31)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.haystack import HaystackAdapter


class TestHaystackAdapter:
    """Test HaystackAdapter class."""

    def test_adapter_id(self):
        adapter = HaystackAdapter()
        assert adapter.adapter_id == "haystack"

    def test_adapter_name(self):
        adapter = HaystackAdapter()
        assert adapter.adapter_name == "Haystack"

    def test_capabilities(self):
        adapter = HaystackAdapter()
        caps = adapter.capabilities()

        assert caps.can_inspect is True
        assert caps.can_export_workflow is True
        assert caps.can_run is False
        assert caps.can_stream_events is False

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_detect_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        adapter = HaystackAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        assert detected is False
        assert confidence == 0.0
        assert evidence == []

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_detect_detected(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "pipe.py").write_text("from haystack import Pipeline\n")

        adapter = HaystackAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        assert detected is True
        assert confidence > 0.0
        assert len(evidence) > 0

    def test_export_empty_workspace(self, tmp_path):
        adapter = HaystackAdapter()
        workflows = adapter.export_workflow(tmp_path)
        assert workflows == []

    def test_export_with_pipeline(self, tmp_path):
        (tmp_path / "pipe.py").write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("retriever", BM25Retriever())\n'
        )

        adapter = HaystackAdapter()
        workflows = adapter.export_workflow(tmp_path)

        assert len(workflows) == 1
        assert workflows[0].runtime == "haystack"

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_capability_report_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        adapter = HaystackAdapter()
        report = adapter.capability_report(tmp_path)

        assert report.detected is False
        assert report.can_run is False
        assert report.availability == "not_detected"
        assert len(report.doctor_actions) == 1
        assert report.doctor_actions[0].id == "install-haystack"

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_capability_report_detected(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "pipe.py").write_text("from haystack import Pipeline\n")

        adapter = HaystackAdapter()
        report = adapter.capability_report(tmp_path)

        assert report.detected is True
        assert report.can_run is False
        assert report.availability == "detected_not_runnable"
        assert report.version == "2.5.0"
        assert "T1" in report.reason
        assert "T2" in report.reason
        assert "gated" in report.reason.lower()
        assert "DAG" in report.reason

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_capability_report_honest_t3_status(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "pipe.py").write_text("from haystack import Pipeline\n")

        adapter = HaystackAdapter()
        report = adapter.capability_report(tmp_path)

        assert report.local_real_gated is True
        assert report.local_real_available is False
        assert report.provider_backed is False
        assert report.fake_offline_supported is False


class TestHaystackAdapterConformance:
    """Test Haystack adapter against conformance checks."""

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_no_false_positive_on_empty_dir(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        adapter = HaystackAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        if detected:
            assert len(evidence) > 0, "Detected with no evidence"
        else:
            assert confidence == 0.0

    def test_detect_returns_valid_types(self, tmp_path):
        adapter = HaystackAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

        assert isinstance(detected, bool)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert isinstance(evidence, list)

    def test_capabilities_returns_valid_type(self):
        from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities

        adapter = HaystackAdapter()
        caps = adapter.capabilities()

        assert isinstance(caps, RuntimeCapabilities)

    def test_export_returns_list(self, tmp_path):
        from agent_runtime_cockpit.protocol.schemas import WorkflowInfo

        adapter = HaystackAdapter()
        workflows = adapter.export_workflow(tmp_path)

        assert isinstance(workflows, list)
        assert all(isinstance(w, WorkflowInfo) for w in workflows)

    def test_run_workflow_raises_not_implemented(self, tmp_path):
        import asyncio

        adapter = HaystackAdapter()

        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.run_workflow("test-wf"))
