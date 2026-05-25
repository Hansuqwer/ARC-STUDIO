"""Tests for DSPy export (Phase 30 T2)."""

from __future__ import annotations

from agent_runtime_cockpit.adapters.dspy.export import (
    DSPyModuleVisitor,
    DSPySignatureVisitor,
    export_dspy_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


class TestSignatureVisitor:
    """Test DSPySignatureVisitor AST parsing."""

    def test_detects_simple_signature(self, tmp_path):
        sig_file = tmp_path / "sig.py"
        sig_file.write_text(
            "import dspy\n"
            "class Classify(dspy.Signature):\n"
            '    """Classify sentiment."""\n'
            "    sentence: str = dspy.InputField()\n"
            "    sentiment: str = dspy.OutputField()\n"
        )

        import ast

        tree = ast.parse(sig_file.read_text(), filename=str(sig_file))
        visitor = DSPySignatureVisitor(sig_file)
        visitor.visit(tree)

        assert len(visitor.signatures) == 1
        assert visitor.signatures[0]["name"] == "Classify"
        assert visitor.signatures[0]["docstring"] == "Classify sentiment."

    def test_detects_input_output_fields(self, tmp_path):
        sig_file = tmp_path / "sig.py"
        sig_file.write_text(
            "import dspy\n"
            "class QA(dspy.Signature):\n"
            "    question: str = dspy.InputField()\n"
            "    context: str = dspy.InputField()\n"
            "    answer: str = dspy.OutputField()\n"
        )

        import ast

        tree = ast.parse(sig_file.read_text(), filename=str(sig_file))
        visitor = DSPySignatureVisitor(sig_file)
        visitor.visit(tree)

        sig = visitor.signatures[0]
        assert len(sig["input_fields"]) == 2
        assert len(sig["output_fields"]) == 1
        input_names = [f["name"] for f in sig["input_fields"]]
        assert "question" in input_names
        assert "context" in input_names
        assert sig["output_fields"][0]["name"] == "answer"

    def test_ignores_non_signature_classes(self, tmp_path):
        sig_file = tmp_path / "other.py"
        sig_file.write_text("class NotASignature:\n    pass\n")

        import ast

        tree = ast.parse(sig_file.read_text(), filename=str(sig_file))
        visitor = DSPySignatureVisitor(sig_file)
        visitor.visit(tree)

        assert len(visitor.signatures) == 0


class TestModuleVisitor:
    """Test DSPyModuleVisitor AST parsing."""

    def test_detects_module_class(self, tmp_path):
        mod_file = tmp_path / "mod.py"
        mod_file.write_text(
            "import dspy\n"
            "class RAG(dspy.Module):\n"
            "    def __init__(self):\n"
            "        self.retrieve = dspy.ChainOfThought('query -> passages')\n"
            "        self.respond = dspy.ChainOfThought('context, question -> response')\n"
            "    def forward(self, question):\n"
            "        pass\n"
        )

        import ast

        tree = ast.parse(mod_file.read_text(), filename=str(mod_file))
        visitor = DSPyModuleVisitor(mod_file)
        visitor.visit(tree)

        assert len(visitor.modules) == 1
        assert visitor.modules[0]["name"] == "RAG"
        assert len(visitor.modules[0]["sub_modules"]) == 2

    def test_detects_standalone_instantiations(self, tmp_path):
        mod_file = tmp_path / "prog.py"
        mod_file.write_text(
            "import dspy\n"
            "cot = dspy.ChainOfThought('question -> answer')\n"
            "react = dspy.ReAct('question -> answer', tools=[search])\n"
        )

        import ast

        tree = ast.parse(mod_file.read_text(), filename=str(mod_file))
        visitor = DSPyModuleVisitor(mod_file)
        visitor.visit(tree)

        assert len(visitor.instantiations) == 2
        assert visitor.instantiations[0]["module_type"] == "ChainOfThought"
        assert visitor.instantiations[1]["module_type"] == "ReAct"
        assert "search" in visitor.instantiations[1]["tools"]

    def test_detects_predict_instantiation(self, tmp_path):
        mod_file = tmp_path / "simple.py"
        mod_file.write_text("import dspy\npredict = dspy.Predict('question -> answer')\n")

        import ast

        tree = ast.parse(mod_file.read_text(), filename=str(mod_file))
        visitor = DSPyModuleVisitor(mod_file)
        visitor.visit(tree)

        assert len(visitor.instantiations) == 1
        assert visitor.instantiations[0]["module_type"] == "Predict"


class TestExportWorkflows:
    """Test export_dspy_workflows function."""

    def test_export_empty_workspace(self, tmp_path):
        workflows = export_dspy_workflows(tmp_path)
        assert workflows == []

    def test_export_signature(self, tmp_path):
        sig_file = tmp_path / "sig.py"
        sig_file.write_text(
            "import dspy\n"
            "class Sentiment(dspy.Signature):\n"
            '    """Classify sentiment."""\n'
            "    text: str = dspy.InputField()\n"
            "    label: str = dspy.OutputField()\n"
        )

        workflows = export_dspy_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert wf.name == "Sentiment"
        assert wf.runtime == "dspy"
        assert wf.metadata["kind"] == "signature"
        assert wf.metadata["input_count"] == 1
        assert wf.metadata["output_count"] == 1

    def test_export_signature_has_input_output_nodes(self, tmp_path):
        sig_file = tmp_path / "sig.py"
        sig_file.write_text(
            "import dspy\n"
            "class QA(dspy.Signature):\n"
            "    question: str = dspy.InputField()\n"
            "    answer: str = dspy.OutputField()\n"
        )

        workflows = export_dspy_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        input_nodes = [n for n in wf.nodes if n.type == NodeType.START]
        output_nodes = [n for n in wf.nodes if n.type == NodeType.END]
        assert len(input_nodes) == 1
        assert len(output_nodes) == 1
        assert input_nodes[0].label == "question"
        assert output_nodes[0].label == "answer"

    def test_export_module_class(self, tmp_path):
        mod_file = tmp_path / "rag.py"
        mod_file.write_text(
            "import dspy\n"
            "class RAG(dspy.Module):\n"
            "    def __init__(self):\n"
            "        self.retrieve = dspy.ChainOfThought('query -> passages')\n"
            "        self.respond = dspy.ChainOfThought('context, question -> response')\n"
            "    def forward(self, question):\n"
            "        pass\n"
        )

        workflows = export_dspy_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert wf.name == "RAG"
        assert wf.runtime == "dspy"
        assert wf.metadata["kind"] == "module"
        assert wf.metadata["sub_module_count"] == 2

    def test_export_standalone_instantiations(self, tmp_path):
        prog_file = tmp_path / "program.py"
        prog_file.write_text(
            "import dspy\n"
            "cot = dspy.ChainOfThought('question -> answer')\n"
            "react = dspy.ReAct('question -> answer', tools=[search])\n"
        )

        workflows = export_dspy_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert wf.runtime == "dspy"
        assert wf.metadata["kind"] == "instantiation"
        assert wf.metadata["module_count"] == 2

    def test_export_react_with_tools(self, tmp_path):
        prog_file = tmp_path / "agent.py"
        prog_file.write_text(
            "import dspy\nreact = dspy.ReAct('question -> answer', tools=[search, calculate])\n"
        )

        workflows = export_dspy_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        tool_nodes = [n for n in wf.nodes if n.type == NodeType.TOOL]
        assert len(tool_nodes) == 2
        tool_labels = [n.label for n in tool_nodes]
        assert "search" in tool_labels
        assert "calculate" in tool_labels

    def test_export_ignores_venv(self, tmp_path):
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "sig.py"
        venv_file.write_text(
            "import dspy\nclass S(dspy.Signature):\n    q: str = dspy.InputField()\n"
        )

        workflows = export_dspy_workflows(tmp_path)
        assert len(workflows) == 0

    def test_export_handles_syntax_errors(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("import dspy\nthis is not valid python {{{")

        workflows = export_dspy_workflows(tmp_path)
        assert workflows == []

    def test_export_ignores_non_dspy_files(self, tmp_path):
        (tmp_path / "regular.py").write_text("class MyClass:\n    pass\n")

        workflows = export_dspy_workflows(tmp_path)
        assert workflows == []

    def test_workflow_metadata(self, tmp_path):
        sig_file = tmp_path / "sig.py"
        sig_file.write_text(
            "import dspy\n"
            "class Extract(dspy.Signature):\n"
            "    text: str = dspy.InputField()\n"
            "    entities: list = dspy.OutputField()\n"
        )

        workflows = export_dspy_workflows(tmp_path)

        assert len(workflows) == 1
        wf = workflows[0]
        assert "source_file" in wf.metadata
        assert "kind" in wf.metadata
        assert wf.metadata["kind"] == "signature"
