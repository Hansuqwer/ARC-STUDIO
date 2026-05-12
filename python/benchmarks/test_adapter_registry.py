"""
Adapter Registry Benchmarks

Benchmarks for adapter registry operations and multi-adapter scenarios.
These benchmarks are marked as off-gate (not required for CI).

Usage:
    pytest benchmarks/test_adapter_registry.py --benchmark-only
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
OpenAIAgentsAdapter = load_adapter_class("openai_agents", "OpenAIAgentsAdapter")

from agent_runtime_cockpit.adapters.registry import AdapterRegistry


@pytest.fixture
def registry():
    """Create adapter registry with all adapters."""
    reg = AdapterRegistry()
    reg.register(SwarmGraphAdapter())
    reg.register(LangGraphAdapter())
    reg.register(CrewAIAdapter())
    reg.register(OpenAIAgentsAdapter())
    return reg


@pytest.fixture
def mixed_workspace(tmp_path):
    """Workspace with multiple runtime artifacts."""
    # SwarmGraph
    (tmp_path / "swarmgraph.yaml").write_text("version: 1.0\n")
    # LangGraph
    (tmp_path / "graph.py").write_text("from langgraph.graph import StateGraph\n")
    # CrewAI
    (tmp_path / "crew.py").write_text("from crewai import Crew\n")
    return tmp_path


# Registry Initialization Benchmarks
@pytest.mark.benchmark(group="registry-init")
def test_registry_init_empty(benchmark):
    """Benchmark empty registry initialization."""
    result = benchmark(AdapterRegistry)
    assert result is not None


@pytest.mark.benchmark(group="registry-init")
def test_registry_init_with_adapters(benchmark):
    """Benchmark registry initialization with all adapters."""
    def init_registry():
        reg = AdapterRegistry()
        reg.register(SwarmGraphAdapter())
        reg.register(LangGraphAdapter())
        reg.register(CrewAIAdapter())
        reg.register(OpenAIAgentsAdapter())
        return reg
    
    result = benchmark(init_registry)
    assert len(result.list_adapters()) == 4


# Registry Lookup Benchmarks
@pytest.mark.benchmark(group="registry-lookup")
def test_registry_get_adapter(benchmark, registry):
    """Benchmark adapter lookup by ID."""
    result = benchmark(registry.get_adapter, "swarmgraph")
    assert result.adapter_id == "swarmgraph"


@pytest.mark.benchmark(group="registry-lookup")
def test_registry_list_adapters(benchmark, registry):
    """Benchmark listing all adapters."""
    result = benchmark(registry.list_adapters)
    assert len(result) == 4


@pytest.mark.benchmark(group="registry-lookup")
def test_registry_has_adapter(benchmark, registry):
    """Benchmark checking adapter existence."""
    result = benchmark(registry.has_adapter, "swarmgraph")
    assert result is True


# Multi-Adapter Detection Benchmarks
@pytest.mark.benchmark(group="multi-detection")
def test_registry_detect_all_empty(benchmark, registry, tmp_path):
    """Benchmark detecting all adapters on empty workspace."""
    def detect_all():
        results = {}
        for adapter in registry.list_adapters():
            results[adapter.adapter_id] = adapter.detect(tmp_path)
        return results
    
    result = benchmark(detect_all)
    assert all(not r[0] for r in result.values())


@pytest.mark.benchmark(group="multi-detection")
def test_registry_detect_all_mixed(benchmark, registry, mixed_workspace):
    """Benchmark detecting all adapters on mixed workspace."""
    def detect_all():
        results = {}
        for adapter in registry.list_adapters():
            results[adapter.adapter_id] = adapter.detect(mixed_workspace)
        return results
    
    result = benchmark(detect_all)
    # At least one should be detected
    assert any(r[0] for r in result.values())


@pytest.mark.benchmark(group="multi-detection")
def test_registry_find_best_adapter(benchmark, registry, mixed_workspace):
    """Benchmark finding best adapter for workspace."""
    def find_best():
        best_adapter = None
        best_confidence = 0.0
        for adapter in registry.list_adapters():
            detected, confidence, _ = adapter.detect(mixed_workspace)
            if detected and confidence > best_confidence:
                best_adapter = adapter
                best_confidence = confidence
        return best_adapter, best_confidence
    
    result = benchmark(find_best)
    assert result[0] is not None


# Capability Report Benchmarks
@pytest.mark.benchmark(group="registry-capabilities")
def test_registry_all_capabilities(benchmark, registry):
    """Benchmark getting capabilities for all adapters."""
    def get_all_capabilities():
        return {
            adapter.adapter_id: adapter.capabilities()
            for adapter in registry.list_adapters()
        }
    
    result = benchmark(get_all_capabilities)
    assert len(result) == 4


@pytest.mark.benchmark(group="registry-capabilities")
def test_registry_all_capability_reports(benchmark, registry, mixed_workspace):
    """Benchmark generating capability reports for all adapters."""
    def get_all_reports():
        return {
            adapter.adapter_id: adapter.capability_report(mixed_workspace)
            for adapter in registry.list_adapters()
        }
    
    result = benchmark(get_all_reports)
    assert len(result) == 4


# Adapter Registration Benchmarks
@pytest.mark.benchmark(group="registry-registration")
def test_registry_register_single(benchmark):
    """Benchmark registering a single adapter."""
    def register_adapter():
        reg = AdapterRegistry()
        reg.register(SwarmGraphAdapter())
        return reg
    
    result = benchmark(register_adapter)
    assert len(result.list_adapters()) == 1


@pytest.mark.benchmark(group="registry-registration")
def test_registry_register_multiple(benchmark):
    """Benchmark registering multiple adapters."""
    def register_adapters():
        reg = AdapterRegistry()
        reg.register(SwarmGraphAdapter())
        reg.register(LangGraphAdapter())
        reg.register(CrewAIAdapter())
        reg.register(OpenAIAgentsAdapter())
        return reg
    
    result = benchmark(register_adapters)
    assert len(result.list_adapters()) == 4


@pytest.mark.benchmark(group="registry-registration")
def test_registry_unregister(benchmark, registry):
    """Benchmark unregistering an adapter."""
    def unregister_adapter():
        reg = AdapterRegistry()
        reg.register(SwarmGraphAdapter())
        reg.register(LangGraphAdapter())
        reg.unregister("swarmgraph")
        return reg
    
    result = benchmark(unregister_adapter)
    assert not result.has_adapter("swarmgraph")


# Concurrent Detection Simulation
@pytest.mark.benchmark(group="concurrent-simulation")
def test_registry_sequential_detection(benchmark, registry, tmp_path):
    """Benchmark sequential detection across multiple workspaces."""
    workspaces = [tmp_path / f"workspace_{i}" for i in range(10)]
    for ws in workspaces:
        ws.mkdir()
        (ws / "file.py").write_text("# test\n")
    
    def detect_sequential():
        results = []
        for ws in workspaces:
            for adapter in registry.list_adapters():
                results.append(adapter.detect(ws))
        return results
    
    result = benchmark(detect_sequential)
    assert len(result) == 40  # 10 workspaces * 4 adapters


# Adapter Filtering Benchmarks
@pytest.mark.benchmark(group="registry-filtering")
def test_registry_filter_runnable(benchmark, registry, mixed_workspace):
    """Benchmark filtering adapters by runnable status."""
    def filter_runnable():
        runnable = []
        for adapter in registry.list_adapters():
            report = adapter.capability_report(mixed_workspace)
            if report.can_run and report.detected:
                runnable.append(adapter)
        return runnable
    
    result = benchmark(filter_runnable)
    assert isinstance(result, list)


@pytest.mark.benchmark(group="registry-filtering")
def test_registry_filter_detected(benchmark, registry, mixed_workspace):
    """Benchmark filtering adapters by detection status."""
    def filter_detected():
        detected = []
        for adapter in registry.list_adapters():
            is_detected, _, _ = adapter.detect(mixed_workspace)
            if is_detected:
                detected.append(adapter)
        return detected
    
    result = benchmark(filter_detected)
    assert isinstance(result, list)
    assert len(result) > 0  # At least one should be detected in mixed workspace
