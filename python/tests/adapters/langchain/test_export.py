"""Tests for LangChain export functionality (Phase 26 T2).

Phase 26 T2: Export via AST-based detection.
Minimum 10 tests required per roadmap.
"""

from __future__ import annotations

import textwrap
from pathlib import Path


from agent_runtime_cockpit.adapters.langchain import LangChainAdapter
from agent_runtime_cockpit.adapters.langchain.export import (
    scan_workspace_for_chains,
    chain_to_workflow_info,
    export_langchain_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


# Test 1: Scan workspace for pipe operator chains
def test_scan_workspace_detects_pipe_chains(tmp_path: Path):
    """Test workspace scanning detects LCEL pipe operator chains."""
    chain_file = tmp_path / "chain.py"
    chain_file.write_text(
        textwrap.dedent("""
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        prompt = ChatPromptTemplate.from_template("Hello {name}")
        parser = StrOutputParser()
        
        my_chain = prompt | parser
    """)
    )

    chains = scan_workspace_for_chains(tmp_path)

    assert len(chains) >= 1
    chain = chains[0]
    assert chain["name"] == "my_chain"
    assert chain["type"] == "pipe_chain"
    assert "prompt" in chain["components"]
    assert "parser" in chain["components"]


# Test 2: Scan workspace for RunnableSequence
def test_scan_workspace_detects_runnable_sequence(tmp_path: Path):
    """Test workspace scanning detects RunnableSequence instantiations."""
    chain_file = tmp_path / "sequence.py"
    chain_file.write_text(
        textwrap.dedent("""
        from langchain_core.runnables import RunnableSequence
        
        step1 = SomeRunnable()
        step2 = AnotherRunnable()
        
        sequence_chain = RunnableSequence(step1, step2)
    """)
    )

    chains = scan_workspace_for_chains(tmp_path)

    assert len(chains) >= 1
    chain = chains[0]
    assert chain["name"] == "sequence_chain"
    assert chain["type"] == "sequence_chain"
    assert len(chain["components"]) == 2


# Test 3: Convert chain to WorkflowInfo
def test_chain_to_workflow_info(tmp_path: Path):
    """Test conversion of detected chain to WorkflowInfo structure."""
    chain = {
        "name": "test_chain",
        "type": "pipe_chain",
        "components": ["prompt", "llm", "parser"],
        "source_file": "chain.py",
        "lineno": 10,
    }

    workflow = chain_to_workflow_info(chain, tmp_path)

    assert workflow.id == "langchain_test_chain"
    assert workflow.name == "test_chain"
    assert workflow.runtime == "langchain"
    assert workflow.source_file == "chain.py"
    assert len(workflow.nodes) == 3
    assert len(workflow.edges) == 2
    assert len(workflow.entry_points) == 1


# Test 4: WorkflowInfo nodes have correct structure
def test_workflow_info_nodes_structure(tmp_path: Path):
    """Test that WorkflowInfo nodes have correct structure."""
    chain = {
        "name": "my_chain",
        "type": "pipe_chain",
        "components": ["step1", "step2"],
        "source_file": "test.py",
        "lineno": 5,
    }

    workflow = chain_to_workflow_info(chain, tmp_path)

    assert len(workflow.nodes) == 2
    node1 = workflow.nodes[0]
    assert node1.label == "step1"
    assert node1.type == NodeType.UNKNOWN
    assert node1.source_location is not None
    assert node1.source_location.file == "test.py"
    assert node1.source_location.line == 5


# Test 5: WorkflowInfo edges connect nodes sequentially
def test_workflow_info_edges_sequential(tmp_path: Path):
    """Test that WorkflowInfo edges connect nodes in sequence."""
    chain = {
        "name": "chain",
        "type": "pipe_chain",
        "components": ["a", "b", "c"],
        "source_file": "test.py",
        "lineno": 1,
    }

    workflow = chain_to_workflow_info(chain, tmp_path)

    assert len(workflow.edges) == 2
    edge1 = workflow.edges[0]
    assert edge1.from_node == workflow.nodes[0].id
    assert edge1.to_node == workflow.nodes[1].id
    assert edge1.conditional is False

    edge2 = workflow.edges[1]
    assert edge2.from_node == workflow.nodes[1].id
    assert edge2.to_node == workflow.nodes[2].id


# Test 6: Export workflows from trivial chain fixture
def test_export_trivial_chain_fixture():
    """Test export from trivial chain fixture project."""
    fixture_path = Path(__file__).parent / "fixtures" / "trivial_chain"

    workflows = export_langchain_workflows(fixture_path)

    assert len(workflows) >= 1
    # Should detect simple_chain and/or explicit_chain
    chain_names = [w.name for w in workflows]
    assert "simple_chain" in chain_names or "explicit_chain" in chain_names


# Test 7: Export workflows from retrieval pipeline fixture
def test_export_retrieval_pipeline_fixture():
    """Test export from retrieval pipeline fixture project."""
    fixture_path = Path(__file__).parent / "fixtures" / "retrieval_pipeline"

    workflows = export_langchain_workflows(fixture_path)

    assert len(workflows) >= 1
    # Should detect rag_chain and/or multi_step_chain
    chain_names = [w.name for w in workflows]
    assert "rag_chain" in chain_names or "multi_step_chain" in chain_names


# Test 8: LangChainAdapter export_workflow method
def test_langchain_adapter_export_workflow(tmp_path: Path):
    """Test LangChainAdapter.export_workflow() method."""
    chain_file = tmp_path / "app.py"
    chain_file.write_text(
        textwrap.dedent("""
        prompt = PromptTemplate()
        llm = ChatOpenAI()
        
        app_chain = prompt | llm
    """)
    )

    adapter = LangChainAdapter()
    workflows = adapter.export_workflow(tmp_path)

    assert isinstance(workflows, list)
    if workflows:  # May be empty if no chains detected
        assert all(w.runtime == "langchain" for w in workflows)


# Test 9: Export handles empty workspace
def test_export_empty_workspace(tmp_path: Path):
    """Test export handles workspace with no chains gracefully."""
    # Create empty Python file
    (tmp_path / "empty.py").write_text("# No chains here\n")

    workflows = export_langchain_workflows(tmp_path)

    assert isinstance(workflows, list)
    assert len(workflows) == 0


# Test 10: Export ignores venv directories
def test_export_ignores_venv(tmp_path: Path):
    """Test that export ignores .venv and venv directories."""
    # Create chain in venv (should be ignored)
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    venv_file = venv_dir / "chain.py"
    venv_file.write_text("venv_chain = a | b")

    # Create chain in main workspace (should be detected)
    main_file = tmp_path / "main.py"
    main_file.write_text("main_chain = x | y")

    chains = scan_workspace_for_chains(tmp_path)

    chain_names = [c["name"] for c in chains]
    assert "main_chain" in chain_names
    assert "venv_chain" not in chain_names


# Test 11: AST visitor handles complex nested chains
def test_ast_visitor_nested_chains(tmp_path: Path):
    """Test AST visitor handles complex nested pipe chains."""
    chain_file = tmp_path / "complex.py"
    chain_file.write_text(
        textwrap.dedent("""
        a = Step1()
        b = Step2()
        c = Step3()
        d = Step4()
        
        complex_chain = a | b | c | d
    """)
    )

    chains = scan_workspace_for_chains(tmp_path)

    assert len(chains) >= 1
    chain = chains[0]
    assert chain["name"] == "complex_chain"
    assert len(chain["components"]) == 4
    assert chain["components"] == ["a", "b", "c", "d"]


# Test 12: Export handles syntax errors gracefully
def test_export_handles_syntax_errors(tmp_path: Path):
    """Test export handles files with syntax errors gracefully."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("this is not valid python syntax ][{")

    good_file = tmp_path / "good.py"
    good_file.write_text("good_chain = a | b")

    workflows = export_langchain_workflows(tmp_path)

    # Should still export the good file
    assert len(workflows) >= 1
    assert workflows[0].name == "good_chain"


# Test 13: Capabilities reflect export support
def test_capabilities_reflect_export_support():
    """Test that adapter capabilities correctly reflect export support."""
    adapter = LangChainAdapter()
    caps = adapter.capabilities()

    assert caps.can_export_workflow is True
    assert caps.can_inspect is True
    assert caps.can_run is False  # T3 not yet implemented


# Test 14: Capability report mentions export availability
def test_capability_report_mentions_export(tmp_path: Path, monkeypatch):
    """Test capability report mentions export availability."""
    # Mock langchain as installed
    from unittest.mock import MagicMock
    import importlib.util

    mock_spec = MagicMock()
    mock_langchain = MagicMock()
    mock_langchain.__version__ = "0.3.5"

    def fake_find_spec(name):
        if name == "langchain":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    from unittest.mock import patch

    with patch.dict("sys.modules", {"langchain": mock_langchain}):
        adapter = LangChainAdapter()
        report = adapter.capability_report(tmp_path)

    assert report.detected is True
    # Reason should mention export or T2
    assert "export" in report.reason.lower() or "t2" in report.reason.lower()


# Test 15: Export metadata includes detection method
def test_export_metadata_includes_detection_method(tmp_path: Path):
    """Test that exported workflows include detection method in metadata."""
    chain_file = tmp_path / "chain.py"
    chain_file.write_text("my_chain = a | b")

    workflows = export_langchain_workflows(tmp_path)

    assert len(workflows) >= 1
    workflow = workflows[0]
    assert "detection_method" in workflow.metadata
    assert workflow.metadata["detection_method"] == "ast_scan"
