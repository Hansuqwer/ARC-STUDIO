"""Tests for Google ADK static workflow export."""

from __future__ import annotations

from agent_runtime_cockpit.adapters.google_adk.export import (
    GoogleADKVisitor,
    export_google_adk_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


# ── visitor ──────────────────────────────────────────────────────────────────


def test_visitor_llm_agent(tmp_path):
    import ast

    src = (
        "from google.adk.agents import LlmAgent\n"
        "root = LlmAgent(name='Root', model='gemini-flash-latest', "
        "instruction='Be helpful')\n"
    )
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "agent.py")
    visitor.visit(tree)
    assert len(visitor.agents) == 1
    agent = visitor.agents[0]
    assert agent["name"] == "Root"
    assert agent["agent_type"] == "LlmAgent"
    assert agent["model"] == "gemini-flash-latest"
    assert agent["instruction"] == "Be helpful"


def test_visitor_sequential_agent_with_sub_agents(tmp_path):
    import ast

    src = (
        "from google.adk.agents import SequentialAgent, LlmAgent\n"
        "step1 = LlmAgent(name='Step1')\n"
        "pipeline = SequentialAgent(name='Pipeline', sub_agents=[step1])\n"
    )
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "pipeline.py")
    visitor.visit(tree)
    # Both LlmAgent and SequentialAgent captured
    names = [a["name"] for a in visitor.agents]
    assert "Pipeline" in names
    pipeline = next(a for a in visitor.agents if a["name"] == "Pipeline")
    assert pipeline["agent_type"] == "SequentialAgent"
    assert "step1" in pipeline["sub_agents"]


def test_visitor_parallel_agent(tmp_path):
    import ast

    src = (
        "from google.adk.agents import ParallelAgent, LlmAgent\n"
        "a = LlmAgent(name='A')\n"
        "b = LlmAgent(name='B')\n"
        "par = ParallelAgent(name='Par', sub_agents=[a, b])\n"
    )
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "par.py")
    visitor.visit(tree)
    par = next((ag for ag in visitor.agents if ag["agent_type"] == "ParallelAgent"), None)
    assert par is not None
    assert len(par["sub_agents"]) == 2


def test_visitor_loop_agent(tmp_path):
    import ast

    src = (
        "from google.adk.agents import LoopAgent, LlmAgent\n"
        "inner = LlmAgent(name='Inner')\n"
        "looper = LoopAgent(name='Looper', sub_agents=[inner])\n"
    )
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "loop.py")
    visitor.visit(tree)
    looper = next((a for a in visitor.agents if a["agent_type"] == "LoopAgent"), None)
    assert looper is not None
    assert "inner" in looper["sub_agents"]


def test_visitor_function_tool(tmp_path):
    import ast

    src = "from google.adk.tools import FunctionTool\ncalc = FunctionTool(func=add_numbers)\n"
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "tools.py")
    visitor.visit(tree)
    assert len(visitor.tools) == 1
    assert visitor.tools[0]["name"] == "calc"


def test_visitor_tool_decorator(tmp_path):
    import ast

    src = (
        "from google.adk.tools import tool\n"
        "@tool\n"
        "def search(query: str) -> str:\n"
        "    return query\n"
    )
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "tools.py")
    visitor.visit(tree)
    assert any(t["name"] == "search" for t in visitor.tools)


def test_visitor_agent_with_tools(tmp_path):
    import ast

    src = (
        "from google.adk.agents import LlmAgent\n"
        "from google.adk.tools import FunctionTool\n"
        "calc = FunctionTool(func=add)\n"
        "agent = LlmAgent(name='Agent', tools=[calc])\n"
    )
    tree = ast.parse(src)
    visitor = GoogleADKVisitor(tmp_path / "agent.py")
    visitor.visit(tree)
    ag = next((a for a in visitor.agents if a["name"] == "Agent"), None)
    assert ag is not None
    assert "calc" in ag["tools"]


# ── export_google_adk_workflows ───────────────────────────────────────────────


def test_export_empty_workspace(tmp_path):
    workflows = export_google_adk_workflows(tmp_path)
    assert workflows == []


def test_export_no_adk_file(tmp_path):
    (tmp_path / "agent.py").write_text("import numpy as np\n")
    workflows = export_google_adk_workflows(tmp_path)
    assert workflows == []


def test_export_llm_agent(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\n"
        "root = LlmAgent(name='Root', model='gemini-flash-latest')\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf.runtime == "google_adk"
    assert wf.name == "Root"
    assert wf.id == "google_adk_Root"
    assert any(n.type == NodeType.AGENT for n in wf.nodes)


def test_export_sequential_agent_has_sub_agent_edges(tmp_path):
    (tmp_path / "pipe.py").write_text(
        "from google.adk.agents import SequentialAgent, LlmAgent\n"
        "step1 = LlmAgent(name='Step1')\n"
        "pipe = SequentialAgent(name='Pipe', sub_agents=[step1])\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    pipe = next((w for w in workflows if w.name == "Pipe"), None)
    assert pipe is not None
    assert any(e.label == "orchestrates" for e in pipe.edges)
    assert any(n.label == "step1" for n in pipe.nodes)


def test_export_agent_with_tools_has_tool_edges(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\n"
        "from google.adk.tools import FunctionTool\n"
        "calc = FunctionTool(func=add)\n"
        "agent = LlmAgent(name='MathAgent', tools=[calc])\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    wf = next((w for w in workflows if w.name == "MathAgent"), None)
    assert wf is not None
    tool_nodes = [n for n in wf.nodes if n.type == NodeType.TOOL]
    assert len(tool_nodes) == 1
    assert tool_nodes[0].label == "calc"
    assert any(e.label == "uses" for e in wf.edges)


def test_export_skips_syntax_error(tmp_path):
    (tmp_path / "bad.py").write_text(
        "from google.adk.agents import LlmAgent\nroot = LlmAgent(name=\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    assert workflows == []


def test_export_skips_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\nroot = LlmAgent(name='X')\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    assert workflows == []


def test_export_metadata_fields(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\n"
        "root = LlmAgent(name='Root', model='gemini-flash-latest', "
        "description='A helpful assistant')\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    wf = workflows[0]
    assert wf.metadata["agent_type"] == "LlmAgent"
    assert wf.metadata["model"] == "gemini-flash-latest"


def test_export_workflow_info_entry_points(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\nroot = LlmAgent(name='Root')\n"
    )
    workflows = export_google_adk_workflows(tmp_path)
    assert workflows[0].entry_points == ["agent_0"]
