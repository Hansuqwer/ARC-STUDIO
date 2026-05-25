"""Tests for Semantic Kernel static export."""

from __future__ import annotations

import ast

from agent_runtime_cockpit.adapters.semantic_kernel.export import (
    SemanticKernelVisitor,
    export_semantic_kernel_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


class TestSemanticKernelVisitor:
    def test_detects_kernel_and_plugin_functions(self, tmp_path):
        source = tmp_path / "app.py"
        source.write_text(
            "from semantic_kernel import Kernel\n"
            "from semantic_kernel.functions import kernel_function\n"
            "kernel = Kernel()\n"
            "class WeatherPlugin:\n"
            "    @kernel_function(name='weather', description='Get weather')\n"
            "    def get_weather(self):\n"
            "        return 'sunny'\n",
            encoding="utf-8",
        )
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        visitor = SemanticKernelVisitor(source)
        visitor.visit(tree)
        assert visitor.kernel_vars[0]["name"] == "kernel"
        assert visitor.plugins[0]["name"] == "WeatherPlugin"
        assert visitor.functions[0]["name"] == "weather"

    def test_detects_agents_and_invocations(self, tmp_path):
        source = tmp_path / "agents.py"
        source.write_text(
            "from semantic_kernel import Kernel\n"
            "from semantic_kernel.agents import ChatCompletionAgent\n"
            "kernel = Kernel()\n"
            "writer = ChatCompletionAgent(name='Writer', instructions='Write')\n"
            "result = kernel.invoke_prompt(function_name='draft', plugin_name='demo')\n",
            encoding="utf-8",
        )
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        visitor = SemanticKernelVisitor(source)
        visitor.visit(tree)
        assert visitor.agents[0]["name"] == "Writer"
        assert visitor.agents[0]["agent_type"] == "ChatCompletionAgent"
        assert visitor.invocations[0]["method"] == "invoke_prompt"


class TestSemanticKernelExport:
    def test_export_empty_workspace(self, tmp_path):
        assert export_semantic_kernel_workflows(tmp_path) == []

    def test_export_plugin_workflow(self, tmp_path):
        (tmp_path / "plugin.py").write_text(
            "from semantic_kernel import Kernel\n"
            "from semantic_kernel.functions import kernel_function\n"
            "kernel = Kernel()\n"
            "class WeatherPlugin:\n"
            "    @kernel_function(name='weather')\n"
            "    def get_weather(self):\n"
            "        return 'sunny'\n"
            "kernel.add_plugin(WeatherPlugin(), plugin_name='weather')\n",
            encoding="utf-8",
        )
        workflows = export_semantic_kernel_workflows(tmp_path)
        assert len(workflows) == 1
        workflow = workflows[0]
        assert workflow.runtime == "semantic_kernel"
        assert workflow.metadata["plugin_count"] >= 1
        assert any(node.type == NodeType.TOOL for node in workflow.nodes)
        assert any(edge.label in {"adds_plugin", "exposes"} for edge in workflow.edges)

    def test_export_agent_workflow(self, tmp_path):
        (tmp_path / "agents.py").write_text(
            "from semantic_kernel import Kernel\n"
            "from semantic_kernel.agents import ChatCompletionAgent\n"
            "kernel = Kernel()\n"
            "writer = ChatCompletionAgent(name='Writer', instructions='Write')\n",
            encoding="utf-8",
        )
        workflows = export_semantic_kernel_workflows(tmp_path)
        assert len(workflows) == 1
        assert workflows[0].metadata["agent_count"] == 1
        assert any(
            node.label == "Writer" and node.type == NodeType.AGENT for node in workflows[0].nodes
        )

    def test_export_ignores_syntax_errors(self, tmp_path):
        (tmp_path / "bad.py").write_text(
            "from semantic_kernel import Kernel\nif ", encoding="utf-8"
        )
        assert export_semantic_kernel_workflows(tmp_path) == []
