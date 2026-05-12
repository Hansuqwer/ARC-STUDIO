#!/usr/bin/env python3
"""
Example 5: Registry Usage

This example demonstrates how to use the AdapterRegistry for
runtime detection, routing, and management.

Usage:
    python 05_registry_usage.py [workspace_path]
"""
import sys
from pathlib import Path
import tempfile

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent_runtime_cockpit.adapters.registry import AdapterRegistry
from _adapter_loader import (
    SwarmGraphAdapter, LangGraphAdapter, CrewAIAdapter, OpenAIAgentsAdapter
)


def create_polyglot_workspace(path: Path):
    """Create a workspace with multiple runtime artifacts."""
    path.mkdir(parents=True, exist_ok=True)
    
    # SwarmGraph (primary)
    (path / "swarmgraph.yaml").write_text("""
version: 1.0
name: Polyglot Agent System
description: Multi-framework agent system
""")
    
    # LangGraph (secondary)
    (path / "experimental_graph.py").write_text("""
# Experimental LangGraph implementation
from langgraph.graph import StateGraph

graph = StateGraph()
""")
    
    # CrewAI (legacy)
    (path / "legacy_crew.py").write_text("""
# Legacy CrewAI implementation (deprecated)
from crewai import Crew
""")
    
    print(f"✓ Created polyglot workspace at {path}")


def demonstrate_registry_basics():
    """Demonstrate basic registry operations."""
    print(f"\n{'='*70}")
    print("Registry Basics")
    print(f"{'='*70}")
    
    # Create empty registry
    registry = AdapterRegistry()
    print(f"Created empty registry")
    print(f"Registered adapters: {len(registry.all())}")
    
    # Register adapters one by one
    print(f"\nRegistering adapters...")
    registry.register(SwarmGraphAdapter())
    print(f"  ✓ Registered SwarmGraph")
    
    registry.register(LangGraphAdapter())
    print(f"  ✓ Registered LangGraph")
    
    registry.register(CrewAIAdapter())
    print(f"  ✓ Registered CrewAI")
    
    registry.register(OpenAIAgentsAdapter())
    print(f"  ✓ Registered OpenAI Agents")
    
    print(f"\nTotal registered adapters: {len(registry.all())}")
    
    # List all adapters
    print(f"\nRegistered adapters:")
    for adapter in registry.all():
        print(f"  • {adapter.adapter_name} (ID: {adapter.adapter_id})")
    
    return registry


def demonstrate_adapter_lookup(registry: AdapterRegistry):
    """Demonstrate adapter lookup operations."""
    print(f"\n{'='*70}")
    print("Adapter Lookup")
    print(f"{'='*70}")
    
    # Get adapter by ID
    adapter = registry.get("swarmgraph")
    if adapter:
        print(f"✓ Found adapter: {adapter.adapter_name}")
    else:
        print(f"✗ Adapter not found")
    
    # Try to get non-existent adapter
    adapter = registry.get("nonexistent")
    if adapter:
        print(f"✓ Found adapter: {adapter.adapter_name}")
    else:
        print(f"✗ Adapter 'nonexistent' not found (expected)")


def demonstrate_detection(registry: AdapterRegistry, workspace_path: Path):
    """Demonstrate multi-adapter detection using registry."""
    print(f"\n{'='*70}")
    print("Multi-Adapter Detection via Registry")
    print(f"{'='*70}")
    print(f"Workspace: {workspace_path}\n")
    
    # Detect all runtimes
    detected_runtimes = registry.detect_all(workspace_path)
    
    if not detected_runtimes:
        print("✗ No runtimes detected")
        return []
    
    print(f"✓ Detected {len(detected_runtimes)} runtime(s):\n")
    
    for runtime in detected_runtimes:
        print(f"  {runtime.name}")
        print(f"    ID: {runtime.id}")
        print(f"    Adapter: {runtime.adapter}")
        print(f"    Confidence: {runtime.confidence}")
        print(f"    Evidence: {', '.join(runtime.evidence[:3])}")
        if len(runtime.evidence) > 3:
            print(f"              ... and {len(runtime.evidence) - 3} more")
        print()
    
    return detected_runtimes


