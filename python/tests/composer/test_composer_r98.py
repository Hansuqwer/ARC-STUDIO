"""Tests for ARC Composer — visual SwarmGraph builder (R98, Phase 323)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.composer import (
    CodeGenResult,
    generate_swarmgraph_code,
    validate_composer_graph,
)
from agent_runtime_cockpit.swarmgraph_ir.models import (
    IRAdapterProvenance,
    IREdge,
    IRGraph,
    IRNode,
    IRNodeKind,
)


@pytest.fixture
def simple_graph() -> IRGraph:
    return IRGraph(
        id="test-workflow",
        runtime="swarmgraph",
        provenance=IRAdapterProvenance(adapter_id="test", runtime="swarmgraph"),
        nodes=[
            IRNode(id="start", label="Start", kind=IRNodeKind.START),
            IRNode(id="agent1", label="Agent 1", kind=IRNodeKind.AGENT),
            IRNode(id="tool1", label="Tool 1", kind=IRNodeKind.TOOL),
            IRNode(id="end", label="End", kind=IRNodeKind.END),
        ],
        edges=[
            IREdge(id="e1", from_node="start", to_node="agent1"),
            IREdge(id="e2", from_node="agent1", to_node="tool1"),
            IREdge(id="e3", from_node="tool1", to_node="end"),
        ],
    )


@pytest.fixture
def cyclic_graph() -> IRGraph:
    return IRGraph(
        id="cyclic-workflow",
        runtime="swarmgraph",
        provenance=IRAdapterProvenance(adapter_id="test", runtime="swarmgraph"),
        nodes=[
            IRNode(id="a", label="A", kind=IRNodeKind.AGENT),
            IRNode(id="b", label="B", kind=IRNodeKind.AGENT),
            IRNode(id="c", label="C", kind=IRNodeKind.AGENT),
        ],
        edges=[
            IREdge(id="e1", from_node="a", to_node="b"),
            IREdge(id="e2", from_node="b", to_node="c"),
            IREdge(id="e3", from_node="c", to_node="a"),
        ],
    )


class TestCodeGenResult:
    def test_ok_result(self) -> None:
        result = CodeGenResult(
            code="print('hello')",
            graph_id="test",
            node_count=2,
            edge_count=1,
        )
        assert result.ok is True
        assert result.errors == []

    def test_error_result(self) -> None:
        result = CodeGenResult(
            code="",
            graph_id="test",
            node_count=0,
            edge_count=0,
            errors=["duplicate node id"],
        )
        assert result.ok is False

    def test_to_dict(self) -> None:
        result = CodeGenResult(
            code="code",
            graph_id="test",
            node_count=3,
            edge_count=2,
            warnings=["warning1"],
        )
        d = result.to_dict()
        assert d["ok"] is True
        assert d["graph_id"] == "test"
        assert d["node_count"] == 3
        assert len(d["warnings"]) == 1


class TestGenerateSwarmGraphCode:
    def test_generate_simple_graph(self, simple_graph: IRGraph) -> None:
        result = generate_swarmgraph_code(simple_graph)
        assert result.ok is True
        assert "def build_test_workflow" in result.code
        assert "StartNode" in result.code
        assert "AgentNode" in result.code
        assert "ToolNode" in result.code
        assert "EndNode" in result.code
        assert 'graph.add_edge("start", "agent1"' in result.code

    def test_generate_includes_header(self, simple_graph: IRGraph) -> None:
        result = generate_swarmgraph_code(simple_graph)
        assert "Auto-generated SwarmGraph workflow" in result.code
        assert "Graph ID: test-workflow" in result.code
        assert "Runtime: swarmgraph" in result.code

    def test_generate_includes_imports(self, simple_graph: IRGraph) -> None:
        result = generate_swarmgraph_code(simple_graph)
        assert "from swarmgraph import SwarmGraph" in result.code
        assert "from swarmgraph.nodes import" in result.code

    def test_generate_cyclic_graph_warns(self, cyclic_graph: IRGraph) -> None:
        result = generate_swarmgraph_code(cyclic_graph)
        assert result.ok is True
        assert any("cycle" in w.lower() for w in result.warnings)

    def test_generate_empty_graph_fails(self) -> None:
        graph = IRGraph(
            id="",
            runtime="",
            provenance=IRAdapterProvenance(adapter_id="test", runtime=""),
            nodes=[],
            edges=[],
        )
        result = generate_swarmgraph_code(graph)
        assert result.ok is False
        assert len(result.errors) > 0

    def test_generate_duplicate_node_ids_fails(self) -> None:
        graph = IRGraph(
            id="dup-test",
            runtime="swarmgraph",
            provenance=IRAdapterProvenance(adapter_id="test", runtime="swarmgraph"),
            nodes=[
                IRNode(id="a", label="A", kind=IRNodeKind.AGENT),
                IRNode(id="a", label="A2", kind=IRNodeKind.AGENT),
            ],
            edges=[],
        )
        result = generate_swarmgraph_code(graph)
        assert result.ok is False
        assert any("duplicate" in e.lower() for e in result.errors)


class TestValidateComposerGraph:
    def test_validate_simple_graph(self, simple_graph: IRGraph) -> None:
        result = validate_composer_graph(simple_graph)
        assert result["ok"] is True
        assert result["graph_id"] == "test-workflow"
        assert result["node_count"] == 4
        assert result["edge_count"] == 3

    def test_validate_cyclic_graph(self, cyclic_graph: IRGraph) -> None:
        result = validate_composer_graph(cyclic_graph)
        assert result["ok"] is True
        assert result["has_cycles"] is True

    def test_validate_empty_graph(self) -> None:
        graph = IRGraph(
            id="",
            runtime="",
            provenance=IRAdapterProvenance(adapter_id="test", runtime=""),
            nodes=[],
            edges=[],
        )
        result = validate_composer_graph(graph)
        assert result["ok"] is False
        assert len(result["errors"]) > 0

    def test_validate_graph_with_isolated_node(self) -> None:
        graph = IRGraph(
            id="isolated-test",
            runtime="swarmgraph",
            provenance=IRAdapterProvenance(adapter_id="test", runtime="swarmgraph"),
            nodes=[
                IRNode(id="start", label="Start", kind=IRNodeKind.START),
                IRNode(id="isolated", label="Isolated", kind=IRNodeKind.AGENT),
                IRNode(id="end", label="End", kind=IRNodeKind.END),
            ],
            edges=[
                IREdge(id="e1", from_node="start", to_node="end"),
            ],
        )
        result = validate_composer_graph(graph)
        assert result["ok"] is True
        assert result["has_dead_nodes"] is True


class TestComposerCLI:
    def test_composer_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["composer", "--help"])
        assert result.exit_code == 0
        assert "composer" in result.output.lower()

    def test_composer_generate(self, tmp_path: Path, simple_graph: IRGraph) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        graph_file = tmp_path / "graph.json"
        graph_file.write_text(simple_graph.model_dump_json(), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            app, ["composer", "generate", str(graph_file), "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "code" in data["data"]

    def test_composer_generate_to_file(self, tmp_path: Path, simple_graph: IRGraph) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        graph_file = tmp_path / "graph.json"
        graph_file.write_text(simple_graph.model_dump_json(), encoding="utf-8")
        output_file = tmp_path / "output.py"

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "composer",
                "generate",
                str(graph_file),
                "--output",
                str(output_file),
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "def build_test_workflow" in content

    def test_composer_validate(self, tmp_path: Path, simple_graph: IRGraph) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        graph_file = tmp_path / "graph.json"
        graph_file.write_text(simple_graph.model_dump_json(), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            app, ["composer", "validate", str(graph_file), "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_composer_generate_missing_file(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "composer",
                "generate",
                str(tmp_path / "nonexistent.json"),
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
