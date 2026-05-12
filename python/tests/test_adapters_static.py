from agent_runtime_cockpit.adapters.crewai import CrewAIAdapter
from agent_runtime_cockpit.adapters.llamaindex import LlamaIndexAdapter
from agent_runtime_cockpit.adapters.openai_agents import OpenAIAgentsAdapter
from agent_runtime_cockpit.adapters.registry import default_registry


def test_static_adapters_are_registered_and_cannot_run():
    registry = default_registry()
    for adapter_id in ("crewai", "openai-agents", "llamaindex"):
        adapter = registry.get(adapter_id)
        assert adapter is not None
        assert adapter.capabilities().can_run is False


def test_crewai_detection_and_static_export(tmp_path):
    (tmp_path / "requirements.txt").write_text("crewai==0.1.0\n")
    adapter = CrewAIAdapter()
    detected, confidence, evidence = adapter.detect(tmp_path)
    assert detected is True
    assert confidence >= 0.7
    assert evidence
    workflows = adapter.export_workflow(tmp_path)
    assert workflows[0].runtime == "crewai"
    assert workflows[0].metadata["can_run"] is False


def test_openai_agents_detection_and_static_export(tmp_path):
    (tmp_path / "agent.py").write_text("from agents import Agent\n")
    adapter = OpenAIAgentsAdapter()
    detected, confidence, evidence = adapter.detect(tmp_path)
    assert detected is True
    assert confidence >= 0.6
    assert evidence
    assert adapter.export_workflow(tmp_path)[0].runtime == "openai-agents"


def test_llamaindex_detection_and_static_export(tmp_path):
    (tmp_path / "pyproject.toml").write_text("dependencies = ['llama-index']\n")
    adapter = LlamaIndexAdapter()
    detected, confidence, evidence = adapter.detect(tmp_path)
    assert detected is True
    assert confidence >= 0.7
    assert evidence
    assert adapter.export_workflow(tmp_path)[0].runtime == "llamaindex"
