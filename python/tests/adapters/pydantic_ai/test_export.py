"""Tests for Pydantic AI export (Phase 29 PR 29.2)."""

from __future__ import annotations


from agent_runtime_cockpit.adapters.pydantic_ai.export import (
    PydanticAIAgentVisitor,
    export_pydantic_ai_agents,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


class TestAgentVisitor:
    """Test PydanticAIAgentVisitor AST parsing."""

    def test_detects_simple_agent(self, tmp_path):
        """Should detect simple Agent instantiation."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            'from pydantic_ai import Agent\nagent = Agent("openai:gpt-4o-mini")\n'
        )

        import ast

        tree = ast.parse(agent_file.read_text(), filename=str(agent_file))
        visitor = PydanticAIAgentVisitor(agent_file)
        visitor.visit(tree)

        assert len(visitor.agents) == 1
        assert visitor.agents[0]["name"] == "agent"
        assert "openai:gpt-4o-mini" in visitor.agents[0]["model"]

    def test_detects_agent_with_tools(self, tmp_path):
        """Should detect Agent with tools list."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'agent = Agent("openai:gpt-4o-mini", tools=[tool1, tool2])\n'
        )

        import ast

        tree = ast.parse(agent_file.read_text(), filename=str(agent_file))
        visitor = PydanticAIAgentVisitor(agent_file)
        visitor.visit(tree)

        assert len(visitor.agents) == 1
        assert len(visitor.agents[0]["tools"]) == 2
        assert "tool1" in visitor.agents[0]["tools"]
        assert "tool2" in visitor.agents[0]["tools"]

    def test_detects_agent_with_system_prompt(self, tmp_path):
        """Should detect Agent with system_prompt."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'agent = Agent("openai:gpt-4o-mini", system_prompt="You are helpful")\n'
        )

        import ast

        tree = ast.parse(agent_file.read_text(), filename=str(agent_file))
        visitor = PydanticAIAgentVisitor(agent_file)
        visitor.visit(tree)

        assert len(visitor.agents) == 1
        assert visitor.agents[0]["system_prompt"] == "You are helpful"

    def test_detects_agent_with_result_type(self, tmp_path):
        """Should detect Agent with result_type."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'agent = Agent("openai:gpt-4o-mini", result_type=MyModel)\n'
        )

        import ast

        tree = ast.parse(agent_file.read_text(), filename=str(agent_file))
        visitor = PydanticAIAgentVisitor(agent_file)
        visitor.visit(tree)

        assert len(visitor.agents) == 1
        assert visitor.agents[0]["result_type"] == "MyModel"


class TestExportAgents:
    """Test export_pydantic_ai_agents function."""

    def test_export_empty_workspace(self, tmp_path):
        """Should return empty list for workspace with no agents."""
        workflows = export_pydantic_ai_agents(tmp_path)
        assert workflows == []

    def test_export_simple_agent(self, tmp_path):
        """Should export simple agent to WorkflowInfo."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'weather_agent = Agent("openai:gpt-4o-mini", system_prompt="Weather assistant")\n'
        )

        workflows = export_pydantic_ai_agents(tmp_path)

        assert len(workflows) == 1
        workflow = workflows[0]
        assert workflow.name == "weather_agent"
        assert workflow.runtime == "pydantic_ai"
        assert len(workflow.nodes) == 1  # Just the agent node
        assert workflow.nodes[0].type == NodeType.AGENT
        assert workflow.nodes[0].label == "weather_agent"

    def test_export_agent_with_tools(self, tmp_path):
        """Should export agent with tools as separate nodes."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'agent = Agent("openai:gpt-4o-mini", tools=[get_weather, get_forecast])\n'
        )

        workflows = export_pydantic_ai_agents(tmp_path)

        assert len(workflows) == 1
        workflow = workflows[0]
        assert len(workflow.nodes) == 3  # Agent + 2 tools

        # Check agent node
        agent_node = workflow.nodes[0]
        assert agent_node.type == NodeType.AGENT

        # Check tool nodes
        tool_nodes = [n for n in workflow.nodes if n.type == NodeType.TOOL]
        assert len(tool_nodes) == 2
        tool_labels = [n.label for n in tool_nodes]
        assert "get_weather" in tool_labels
        assert "get_forecast" in tool_labels

        # Check edges
        assert len(workflow.edges) == 2  # Agent -> tool1, Agent -> tool2

    def test_export_multiple_agents(self, tmp_path):
        """Should export multiple agents from same file."""
        agent_file = tmp_path / "agents.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'agent1 = Agent("openai:gpt-4o-mini")\n'
            'agent2 = Agent("anthropic:claude-3-5-sonnet-20241022")\n'
        )

        workflows = export_pydantic_ai_agents(tmp_path)

        assert len(workflows) == 2
        names = [w.name for w in workflows]
        assert "agent1" in names
        assert "agent2" in names

    def test_export_ignores_venv(self, tmp_path):
        """Should ignore agents in .venv directory."""
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "agent.py"
        venv_file.write_text('from pydantic_ai import Agent\nagent = Agent("openai:gpt-4o-mini")\n')

        workflows = export_pydantic_ai_agents(tmp_path)
        assert len(workflows) == 0

    def test_export_handles_syntax_errors(self, tmp_path):
        """Should handle files with syntax errors gracefully."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("this is not valid python syntax {{{")

        workflows = export_pydantic_ai_agents(tmp_path)
        assert workflows == []  # Should not crash

    def test_workflow_metadata(self, tmp_path):
        """Should include metadata in WorkflowInfo."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text(
            "from pydantic_ai import Agent\n"
            'agent = Agent("openai:gpt-4o-mini", tools=[tool1, tool2])\n'
        )

        workflows = export_pydantic_ai_agents(tmp_path)

        assert len(workflows) == 1
        workflow = workflows[0]
        assert "source_file" in workflow.metadata
        assert "model" in workflow.metadata
        assert "tool_count" in workflow.metadata
        assert workflow.metadata["tool_count"] == 2
