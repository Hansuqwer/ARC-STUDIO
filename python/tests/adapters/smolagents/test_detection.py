"""Tests for Smolagents detection."""

from __future__ import annotations

from unittest.mock import Mock, patch

from agent_runtime_cockpit.adapters.smolagents.detect import (
    SmolagentsDetectionResult,
    detect_smolagents,
    detect_smolagents_import,
    scan_workspace_for_smolagents,
)


def test_detect_import_not_installed():
    with patch("importlib.util.find_spec", return_value=None):
        assert detect_smolagents_import() == (False, None)


def test_detect_import_handles_error():
    with patch("importlib.util.find_spec", return_value=Mock()):
        detected, version = detect_smolagents_import()
    assert isinstance(detected, bool)
    assert version is None or isinstance(version, str)


def test_scan_empty_workspace(tmp_path):
    evidence, has_agents, has_tools, has_models, has_code = scan_workspace_for_smolagents(tmp_path)
    assert evidence == []
    assert has_agents is False
    assert has_tools is False
    assert has_models is False
    assert has_code is False


def test_scan_detects_code_agent(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from smolagents import CodeAgent, InferenceClientModel\n"
        "model = InferenceClientModel()\n"
        "agent = CodeAgent(tools=[], model=model)\n"
    )
    evidence, has_agents, _, has_models, has_code = scan_workspace_for_smolagents(tmp_path)
    assert evidence == ["agent.py"]
    assert has_agents is True
    assert has_models is True
    assert has_code is True


def test_scan_detects_tool_calling_agent_and_tool(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from smolagents import ToolCallingAgent, LiteLLMModel, tool\n"
        "@tool\n"
        "def search(query: str): return query\n"
        "model = LiteLLMModel(model_id='gpt-4')\n"
        "agent = ToolCallingAgent(tools=[search], model=model)\n"
    )
    evidence, has_agents, has_tools, has_models, _ = scan_workspace_for_smolagents(tmp_path)
    assert evidence == ["agent.py"]
    assert has_agents is True
    assert has_tools is True
    assert has_models is True


def test_scan_detects_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("smolagents[toolkit]>=1.0\n")
    evidence, *_ = scan_workspace_for_smolagents(tmp_path)
    assert evidence == ["requirements.txt"]


def test_scan_detects_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies=["smolagents"]\n')
    evidence, *_ = scan_workspace_for_smolagents(tmp_path)
    assert evidence == ["pyproject.toml"]


def test_scan_ignores_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "agent.py").write_text("from smolagents import CodeAgent\n")
    evidence, *_ = scan_workspace_for_smolagents(tmp_path)
    assert evidence == []


def test_full_detection_not_detected(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.smolagents.detect.detect_smolagents_import",
        return_value=(False, None),
    ):
        result = detect_smolagents(tmp_path)
    assert result.detected is False
    assert result.confidence == 0.0


def test_full_detection_workspace_only(tmp_path):
    (tmp_path / "agent.py").write_text("from smolagents import CodeAgent\n")
    with patch(
        "agent_runtime_cockpit.adapters.smolagents.detect.detect_smolagents_import",
        return_value=(False, None),
    ):
        result = detect_smolagents(tmp_path)
    assert result.detected is True
    assert result.confidence > 0.0
    assert result.has_agents is True


def test_result_named_tuple(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.smolagents.detect.detect_smolagents_import",
        return_value=(True, "1.0"),
    ):
        result = detect_smolagents(tmp_path)
    assert isinstance(result, SmolagentsDetectionResult)
    assert result.version == "1.0"
