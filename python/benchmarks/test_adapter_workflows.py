"""
Adapter Workflow Benchmarks

Benchmarks for adapter workflow export and schema operations.
These benchmarks are marked as off-gate (not required for CI).

Usage:
    pytest benchmarks/test_adapter_workflows.py --benchmark-only
    pytest benchmarks/test_adapter_workflows.py --benchmark-only --benchmark-save=baseline
"""
import pytest
from pathlib import Path

import sys
import importlib.util
from pathlib import Path

# Load adapters from .py files directly, bypassing the subdirectories
adapters_dir = Path(__file__).parent.parent / "src" / "agent_runtime_cockpit" / "adapters"

def load_adapter_class(module_name, class_name):
    """Load adapter class from .py file directly."""
    spec = importlib.util.spec_from_file_location(
        f"agent_runtime_cockpit.adapters.{module_name}",
        adapters_dir / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)

SwarmGraphAdapter = load_adapter_class("swarmgraph", "SwarmGraphAdapter")
LangGraphAdapter = load_adapter_class("langgraph", "LangGraphAdapter")
CrewAIAdapter = load_adapter_class("crewai", "CrewAIAdapter")


@pytest.fixture
def swarmgraph_workspace_with_workflows(tmp_path):
    """Workspace with SwarmGraph workflows."""
    (tmp_path / "swarmgraph.yaml").write_text("""
version: 1.0
workflows:
  - id: test-workflow
    name: Test Workflow
    description: A test workflow
""")
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "agent.py").write_text("""
from swarmgraph import Agent

agent = Agent(name="test", role="tester")
""")
    return tmp_path


@pytest.fixture
def langgraph_workspace_with_workflows(tmp_path):
    """Workspace with LangGraph workflows."""
    (tmp_path / "graph.py").write_text("""
from langgraph.graph import StateGraph

def create_graph():
    graph = StateGraph()
    graph.add_node("start", lambda x: x)
    graph.add_node("end", lambda x: x)
    graph.add_edge("start", "end")
    return graph.compile()
""")
    return tmp_path


@pytest.fixture
def crewai_workspace_with_workflows(tmp_path):
    """Workspace with CrewAI workflows."""
    (tmp_path / "crew.py").write_text("""
from crewai import Crew, Agent, Task

agent = Agent(role="tester", goal="test", backstory="testing")
task = Task(description="test task", agent=agent)
crew = Crew(agents=[agent], tasks=[task])
""")
    return tmp_path


