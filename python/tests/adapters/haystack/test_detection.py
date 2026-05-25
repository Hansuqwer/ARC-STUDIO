"""Tests for Haystack detection (Phase 31 T1)."""

from __future__ import annotations

from unittest.mock import Mock, patch

from agent_runtime_cockpit.adapters.haystack.detect import (
    HaystackDetectionResult,
    detect_haystack,
    detect_haystack_import,
    scan_workspace_for_haystack,
)


class TestHaystackImportDetection:
    """Test haystack import detection."""

    @patch("importlib.util.find_spec")
    def test_detect_when_not_installed(self, mock_find_spec):
        mock_find_spec.return_value = None
        detected, version = detect_haystack_import()
        assert detected is False
        assert version is None

    @patch("importlib.util.find_spec")
    def test_detect_handles_import_error(self, mock_find_spec):
        mock_find_spec.return_value = Mock()
        detected, version = detect_haystack_import()
        assert isinstance(detected, bool)
        assert version is None or isinstance(version, str)


class TestWorkspaceScanning:
    """Test workspace scanning for Haystack usage."""

    def test_scan_empty_workspace(self, tmp_path):
        evidence, has_pipes, has_comps, has_yaml = scan_workspace_for_haystack(tmp_path)
        assert evidence == []
        assert has_pipes is False
        assert has_comps is False
        assert has_yaml is False

    def test_scan_detects_import_statement(self, tmp_path):
        test_file = tmp_path / "pipeline.py"
        test_file.write_text("import haystack\n")

        evidence, _, _, _ = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) == 1
        assert "pipeline.py" in evidence[0]

    def test_scan_detects_from_import(self, tmp_path):
        test_file = tmp_path / "main.py"
        test_file.write_text("from haystack import Pipeline\n")

        evidence, _, _, _ = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) == 1
        assert "main.py" in evidence[0]

    def test_scan_detects_pipelines(self, tmp_path):
        test_file = tmp_path / "pipe.py"
        test_file.write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("retriever", BM25Retriever())\n'
            'pipe.connect("retriever.documents", "generator.prompt")\n'
        )

        evidence, has_pipes, _, _ = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) >= 1
        assert has_pipes is True

    def test_scan_detects_components(self, tmp_path):
        test_file = tmp_path / "custom.py"
        test_file.write_text(
            "from haystack import component\n"
            "@component\n"
            "class MyComponent:\n"
            "    def run(self, text: str):\n"
            "        pass\n"
        )

        evidence, _, has_comps, _ = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) >= 1
        assert has_comps is True

    def test_scan_detects_yaml_pipelines(self, tmp_path):
        yaml_file = tmp_path / "pipeline.yaml"
        yaml_file.write_text(
            "components:\n"
            "  retriever:\n"
            "    type: haystack.components.retrievers.InMemoryBM25Retriever\n"
        )

        evidence, _, _, has_yaml = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) >= 1
        assert has_yaml is True

    def test_scan_detects_requirements_txt(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("haystack-ai>=2.0\n")

        evidence, _, _, _ = scan_workspace_for_haystack(tmp_path)
        assert "requirements.txt" in evidence

    def test_scan_detects_farm_haystack_legacy(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("farm-haystack>=1.0\n")

        evidence, _, _, _ = scan_workspace_for_haystack(tmp_path)
        assert "requirements.txt" in evidence

    def test_scan_detects_pyproject_toml(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\ndependencies = ["haystack-ai>=2.0"]\n')

        evidence, _, _, _ = scan_workspace_for_haystack(tmp_path)
        assert "pyproject.toml" in evidence

    def test_scan_ignores_venv(self, tmp_path):
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "pipe.py"
        venv_file.write_text("from haystack import Pipeline\npipe = Pipeline()\n")

        evidence, _, _, _ = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) == 0

    def test_scan_multiple_files(self, tmp_path):
        (tmp_path / "pipe.py").write_text("from haystack import Pipeline\npipe = Pipeline()\n")
        (tmp_path / "comp.py").write_text(
            "from haystack import component\n@component\nclass C:\n    def run(self): pass\n"
        )
        (tmp_path / "requirements.txt").write_text("haystack-ai>=2.0\n")

        evidence, has_pipes, has_comps, _ = scan_workspace_for_haystack(tmp_path)
        assert len(evidence) == 3
        assert has_pipes is True
        assert has_comps is True


class TestFullDetection:
    """Test full detection logic."""

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_not_detected_when_not_installed(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)

        result = detect_haystack(tmp_path)

        assert result.detected is False
        assert result.confidence == 0.0
        assert result.version is None

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_detected_with_base_confidence(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")

        result = detect_haystack(tmp_path)

        assert result.detected is True
        assert result.confidence == 0.3
        assert result.version == "2.5.0"

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_detected_with_workspace_usage(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "pipe.py").write_text("from haystack import Pipeline\n")

        result = detect_haystack(tmp_path)

        assert result.detected is True
        assert result.confidence == 0.6

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_detected_with_full_signals(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "pipe.py").write_text(
            "from haystack import Pipeline, component\n"
            "pipe = Pipeline()\n"
            "pipe.add_component('r', Retriever())\n"
            "pipe.connect('r.docs', 'g.prompt')\n"
            "@component\n"
            "class MyComp:\n"
            "    def run(self): pass\n"
        )
        (tmp_path / "pipeline.yaml").write_text(
            "components:\n  retriever:\n    type: haystack.components.retrievers.BM25\n"
        )

        result = detect_haystack(tmp_path)

        assert result.detected is True
        assert result.confidence == 1.0
        assert result.has_pipelines is True
        assert result.has_components is True
        assert result.has_yaml_pipelines is True

    @patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import")
    def test_detected_from_workspace_only(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        (tmp_path / "pipe.py").write_text("from haystack import Pipeline\n")

        result = detect_haystack(tmp_path)

        assert result.detected is True
        assert result.confidence == 0.2

    def test_result_is_named_tuple(self, tmp_path):
        with patch("agent_runtime_cockpit.adapters.haystack.detect.detect_haystack_import") as m:
            m.return_value = (True, "2.5.0")
            result = detect_haystack(tmp_path)

            assert isinstance(result, HaystackDetectionResult)
            assert hasattr(result, "detected")
            assert hasattr(result, "confidence")
            assert hasattr(result, "evidence")
            assert hasattr(result, "version")
            assert hasattr(result, "has_pipelines")
            assert hasattr(result, "has_components")
            assert hasattr(result, "has_yaml_pipelines")
