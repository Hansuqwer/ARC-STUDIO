"""Tests for DSPy detection (Phase 30 T1)."""

from __future__ import annotations

from unittest.mock import Mock, patch

from agent_runtime_cockpit.adapters.dspy.detect import (
    DSPyDetectionResult,
    detect_dspy,
    detect_dspy_import,
    scan_workspace_for_dspy,
)


class TestDSPyImportDetection:
    """Test dspy import detection."""

    @patch("importlib.util.find_spec")
    def test_detect_when_not_installed(self, mock_find_spec):
        mock_find_spec.return_value = None
        detected, version = detect_dspy_import()
        assert detected is False
        assert version is None

    @patch("importlib.util.find_spec")
    def test_detect_handles_import_error(self, mock_find_spec):
        mock_find_spec.return_value = Mock()
        detected, version = detect_dspy_import()
        assert isinstance(detected, bool)
        assert version is None or isinstance(version, str)


class TestWorkspaceScanning:
    """Test workspace scanning for DSPy usage."""

    def test_scan_empty_workspace(self, tmp_path):
        evidence, has_sigs, has_mods, has_opts = scan_workspace_for_dspy(tmp_path)
        assert evidence == []
        assert has_sigs is False
        assert has_mods is False
        assert has_opts is False

    def test_scan_detects_import_statement(self, tmp_path):
        test_file = tmp_path / "program.py"
        test_file.write_text("import dspy\n")

        evidence, has_sigs, has_mods, has_opts = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) == 1
        assert "program.py" in evidence[0]

    def test_scan_detects_from_import(self, tmp_path):
        test_file = tmp_path / "main.py"
        test_file.write_text("from dspy import Predict, ChainOfThought\n")

        evidence, _, _, _ = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) == 1
        assert "main.py" in evidence[0]

    def test_scan_detects_signatures(self, tmp_path):
        test_file = tmp_path / "sigs.py"
        test_file.write_text(
            "import dspy\n"
            "class MySig(dspy.Signature):\n"
            '    """Classify text."""\n'
            "    text: str = dspy.InputField()\n"
            "    label: str = dspy.OutputField()\n"
        )

        evidence, has_sigs, _, _ = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) >= 1
        assert has_sigs is True

    def test_scan_detects_modules(self, tmp_path):
        test_file = tmp_path / "modules.py"
        test_file.write_text("import dspy\ncot = dspy.ChainOfThought('question -> answer')\n")

        evidence, _, has_mods, _ = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) >= 1
        assert has_mods is True

    def test_scan_detects_optimizers(self, tmp_path):
        test_file = tmp_path / "optimize.py"
        test_file.write_text("import dspy\noptimizer = dspy.MIPROv2(metric=metric, auto='light')\n")

        evidence, _, _, has_opts = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) >= 1
        assert has_opts is True

    def test_scan_detects_requirements_txt(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("dspy>=2.5\n")

        evidence, _, _, _ = scan_workspace_for_dspy(tmp_path)
        assert "requirements.txt" in evidence

    def test_scan_detects_dspy_ai_legacy(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("dspy-ai>=2.4\n")

        evidence, _, _, _ = scan_workspace_for_dspy(tmp_path)
        assert "requirements.txt" in evidence

    def test_scan_detects_pyproject_toml(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\ndependencies = ["dspy>=2.5"]\n')

        evidence, _, _, _ = scan_workspace_for_dspy(tmp_path)
        assert "pyproject.toml" in evidence

    def test_scan_ignores_venv(self, tmp_path):
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "program.py"
        venv_file.write_text("import dspy\npredict = dspy.Predict('q -> a')\n")

        evidence, _, _, _ = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) == 0

    def test_scan_multiple_files(self, tmp_path):
        (tmp_path / "sig.py").write_text("import dspy\nclass S(dspy.Signature): pass\n")
        (tmp_path / "mod.py").write_text("import dspy\ncot = dspy.ChainOfThought('q -> a')\n")
        (tmp_path / "requirements.txt").write_text("dspy>=2.5\n")

        evidence, has_sigs, has_mods, _ = scan_workspace_for_dspy(tmp_path)
        assert len(evidence) == 3
        assert has_sigs is True
        assert has_mods is True


class TestFullDetection:
    """Test full detection logic."""

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_not_detected_when_not_installed(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)

        result = detect_dspy(tmp_path)

        assert result.detected is False
        assert result.confidence == 0.0
        assert result.version is None

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_detected_with_base_confidence(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")

        result = detect_dspy(tmp_path)

        assert result.detected is True
        assert result.confidence == 0.3
        assert result.version == "2.5.0"

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_detected_with_workspace_usage(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "program.py").write_text("import dspy\n")

        result = detect_dspy(tmp_path)

        assert result.detected is True
        assert result.confidence == 0.6

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_detected_with_full_signals(self, mock_import, tmp_path):
        mock_import.return_value = (True, "2.5.0")
        (tmp_path / "program.py").write_text(
            "import dspy\n"
            "class S(dspy.Signature):\n"
            "    q: str = dspy.InputField()\n"
            "    a: str = dspy.OutputField()\n"
            "cot = dspy.ChainOfThought(S)\n"
            "opt = dspy.MIPROv2(metric=m)\n"
        )

        result = detect_dspy(tmp_path)

        assert result.detected is True
        assert result.confidence == 1.0
        assert result.has_signatures is True
        assert result.has_modules is True
        assert result.has_optimizers is True

    @patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import")
    def test_detected_from_workspace_only(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        (tmp_path / "program.py").write_text("import dspy\n")

        result = detect_dspy(tmp_path)

        assert result.detected is True
        assert result.confidence == 0.2

    def test_result_is_named_tuple(self, tmp_path):
        with patch("agent_runtime_cockpit.adapters.dspy.detect.detect_dspy_import") as m:
            m.return_value = (True, "2.5.0")
            result = detect_dspy(tmp_path)

            assert isinstance(result, DSPyDetectionResult)
            assert hasattr(result, "detected")
            assert hasattr(result, "confidence")
            assert hasattr(result, "evidence")
            assert hasattr(result, "version")
            assert hasattr(result, "has_signatures")
            assert hasattr(result, "has_modules")
            assert hasattr(result, "has_optimizers")
