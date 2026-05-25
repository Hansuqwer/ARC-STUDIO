"""Tests for Google ADK detection logic."""

from __future__ import annotations

from unittest.mock import Mock, patch

from agent_runtime_cockpit.adapters.google_adk.detect import (
    GoogleADKDetectionResult,
    detect_google_adk,
    detect_google_adk_import,
    scan_workspace_for_google_adk,
)


# ── import probe ─────────────────────────────────────────────────────────────


def test_detect_import_not_installed():
    with patch("importlib.util.find_spec", return_value=None):
        detected, version = detect_google_adk_import()
    assert detected is False
    assert version is None


def test_detect_import_handles_import_error():
    with patch("importlib.util.find_spec", return_value=Mock()):
        # google.adk not installed in test env; should return (False, None) or (True, ...)
        detected, version = detect_google_adk_import()
    assert isinstance(detected, bool)
    assert version is None or isinstance(version, str)


# ── workspace scanner ────────────────────────────────────────────────────────


def test_scan_empty_workspace(tmp_path):
    ev, llm, seq, par, loop, tools, runner = scan_workspace_for_google_adk(tmp_path)
    assert ev == []
    assert llm is False
    assert seq is False
    assert par is False
    assert loop is False
    assert tools is False
    assert runner is False


def test_scan_detects_llm_agent(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\n"
        "root_agent = LlmAgent(name='MyAgent', model='gemini-flash-latest')\n"
    )
    ev, llm, *_ = scan_workspace_for_google_adk(tmp_path)
    assert "agent.py" in ev
    assert llm is True


def test_scan_detects_sequential_agent(tmp_path):
    (tmp_path / "pipeline.py").write_text(
        "from google.adk.agents import SequentialAgent, LlmAgent\n"
        "step1 = LlmAgent(name='Step1')\n"
        "pipeline = SequentialAgent(name='Pipeline', sub_agents=[step1])\n"
    )
    ev, _, seq, *_ = scan_workspace_for_google_adk(tmp_path)
    assert ev
    assert seq is True


def test_scan_detects_parallel_agent(tmp_path):
    (tmp_path / "par.py").write_text(
        "from google.adk.agents import ParallelAgent\n"
        "gather = ParallelAgent(name='Gather', sub_agents=[])\n"
    )
    ev, _, _, par, *_ = scan_workspace_for_google_adk(tmp_path)
    assert par is True


def test_scan_detects_loop_agent(tmp_path):
    (tmp_path / "loop.py").write_text(
        "from google.adk.agents import LoopAgent\n"
        "looper = LoopAgent(name='Looper', sub_agents=[])\n"
    )
    ev, _, _, _, loop, *_ = scan_workspace_for_google_adk(tmp_path)
    assert loop is True


def test_scan_detects_function_tool(tmp_path):
    (tmp_path / "tools.py").write_text(
        "from google.adk.tools import FunctionTool\ncalc = FunctionTool(func=add)\n"
    )
    ev, _, _, _, _, tools, _ = scan_workspace_for_google_adk(tmp_path)
    assert tools is True


def test_scan_detects_runner(tmp_path):
    (tmp_path / "run.py").write_text(
        "from google.adk.runners import Runner\n"
        "runner = Runner(agent=root_agent, app_name='demo')\n"
    )
    ev, *_, runner_flag = scan_workspace_for_google_adk(tmp_path)
    assert runner_flag is True


def test_scan_detects_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("google-adk>=0.4.0\n")
    ev, *_ = scan_workspace_for_google_adk(tmp_path)
    assert "requirements.txt" in ev


def test_scan_detects_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies=["google-adk"]\n')
    ev, *_ = scan_workspace_for_google_adk(tmp_path)
    assert "pyproject.toml" in ev


def test_scan_ignores_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "agent.py").write_text("from google.adk.agents import LlmAgent\n")
    ev, *_ = scan_workspace_for_google_adk(tmp_path)
    assert ev == []


def test_scan_ignores_node_modules(tmp_path):
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "agent.py").write_text("from google.adk.agents import LlmAgent\n")
    ev, *_ = scan_workspace_for_google_adk(tmp_path)
    assert ev == []


# ── full detect() ────────────────────────────────────────────────────────────


def test_full_detection_not_detected(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(False, None),
    ):
        result = detect_google_adk(tmp_path)
    assert result.detected is False
    assert result.confidence == 0.0
    assert result.evidence == []


def test_full_detection_workspace_only(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\n"
        "root = LlmAgent(name='Root', model='gemini-flash-latest')\n"
    )
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(False, None),
    ):
        result = detect_google_adk(tmp_path)
    assert result.detected is True
    assert result.confidence > 0.0
    assert result.has_llm_agent is True


def test_full_detection_installed_only(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(True, "0.4.0"),
    ):
        result = detect_google_adk(tmp_path)
    assert result.detected is True
    assert result.version == "0.4.0"
    assert result.confidence >= 0.3


def test_result_is_named_tuple(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(True, "0.4.0"),
    ):
        result = detect_google_adk(tmp_path)
    assert isinstance(result, GoogleADKDetectionResult)


def test_confidence_caps_at_1(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent\n"
        "from google.adk.tools import FunctionTool\n"
        "from google.adk.runners import Runner\n"
        "a = LlmAgent(name='A')\n"
        "b = SequentialAgent(name='B', sub_agents=[a])\n"
        "c = ParallelAgent(name='C', sub_agents=[a])\n"
        "d = LoopAgent(name='D', sub_agents=[a])\n"
        "t = FunctionTool(func=f)\n"
        "r = Runner(agent=a)\n"
    )
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(True, "0.4.0"),
    ):
        result = detect_google_adk(tmp_path)
    assert result.confidence <= 1.0
