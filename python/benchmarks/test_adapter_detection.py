"""
Adapter Detection Benchmarks

Benchmarks for adapter detection performance across different workspace sizes.
These benchmarks are marked as off-gate (not required for CI).

Usage:
    pytest benchmarks/test_adapter_detection.py --benchmark-only
    pytest benchmarks/test_adapter_detection.py --benchmark-only --benchmark-save=baseline
    pytest benchmarks/test_adapter_detection.py --benchmark-only --benchmark-compare=baseline
"""
import pytest
from pathlib import Path
import tempfile
import shutil

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
OpenAIAgentsAdapter = load_adapter_class("openai_agents", "OpenAIAgentsAdapter")


@pytest.fixture
def empty_workspace(tmp_path):
    """Empty workspace for baseline measurements."""
    return tmp_path


@pytest.fixture
def small_workspace(tmp_path):
    """Small workspace with 10 files."""
    for i in range(10):
        (tmp_path / f"file_{i}.py").write_text(f"# File {i}\n")
    return tmp_path


@pytest.fixture
def medium_workspace(tmp_path):
    """Medium workspace with 100 files."""
    for i in range(100):
        (tmp_path / f"file_{i}.py").write_text(f"# File {i}\n")
    return tmp_path


@pytest.fixture
def large_workspace(tmp_path):
    """Large workspace with 1000 files."""
    for i in range(1000):
        (tmp_path / f"file_{i}.py").write_text(f"# File {i}\n")
    return tmp_path


@pytest.fixture
def swarmgraph_workspace(tmp_path):
    """Workspace with SwarmGraph artifacts."""
    (tmp_path / "swarmgraph.yaml").write_text("version: 1.0\n")
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "agent.py").write_text("# Agent\n")
    return tmp_path


@pytest.fixture
def langgraph_workspace(tmp_path):
    """Workspace with LangGraph artifacts."""
    (tmp_path / "graph.py").write_text("from langgraph.graph import StateGraph\n")
    return tmp_path


@pytest.fixture
def crewai_workspace(tmp_path):
    """Workspace with CrewAI artifacts."""
    (tmp_path / "crew.py").write_text("from crewai import Crew\n")
    return tmp_path


# SwarmGraph Detection Benchmarks
@pytest.mark.benchmark(group="detection-swarmgraph")
def test_swarmgraph_detect_empty(benchmark, empty_workspace):
    """Benchmark SwarmGraph detection on empty workspace."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.detect, empty_workspace)
    assert result[0] is False  # not detected


@pytest.mark.benchmark(group="detection-swarmgraph")
def test_swarmgraph_detect_small(benchmark, small_workspace):
    """Benchmark SwarmGraph detection on small workspace."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.detect, small_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-swarmgraph")
def test_swarmgraph_detect_medium(benchmark, medium_workspace):
    """Benchmark SwarmGraph detection on medium workspace."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.detect, medium_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-swarmgraph")
def test_swarmgraph_detect_large(benchmark, large_workspace):
    """Benchmark SwarmGraph detection on large workspace."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.detect, large_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-swarmgraph")
