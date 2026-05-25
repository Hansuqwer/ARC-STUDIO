"""Tests for Haystack export (Phase 31 T2)."""

from __future__ import annotations

from agent_runtime_cockpit.adapters.haystack.export import (
    HaystackComponentVisitor,
    HaystackPipelineVisitor,
    export_haystack_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


class TestComponentVisitor:
    """Test HaystackComponentVisitor AST parsing."""

    def test_detects_component_class(self, tmp_path):
        comp_file = tmp_path / "comp.py"
        comp_file.write_text(
            "from haystack import component\n"
            "@component\n"
            "class MyComponent:\n"
            "    def run(self, text: str):\n"
            "        return {'result': text}\n"
        )

        import ast

        tree = ast.parse(comp_file.read_text(), filename=str(comp_file))
        visitor = HaystackComponentVisitor(comp_file)
        visitor.visit(tree)

        assert len(visitor.components) == 1
        assert visitor.components[0]["name"] == "MyComponent"
        assert visitor.components[0]["has_run_method"] is True

    def test_detects_output_types(self, tmp_path):
        comp_file = tmp_path / "comp.py"
        comp_file.write_text(
            "from haystack import component\n"
            "@component\n"
            "class MyComponent:\n"
            "    @component.output_types(result=str, count=int)\n"
            "    def run(self, text: str):\n"
            "        return {'result': text, 'count': 1}\n"
        )

        import ast

        tree = ast.parse(comp_file.read_text(), filename=str(comp_file))
        visitor = HaystackComponentVisitor(comp_file)
        visitor.visit(tree)

        comp = visitor.components[0]
        assert "result" in comp["output_types"]
        assert "count" in comp["output_types"]

    def test_detects_run_inputs(self, tmp_path):
        comp_file = tmp_path / "comp.py"
        comp_file.write_text(
            "from haystack import component\n"
            "@component\n"
            "class MyComponent:\n"
            "    def run(self, query: str, documents: list):\n"
            "        pass\n"
        )

        import ast

        tree = ast.parse(comp_file.read_text(), filename=str(comp_file))
        visitor = HaystackComponentVisitor(comp_file)
        visitor.visit(tree)

        comp = visitor.components[0]
        assert "query" in comp["run_inputs"]
        assert "documents" in comp["run_inputs"]

    def test_ignores_non_component_classes(self, tmp_path):
        comp_file = tmp_path / "other.py"
        comp_file.write_text("class NotAComponent:\n    pass\n")

        import ast

        tree = ast.parse(comp_file.read_text(), filename=str(comp_file))
        visitor = HaystackComponentVisitor(comp_file)
        visitor.visit(tree)

        assert len(visitor.components) == 0


class TestPipelineVisitor:
    """Test HaystackPipelineVisitor AST parsing."""

    def test_detects_pipeline_creation(self, tmp_path):
        pipe_file = tmp_path / "pipe.py"
        pipe_file.write_text("from haystack import Pipeline\npipe = Pipeline()\n")

        import ast

        tree = ast.parse(pipe_file.read_text(), filename=str(pipe_file))
        visitor = HaystackPipelineVisitor(pipe_file)
        visitor.visit(tree)

        assert len(visitor.pipelines) == 1
        assert visitor.pipelines[0]["var_name"] == "pipe"

    def test_detects_add_component(self, tmp_path):
        pipe_file = tmp_path / "pipe.py"
        pipe_file.write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("retriever", BM25Retriever())\n'
            'pipe.add_component("generator", OpenAIGenerator())\n'
        )

        import ast

        tree = ast.parse(pipe_file.read_text(), filename=str(pipe_file))
        visitor = HaystackPipelineVisitor(pipe_file)
        visitor.visit(tree)

        assert len(visitor.pipelines) == 1
        assert len(visitor.pipelines[0]["components"]) == 2
        assert visitor.pipelines[0]["components"][0]["name"] == "retriever"
        assert visitor.pipelines[0]["components"][0]["component_type"] == "BM25Retriever"

    def test_detects_connect(self, tmp_path):
        pipe_file = tmp_path / "pipe.py"
        pipe_file.write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("retriever", BM25Retriever())\n'
            'pipe.add_component("generator", OpenAIGenerator())\n'
            'pipe.connect("retriever.documents", "generator.prompt")\n'
        )

        import ast

        tree = ast.parse(pipe_file.read_text(), filename=str(pipe_file))
        visitor = HaystackPipelineVisitor(pipe_file)
        visitor.visit(tree)

        assert len(visitor.pipelines[0]["connections"]) == 1
        conn = visitor.pipelines[0]["connections"][0]
        assert conn["source"] == "retriever.documents"
        assert conn["target"] == "generator.prompt"


