# ARC Adapter Usage Examples

This directory contains practical examples demonstrating how to use ARC runtime adapters.

## Examples

1. **Basic Detection** (`01_basic_detection.py`) - Detect runtimes in a workspace
2. **Multi-Adapter Detection** (`02_multi_adapter_detection.py`) - Use multiple adapters simultaneously
3. **Workflow Inspection** (`03_workflow_inspection.py`) - Inspect and export workflows
4. **Custom Adapter** (`04_custom_adapter.py`) - Create a custom runtime adapter
5. **Registry Usage** (`05_registry_usage.py`) - Use the adapter registry for runtime routing

## Running Examples

Each example is standalone and can be run directly:

```bash
cd python
uv run python examples/adapters/01_basic_detection.py
```

## Prerequisites

Install ARC with dev dependencies:

```bash
cd python
uv pip install -e ".[dev]"
```

## Example Workspaces

Some examples create temporary workspaces for demonstration. You can also point them to real workspaces:

```bash
uv run python examples/adapters/01_basic_detection.py /path/to/your/workspace
```

## Learn More

- [Adapter Base Class](../../src/agent_runtime_cockpit/adapters/base.py)
- [Adapter Registry](../../src/agent_runtime_cockpit/adapters/registry.py)
- [Adapter Tests](../../tests/test_adapters.py)
- [Adapter Benchmarks](../../benchmarks/)