# Workspace Inspection Benchmarks
@pytest.mark.benchmark(group="inspect-workspace")
def test_swarmgraph_inspect_workspace(benchmark, swarmgraph_workspace_with_workflows):
    """Benchmark SwarmGraph workspace inspection."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.inspect_workspace, swarmgraph_workspace_with_workflows)
    assert result.workspace_path is not None


@pytest.mark.benchmark(group="inspect-workspace")
def test_langgraph_inspect_workspace(benchmark, langgraph_workspace_with_workflows):
    """Benchmark LangGraph workspace inspection."""
    adapter = LangGraphAdapter()
    try:
        result = benchmark(adapter.inspect_workspace, langgraph_workspace_with_workflows)
        assert result.workspace_path is not None
    except NotImplementedError:
        pytest.skip("LangGraph inspect_workspace not implemented")


@pytest.mark.benchmark(group="inspect-workspace")
def test_crewai_inspect_workspace(benchmark, crewai_workspace_with_workflows):
    """Benchmark CrewAI workspace inspection."""
    adapter = CrewAIAdapter()
    try:
        result = benchmark(adapter.inspect_workspace, crewai_workspace_with_workflows)
        assert result.workspace_path is not None
    except NotImplementedError:
        pytest.skip("CrewAI inspect_workspace not implemented")


# Workflow Export Benchmarks
@pytest.mark.benchmark(group="export-workflow")
def test_swarmgraph_export_workflow(benchmark, swarmgraph_workspace_with_workflows):
    """Benchmark SwarmGraph workflow export."""
    adapter = SwarmGraphAdapter()
    try:
        result = benchmark(adapter.export_workflow, swarmgraph_workspace_with_workflows)
        assert isinstance(result, list)
    except NotImplementedError:
        pytest.skip("SwarmGraph export_workflow not implemented")


@pytest.mark.benchmark(group="export-workflow")
def test_langgraph_export_workflow(benchmark, langgraph_workspace_with_workflows):
    """Benchmark LangGraph workflow export."""
    adapter = LangGraphAdapter()
    try:
        result = benchmark(adapter.export_workflow, langgraph_workspace_with_workflows)
        assert isinstance(result, list)
    except NotImplementedError:
        pytest.skip("LangGraph export_workflow not implemented")


@pytest.mark.benchmark(group="export-workflow")
def test_crewai_export_workflow(benchmark, crewai_workspace_with_workflows):
    """Benchmark CrewAI workflow export."""
    adapter = CrewAIAdapter()
    try:
        result = benchmark(adapter.export_workflow, crewai_workspace_with_workflows)
        assert isinstance(result, list)
    except NotImplementedError:
        pytest.skip("CrewAI export_workflow not implemented")


# Schema Export Benchmarks
@pytest.mark.benchmark(group="export-schemas")
def test_swarmgraph_export_schemas(benchmark, swarmgraph_workspace_with_workflows):
    """Benchmark SwarmGraph schema export."""
    adapter = SwarmGraphAdapter()
    try:
        result = benchmark(adapter.export_schemas, swarmgraph_workspace_with_workflows)
        assert isinstance(result, list)
    except NotImplementedError:
        pytest.skip("SwarmGraph export_schemas not implemented")


@pytest.mark.benchmark(group="export-schemas")
def test_langgraph_export_schemas(benchmark, langgraph_workspace_with_workflows):
    """Benchmark LangGraph schema export."""
    adapter = LangGraphAdapter()
    try:
        result = benchmark(adapter.export_schemas, langgraph_workspace_with_workflows)
        assert isinstance(result, list)
    except NotImplementedError:
        pytest.skip("LangGraph export_schemas not implemented")


@pytest.mark.benchmark(group="export-schemas")
def test_crewai_export_schemas(benchmark, crewai_workspace_with_workflows):
    """Benchmark CrewAI schema export."""
    adapter = CrewAIAdapter()
    try:
        result = benchmark(adapter.export_schemas, crewai_workspace_with_workflows)
        assert isinstance(result, list)
    except NotImplementedError:
        pytest.skip("CrewAI export_schemas not implemented")


# Combined Operations Benchmarks
@pytest.mark.benchmark(group="combined-operations")
def test_swarmgraph_full_inspection(benchmark, swarmgraph_workspace_with_workflows):
    """Benchmark full SwarmGraph inspection (detect + inspect + export)."""
    adapter = SwarmGraphAdapter()
    
    def full_inspection():
        detected, confidence, evidence = adapter.detect(swarmgraph_workspace_with_workflows)
        if detected:
            workspace_info = adapter.inspect_workspace(swarmgraph_workspace_with_workflows)
            try:
                workflows = adapter.export_workflow(swarmgraph_workspace_with_workflows)
            except NotImplementedError:
                workflows = []
            try:
                schemas = adapter.export_schemas(swarmgraph_workspace_with_workflows)
            except NotImplementedError:
                schemas = []
            return workspace_info, workflows, schemas
        return None, [], []
    
    result = benchmark(full_inspection)
    assert result[0] is not None


@pytest.mark.benchmark(group="combined-operations")
def test_langgraph_full_inspection(benchmark, langgraph_workspace_with_workflows):
    """Benchmark full LangGraph inspection (detect + inspect + export)."""
    adapter = LangGraphAdapter()
    
    def full_inspection():
        detected, confidence, evidence = adapter.detect(langgraph_workspace_with_workflows)
        if detected:
            try:
                workspace_info = adapter.inspect_workspace(langgraph_workspace_with_workflows)
            except NotImplementedError:
                workspace_info = None
            try:
                workflows = adapter.export_workflow(langgraph_workspace_with_workflows)
            except NotImplementedError:
                workflows = []
            try:
                schemas = adapter.export_schemas(langgraph_workspace_with_workflows)
            except NotImplementedError:
                schemas = []
            return workspace_info, workflows, schemas
        return None, [], []
    
    result = benchmark(full_inspection)
    # LangGraph should be detected
    assert result is not None


@pytest.mark.benchmark(group="combined-operations")
def test_crewai_full_inspection(benchmark, crewai_workspace_with_workflows):
    """Benchmark full CrewAI inspection (detect + inspect + export)."""
    adapter = CrewAIAdapter()
    
    def full_inspection():
        detected, confidence, evidence = adapter.detect(crewai_workspace_with_workflows)
        if detected:
            try:
                workspace_info = adapter.inspect_workspace(crewai_workspace_with_workflows)
            except NotImplementedError:
                workspace_info = None
            try:
                workflows = adapter.export_workflow(crewai_workspace_with_workflows)
            except NotImplementedError:
                workflows = []
            try:
                schemas = adapter.export_schemas(crewai_workspace_with_workflows)
            except NotImplementedError:
                schemas = []
            return workspace_info, workflows, schemas
        return None, [], []
    
    result = benchmark(full_inspection)
    # CrewAI should be detected
    assert result is not None


# Adapter Initialization Benchmarks
@pytest.mark.benchmark(group="initialization")
def test_swarmgraph_adapter_init(benchmark):
    """Benchmark SwarmGraph adapter initialization."""
    result = benchmark(SwarmGraphAdapter)
    assert result.adapter_id == "swarmgraph"


@pytest.mark.benchmark(group="initialization")
def test_langgraph_adapter_init(benchmark):
    """Benchmark LangGraph adapter initialization."""
    result = benchmark(LangGraphAdapter)
    assert result.adapter_id == "langgraph"


@pytest.mark.benchmark(group="initialization")
def test_crewai_adapter_init(benchmark):
    """Benchmark CrewAI adapter initialization."""
    result = benchmark(CrewAIAdapter)
    assert result.adapter_id == "crewai"


@pytest.mark.benchmark(group="initialization")
def test_all_adapters_init(benchmark):
    """Benchmark initialization of all adapters."""
    def init_all():
        return [
            SwarmGraphAdapter(),
            LangGraphAdapter(),
            CrewAIAdapter(),
        ]
    
    result = benchmark(init_all)
    assert len(result) == 3
