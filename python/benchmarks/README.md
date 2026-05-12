# ARC Adapter Benchmarks

Performance benchmarks for ARC runtime adapters. These benchmarks are **off-gate** (not required for CI to pass) and are used for performance monitoring and regression detection.

## Overview

The benchmark suite covers:

- **Adapter Detection**: Performance of runtime detection across different workspace sizes
- **Workflow Operations**: Export and inspection performance
- **Registry Operations**: Multi-adapter coordination and lookup performance
- **Initialization**: Adapter and registry initialization overhead

## Running Benchmarks

### Prerequisites

Install benchmark dependencies:

```bash
cd python
uv pip install -e ".[dev]"
```

### Basic Usage

Run all benchmarks:

```bash
pytest benchmarks/ --benchmark-only
```

Run specific benchmark file:

```bash
pytest benchmarks/test_adapter_detection.py --benchmark-only
```

Run specific benchmark group:

```bash
pytest benchmarks/ --benchmark-only -k "detection-swarmgraph"
```

### Saving Baselines

Save a baseline for comparison:

```bash
pytest benchmarks/ --benchmark-only --benchmark-save=baseline
```

Compare against baseline:

```bash
pytest benchmarks/ --benchmark-only --benchmark-compare=baseline
```

### Advanced Options

Generate histogram:

```bash
pytest benchmarks/ --benchmark-only --benchmark-histogram
```

Adjust number of rounds:

```bash
pytest benchmarks/ --benchmark-only --benchmark-min-rounds=10
```

Disable GC during benchmarks:

```bash
pytest benchmarks/ --benchmark-only --benchmark-disable-gc
```

## Benchmark Groups

### Detection Benchmarks

- `detection-swarmgraph`: SwarmGraph detection performance
- `detection-langgraph`: LangGraph detection performance
- `detection-crewai`: CrewAI detection performance
- `detection-openai`: OpenAI Agents detection performance

### Workflow Benchmarks

- `inspect-workspace`: Workspace inspection performance
- `export-workflow`: Workflow export performance
- `export-schemas`: Schema export performance
- `combined-operations`: Full inspection pipeline

### Registry Benchmarks

- `registry-init`: Registry initialization
- `registry-lookup`: Adapter lookup operations
- `multi-detection`: Multi-adapter detection
- `registry-capabilities`: Capability queries
- `registry-registration`: Adapter registration/unregistration
- `concurrent-simulation`: Concurrent detection simulation
- `registry-filtering`: Adapter filtering operations

### Initialization Benchmarks

- `initialization`: Adapter initialization overhead
- `capabilities`: Capability query performance

## Performance Targets

These are aspirational targets, not hard requirements:

| Operation | Target | Notes |
|-----------|--------|-------|
| Adapter detection (empty workspace) | < 10ms | Should be fast for negative cases |
| Adapter detection (small workspace) | < 50ms | 10-100 files |
| Adapter detection (medium workspace) | < 200ms | 100-1000 files |
| Adapter detection (large workspace) | < 1s | 1000+ files |
| Capability report | < 20ms | Includes detection |
| Registry initialization (4 adapters) | < 50ms | One-time cost |
| Adapter lookup | < 1ms | Should be O(1) |
| Multi-adapter detection (4 adapters) | < 100ms | Empty workspace |

## Interpreting Results

### Statistics

- **Min**: Fastest execution time (best case)
- **Max**: Slowest execution time (worst case)
- **Mean**: Average execution time
- **StdDev**: Standard deviation (consistency indicator)
- **Median**: Middle value (50th percentile)
- **IQR**: Interquartile range (middle 50% spread)
- **Outliers**: Runs significantly slower/faster than typical

### What to Watch For

- **Regressions**: Mean time increases significantly between runs
- **High StdDev**: Inconsistent performance (may indicate caching issues)
- **Outliers**: May indicate GC pauses or system interference
- **Scaling**: Performance should scale sub-linearly with workspace size

## CI Integration

Benchmarks are marked as **off-gate** using pytest markers. They:

- Do NOT block PR merges
- Run on a schedule (nightly/weekly)
- Generate performance reports for monitoring
- Alert on significant regressions (>20% slowdown)

To run benchmarks in CI:

```bash
pytest benchmarks/ --benchmark-only --benchmark-json=benchmark-results.json
```

## Adding New Benchmarks

1. Create a new test file in `benchmarks/`
2. Use `@pytest.mark.benchmark(group="group-name")` decorator
3. Use `benchmark` fixture to wrap the operation
4. Add assertions to verify correctness
5. Document the benchmark in this README

Example:

```python
@pytest.mark.benchmark(group="my-operation")
def test_my_operation(benchmark):
    """Benchmark my operation."""
    adapter = MyAdapter()
    result = benchmark(adapter.my_operation, arg1, arg2)
    assert result is not None
```

## Troubleshooting

### Benchmarks are slow

- Reduce workspace sizes in fixtures
- Use `--benchmark-min-rounds=1` for quick checks
- Run specific groups instead of all benchmarks

### High variance in results

- Close other applications
- Disable CPU frequency scaling
- Use `--benchmark-disable-gc`
- Increase `--benchmark-min-rounds`

### Import errors

- Ensure dev dependencies are installed: `uv pip install -e ".[dev]"`
- Check that adapters are importable: `python -c "from agent_runtime_cockpit.adapters import SwarmGraphAdapter"`

## References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [ARC Adapter Base Class](../src/agent_runtime_cockpit/adapters/base.py)
- [ARC Adapter Registry](../src/agent_runtime_cockpit/adapters/registry.py)