def demonstrate_runtime_selection(detected_runtimes):
    """Demonstrate how to select the best runtime."""
    print(f"\n{'='*70}")
    print("Runtime Selection Strategy")
    print(f"{'='*70}")
    
    if not detected_runtimes:
        print("No runtimes to select from")
        return None
    
    if len(detected_runtimes) == 1:
        runtime = detected_runtimes[0]
        print(f"✓ Single runtime detected: {runtime.name}")
        print(f"  Automatic selection: {runtime.adapter}")
        return runtime
    
    print(f"Multiple runtimes detected ({len(detected_runtimes)})")
    print(f"\nSelection strategies:\n")
    
    # Strategy 1: Highest confidence
    by_confidence = sorted(detected_runtimes, 
                          key=lambda r: (r.confidence.value, len(r.evidence)), 
                          reverse=True)
    best = by_confidence[0]
    print(f"1. Highest Confidence:")
    print(f"   → {best.name} ({best.adapter})")
    print(f"     Confidence: {best.confidence}, Evidence: {len(best.evidence)} items")
    
    # Strategy 2: Most evidence
    by_evidence = sorted(detected_runtimes, 
                        key=lambda r: len(r.evidence), 
                        reverse=True)
    most_evidence = by_evidence[0]
    print(f"\n2. Most Evidence:")
    print(f"   → {most_evidence.name} ({most_evidence.adapter})")
    print(f"     Evidence: {len(most_evidence.evidence)} items")
    
    # Strategy 3: Explicit priority list
    priority_order = ["swarmgraph", "langgraph", "crewai", "openai_agents"]
    for adapter_id in priority_order:
        matching = [r for r in detected_runtimes if r.adapter == adapter_id]
        if matching:
            priority_choice = matching[0]
            print(f"\n3. Priority Order (swarmgraph > langgraph > crewai > openai):")
            print(f"   → {priority_choice.name} ({priority_choice.adapter})")
            break
    
    print(f"\n✓ Recommended: {best.name} (highest confidence)")
    return best


def demonstrate_default_registry():
    """Demonstrate using the default registry."""
    print(f"\n{'='*70}")
    print("Default Registry")
    print(f"{'='*70}")
    
    # Build default registry (includes all built-in adapters)
    from agent_runtime_cockpit.adapters.registry import default_registry
    
    registry = default_registry()
    
    print(f"Default registry includes {len(registry.all())} adapters:")
    for adapter in registry.all():
        caps = adapter.capabilities()
        print(f"\n  {adapter.adapter_name} ({adapter.adapter_id})")
        print(f"    Can Run: {caps.can_run}")
        print(f"    Can Inspect: {caps.can_inspect}")
        print(f"    Can Export Workflows: {caps.can_export_workflows}")


def main():
    """Main example function."""
    print("ARC Adapter Example 5: Registry Usage")
    print("=" * 70)
    
    # Demonstrate registry basics
    registry = demonstrate_registry_basics()
    
    # Demonstrate adapter lookup
    demonstrate_adapter_lookup(registry)
    
    # Get workspace path from args or create a sample
    if len(sys.argv) > 1:
        workspace_path = Path(sys.argv[1])
        print(f"\nUsing provided workspace: {workspace_path}")
    else:
        # Create a temporary polyglot workspace
        temp_dir = tempfile.mkdtemp(prefix="arc_example_registry_")
        workspace_path = Path(temp_dir) / "polyglot_project"
        print(f"\nNo workspace provided, creating polyglot workspace...")
        create_polyglot_workspace(workspace_path)
    
    # Demonstrate detection
    detected_runtimes = demonstrate_detection(registry, workspace_path)
    
    # Demonstrate runtime selection
    selected_runtime = demonstrate_runtime_selection(detected_runtimes)
    
    # Demonstrate default registry
    demonstrate_default_registry()
    
    # Key takeaways
    print(f"\n{'='*70}")
    print("Key Takeaways:")
    print("  1. AdapterRegistry manages multiple adapters centrally")
    print("  2. register() adds adapters to the registry")
    print("  3. get() retrieves adapters by ID")
    print("  4. all() returns all registered adapters")
    print("  5. detect_all() runs detection across all adapters")
    print("  6. default_registry() provides pre-configured registry")
    print("  7. Registry enables runtime routing and selection strategies")
    print("  8. Use confidence and evidence to choose the best runtime")


if __name__ == "__main__":
    main()