class TestExportWorkflows:
    """Test export_haystack_workflows function."""

    def test_export_empty_workspace(self, tmp_path):
        workflows = export_haystack_workflows(tmp_path)
        assert workflows == []

    def test_export_component(self, tmp_path):
        comp_file = tmp_path / "comp.py"
        comp_file.write_text(
            "from haystack import component\n"
            "@component\n"
            "class TextCleaner:\n"
            "    @component.output_types(cleaned=str)\n"
            "    def run(self, text: str):\n"
            "        return {'cleaned': text.strip()}\n"
        )

        workflows = export_haystack_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert wf.name == "TextCleaner"
        assert wf.runtime == "haystack"
        assert wf.metadata["kind"] == "component"

    def test_export_component_has_input_output_nodes(self, tmp_path):
        comp_file = tmp_path / "comp.py"
        comp_file.write_text(
            "from haystack import component\n"
            "@component\n"
            "class QA:\n"
            "    @component.output_types(answer=str)\n"
            "    def run(self, question: str):\n"
            "        pass\n"
        )

        workflows = export_haystack_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        input_nodes = [n for n in wf.nodes if n.type == NodeType.START]
        output_nodes = [n for n in wf.nodes if n.type == NodeType.END]
        assert len(input_nodes) == 1
        assert len(output_nodes) == 1
        assert input_nodes[0].label == "question"
        assert output_nodes[0].label == "answer"

    def test_export_pipeline(self, tmp_path):
        pipe_file = tmp_path / "rag.py"
        pipe_file.write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("retriever", BM25Retriever())\n'
            'pipe.add_component("generator", OpenAIGenerator())\n'
            'pipe.connect("retriever.documents", "generator.prompt")\n'
        )

        workflows = export_haystack_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert wf.runtime == "haystack"
        assert wf.metadata["kind"] == "pipeline"
        assert wf.metadata["component_count"] == 2
        assert wf.metadata["connection_count"] == 1

    def test_export_pipeline_dag_edges(self, tmp_path):
        pipe_file = tmp_path / "dag.py"
        pipe_file.write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("a", ComponentA())\n'
            'pipe.add_component("b", ComponentB())\n'
            'pipe.add_component("c", ComponentC())\n'
            'pipe.connect("a.output", "b.input")\n'
            'pipe.connect("b.output", "c.input")\n'
        )

        workflows = export_haystack_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert len(wf.nodes) == 3
        assert len(wf.edges) == 2

    def test_export_ignores_venv(self, tmp_path):
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "pipe.py"
        venv_file.write_text("from haystack import Pipeline\npipe = Pipeline()\n")

        workflows = export_haystack_workflows(tmp_path)
        assert len(workflows) == 0

    def test_export_handles_syntax_errors(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from haystack import Pipeline\nthis is not valid {{{")

        workflows = export_haystack_workflows(tmp_path)
        assert workflows == []

    def test_export_ignores_non_haystack_files(self, tmp_path):
        (tmp_path / "regular.py").write_text("class MyClass:\n    pass\n")

        workflows = export_haystack_workflows(tmp_path)
        assert workflows == []

    def test_workflow_metadata(self, tmp_path):
        pipe_file = tmp_path / "pipe.py"
        pipe_file.write_text(
            "from haystack import Pipeline\n"
            "pipe = Pipeline()\n"
            'pipe.add_component("retriever", BM25Retriever())\n'
        )

        workflows = export_haystack_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert "source_file" in wf.metadata
        assert "kind" in wf.metadata
        assert wf.metadata["kind"] == "pipeline"