def test_swarmgraph_detect_positive(benchmark, swarmgraph_workspace):
    """Benchmark SwarmGraph detection on workspace with artifacts."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.detect, swarmgraph_workspace)
    assert result[0] is True  # detected


# LangGraph Detection Benchmarks
@pytest.mark.benchmark(group="detection-langgraph")
def test_langgraph_detect_empty(benchmark, empty_workspace):
    """Benchmark LangGraph detection on empty workspace."""
    adapter = LangGraphAdapter()
    result = benchmark(adapter.detect, empty_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-langgraph")
def test_langgraph_detect_small(benchmark, small_workspace):
    """Benchmark LangGraph detection on small workspace."""
    adapter = LangGraphAdapter()
    result = benchmark(adapter.detect, small_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-langgraph")
def test_langgraph_detect_medium(benchmark, medium_workspace):
    """Benchmark LangGraph detection on medium workspace."""
    adapter = LangGraphAdapter()
    result = benchmark(adapter.detect, medium_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-langgraph")
def test_langgraph_detect_positive(benchmark, langgraph_workspace):
    """Benchmark LangGraph detection on workspace with artifacts."""
    adapter = LangGraphAdapter()
    result = benchmark(adapter.detect, langgraph_workspace)
    assert result[0] is True


# CrewAI Detection Benchmarks
@pytest.mark.benchmark(group="detection-crewai")
def test_crewai_detect_empty(benchmark, empty_workspace):
    """Benchmark CrewAI detection on empty workspace."""
    adapter = CrewAIAdapter()
    result = benchmark(adapter.detect, empty_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-crewai")
def test_crewai_detect_small(benchmark, small_workspace):
    """Benchmark CrewAI detection on small workspace."""
    adapter = CrewAIAdapter()
    result = benchmark(adapter.detect, small_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-crewai")
def test_crewai_detect_positive(benchmark, crewai_workspace):
    """Benchmark CrewAI detection on workspace with artifacts."""
    adapter = CrewAIAdapter()
    result = benchmark(adapter.detect, crewai_workspace)
    assert result[0] is True


# OpenAI Agents Detection Benchmarks
@pytest.mark.benchmark(group="detection-openai")
def test_openai_detect_empty(benchmark, empty_workspace):
    """Benchmark OpenAI Agents detection on empty workspace."""
    adapter = OpenAIAgentsAdapter()
    result = benchmark(adapter.detect, empty_workspace)
    assert result[0] is False


@pytest.mark.benchmark(group="detection-openai")
def test_openai_detect_small(benchmark, small_workspace):
    """Benchmark OpenAI Agents detection on small workspace."""
    adapter = OpenAIAgentsAdapter()
    result = benchmark(adapter.detect, small_workspace)
    assert result[0] is False


# Capability Report Benchmarks
@pytest.mark.benchmark(group="capability-report")
def test_swarmgraph_capability_report(benchmark, swarmgraph_workspace):
    """Benchmark SwarmGraph capability report generation."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.capability_report, swarmgraph_workspace)
    assert result.runtime_id == "swarmgraph"


@pytest.mark.benchmark(group="capability-report")
def test_langgraph_capability_report(benchmark, langgraph_workspace):
    """Benchmark LangGraph capability report generation."""
    adapter = LangGraphAdapter()
    result = benchmark(adapter.capability_report, langgraph_workspace)
    assert result.runtime_id == "langgraph"


@pytest.mark.benchmark(group="capability-report")
def test_crewai_capability_report(benchmark, crewai_workspace):
    """Benchmark CrewAI capability report generation."""
    adapter = CrewAIAdapter()
    result = benchmark(adapter.capability_report, crewai_workspace)
    assert result.runtime_id == "crewai"


# Multi-adapter Detection Benchmarks
@pytest.mark.benchmark(group="multi-adapter")
def test_all_adapters_detect_empty(benchmark, empty_workspace):
    """Benchmark all adapters detecting on empty workspace."""
    adapters = [
        SwarmGraphAdapter(),
        LangGraphAdapter(),
        CrewAIAdapter(),
        OpenAIAgentsAdapter(),
    ]
    
    def detect_all():
        results = []
        for adapter in adapters:
            results.append(adapter.detect(empty_workspace))
        return results
    
    results = benchmark(detect_all)
    assert all(not r[0] for r in results)  # none detected


@pytest.mark.benchmark(group="multi-adapter")
def test_all_adapters_detect_small(benchmark, small_workspace):
    """Benchmark all adapters detecting on small workspace."""
    adapters = [
        SwarmGraphAdapter(),
        LangGraphAdapter(),
        CrewAIAdapter(),
        OpenAIAgentsAdapter(),
    ]
    
    def detect_all():
        results = []
        for adapter in adapters:
            results.append(adapter.detect(small_workspace))
        return results
    
    results = benchmark(detect_all)
    assert all(not r[0] for r in results)


# Capabilities Benchmarks
@pytest.mark.benchmark(group="capabilities")
def test_swarmgraph_capabilities(benchmark):
    """Benchmark SwarmGraph capabilities query."""
    adapter = SwarmGraphAdapter()
    result = benchmark(adapter.capabilities)
    assert result.can_run is not None


@pytest.mark.benchmark(group="capabilities")
def test_langgraph_capabilities(benchmark):
    """Benchmark LangGraph capabilities query."""
    adapter = LangGraphAdapter()
    result = benchmark(adapter.capabilities)
    assert result.can_run is not None


@pytest.mark.benchmark(group="capabilities")
def test_crewai_capabilities(benchmark):
    """Benchmark CrewAI capabilities query."""
    adapter = CrewAIAdapter()
    result = benchmark(adapter.capabilities)
    assert result.can_run is not None


@pytest.mark.benchmark(group="capabilities")
def test_openai_capabilities(benchmark):
    """Benchmark OpenAI Agents capabilities query."""
    adapter = OpenAIAgentsAdapter()
    result = benchmark(adapter.capabilities)
    assert result.can_run is not None
