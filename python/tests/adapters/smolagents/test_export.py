"""Tests for Smolagents export."""

from __future__ import annotations

import ast

from agent_runtime_cockpit.adapters.smolagents.export import (
    SmolagentsVisitor,
    export_smolagents_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


def test_visitor_detects_code_agent(tmp_path):
    path = tmp_path / "agent.py"
    path.write_text(
        "from smolagents import CodeAgent, InferenceClientModel\n"
        "model = InferenceClientModel()\n"
        "agent = CodeAgent(tools=[], model=model)\n"
    )
    visitor = SmolagentsVisitor(path)
    visitor.visit(ast.parse(path.read_text()))
    assert len(visitor.agents) == 1
    assert visitor.agents[0]["agent_type"] == "CodeAgent"
    assert visitor.agents[0]["code_execution"] is True


def test_visitor_detects_tool_and_toolcalling_agent(tmp_path):
    path = tmp_path / "agent.py"
    path.write_text(
        "from smolagents import ToolCallingAgent, tool\n"
        "@tool\n"
        "def search(query: str): return query\n"
        "agent = ToolCallingAgent(tools=[search], model=model)\n"
    )
    visitor = SmolagentsVisitor(path)
    visitor.visit(ast.parse(path.read_text()))
    assert visitor.tools[0]["name"] == "search"
    assert visitor.agents[0]["tools"] == ["search"]


def test_export_empty_workspace(tmp_path):
    assert export_smolagents_workflows(tmp_path) == []


def test_export_agent_with_tool(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from smolagents import CodeAgent, InferenceClientModel, tool\n"
        "@tool\n"
        "def search(query: str): return query\n"
        "model = InferenceClientModel()\n"
        "agent = CodeAgent(tools=[search], model=model)\n"
    )
    workflows = export_smolagents_workflows(tmp_path)
    assert len(workflows) == 1
    workflow = workflows[0]
    assert workflow.runtime == "smolagents"
    assert workflow.metadata["agent_type"] == "CodeAgent"
    assert workflow.metadata["code_execution"] is True
    assert len([n for n in workflow.nodes if n.type == NodeType.TOOL]) == 1
    assert len(workflow.edges) == 1


def test_export_tool_calling_agent_no_code_execution(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from smolagents import ToolCallingAgent\nagent = ToolCallingAgent(tools=[], model=model)\n"
    )
    workflow = export_smolagents_workflows(tmp_path)[0]
    assert workflow.metadata["code_execution"] is False


def test_export_ignores_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "agent.py").write_text("from smolagents import CodeAgent\nagent=CodeAgent()\n")
    assert export_smolagents_workflows(tmp_path) == []


def test_export_handles_syntax_errors(tmp_path):
    (tmp_path / "bad.py").write_text("from smolagents import CodeAgent\n{{{")
    assert export_smolagents_workflows(tmp_path) == []
