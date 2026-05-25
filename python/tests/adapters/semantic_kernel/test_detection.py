"""Tests for Semantic Kernel adapter detection."""

from __future__ import annotations

from unittest.mock import Mock, patch

from agent_runtime_cockpit.adapters.semantic_kernel.detect import (
    SemanticKernelDetectionResult,
    detect_semantic_kernel,
    detect_semantic_kernel_import,
    scan_workspace_for_semantic_kernel,
)


class TestSemanticKernelImportDetection:
    @patch("importlib.util.find_spec")
    def test_detect_when_not_installed(self, mock_find_spec):
        mock_find_spec.return_value = None
        detected, version = detect_semantic_kernel_import()
        assert detected is False
        assert version is None

    @patch("importlib.util.find_spec")
    def test_detect_handles_import_error(self, mock_find_spec):
        mock_find_spec.return_value = Mock()
        detected, version = detect_semantic_kernel_import()
        assert isinstance(detected, bool)
        assert version is None or isinstance(version, str)


class TestSemanticKernelWorkspaceScanning:
    def test_scan_empty_workspace(self, tmp_path):
        evidence, has_kernel, has_plugins, has_agents, has_processes = (
            scan_workspace_for_semantic_kernel(tmp_path)
        )
        assert evidence == []
        assert has_kernel is False
        assert has_plugins is False
        assert has_agents is False
        assert has_processes is False

    def test_scan_detects_import_and_kernel(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "from semantic_kernel import Kernel\nkernel = Kernel()\n",
            encoding="utf-8",
        )
        evidence, has_kernel, _, _, _ = scan_workspace_for_semantic_kernel(tmp_path)
        assert "app.py" in evidence
        assert has_kernel is True

    def test_scan_detects_kernel_function_plugin(self, tmp_path):
        (tmp_path / "plugins.py").write_text(
            "from semantic_kernel.functions import kernel_function\n"
            "class WeatherPlugin:\n"
            "    @kernel_function(name='weather')\n"
            "    def get_weather(self):\n"
            "        return 'sunny'\n",
            encoding="utf-8",
        )
        evidence, _, has_plugins, _, _ = scan_workspace_for_semantic_kernel(tmp_path)
        assert "plugins.py" in evidence
        assert has_plugins is True

    def test_scan_detects_agents(self, tmp_path):
        (tmp_path / "agents.py").write_text(
            "from semantic_kernel.agents import ChatCompletionAgent\n"
            "agent = ChatCompletionAgent(name='Writer')\n",
            encoding="utf-8",
        )
        evidence, _, _, has_agents, _ = scan_workspace_for_semantic_kernel(tmp_path)
        assert "agents.py" in evidence
        assert has_agents is True

    def test_scan_detects_processes(self, tmp_path):
        (tmp_path / "process.py").write_text(
            "from semantic_kernel.processes import ProcessBuilder\n"
            "builder = ProcessBuilder(name='flow')\n",
            encoding="utf-8",
        )
        evidence, _, _, _, has_processes = scan_workspace_for_semantic_kernel(tmp_path)
        assert "process.py" in evidence
        assert has_processes is True

    def test_scan_detects_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("semantic-kernel>=1.0\n", encoding="utf-8")
        evidence, *_ = scan_workspace_for_semantic_kernel(tmp_path)
        assert "requirements.txt" in evidence

    def test_scan_ignores_venv(self, tmp_path):
        venv_file = tmp_path / ".venv" / "lib" / "app.py"
        venv_file.parent.mkdir(parents=True)
        venv_file.write_text("from semantic_kernel import Kernel\n", encoding="utf-8")
        evidence, *_ = scan_workspace_for_semantic_kernel(tmp_path)
        assert evidence == []


class TestSemanticKernelFullDetection:
    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_not_detected(self, mock_import, tmp_path):
        mock_import.return_value = (False, None)
        result = detect_semantic_kernel(tmp_path)
        assert result.detected is False
        assert result.confidence == 0.0

    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_detected_from_install(self, mock_import, tmp_path):
        mock_import.return_value = (True, "1.35.0")
        result = detect_semantic_kernel(tmp_path)
        assert result.detected is True
        assert result.confidence == 0.3
        assert result.version == "1.35.0"

    @patch("agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import")
    def test_detected_with_full_signals(self, mock_import, tmp_path):
        mock_import.return_value = (True, "1.35.0")
        (tmp_path / "app.py").write_text(
            "from semantic_kernel import Kernel\n"
            "from semantic_kernel.functions import kernel_function\n"
            "from semantic_kernel.agents import ChatCompletionAgent\n"
            "kernel = Kernel()\n"
            "class P:\n"
            "    @kernel_function(name='f')\n"
            "    def f(self): return 'x'\n"
            "agent = ChatCompletionAgent(name='A')\n",
            encoding="utf-8",
        )
        result = detect_semantic_kernel(tmp_path)
        assert result.detected is True
        assert result.confidence == 0.95
        assert result.has_kernel is True
        assert result.has_plugins is True
        assert result.has_agents is True

    def test_result_is_named_tuple(self, tmp_path):
        with patch(
            "agent_runtime_cockpit.adapters.semantic_kernel.detect.detect_semantic_kernel_import"
        ) as mock_import:
            mock_import.return_value = (False, None)
            result = detect_semantic_kernel(tmp_path)
        assert isinstance(result, SemanticKernelDetectionResult)
        assert hasattr(result, "has_processes")
