#!/usr/bin/env python3
"""
Example 2: Multi-Adapter Detection

This example demonstrates how to use multiple adapters simultaneously
to detect all available runtimes in a workspace.

Usage:
    python 02_multi_adapter_detection.py [workspace_path]
"""
import sys
from pathlib import Path
import tempfile

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from _adapter_loader import (
    SwarmGraphAdapter, LangGraphAdapter, CrewAIAdapter, OpenAIAgentsAdapter
)


def create_mixed_workspace(path: Path):
    """Create a workspace with multiple runtime artifacts."""
    path.mkdir(parents=True, exist_ok=True)
    
    # SwarmGraph artifacts
    (path / "swarmgraph.yaml").write_text("""
version: 1.0
name: Multi-Runtime Project
""")
    
    # LangGraph artifacts
    (path / "graph.py").write_text("""
from langgraph.graph import StateGraph

def create_workflow():
    graph = StateGraph()
    graph.add_node("start", lambda x: x)
    graph.add_node("process", lambda x: x)
    graph.add_node("end", lambda x: x)
    graph.add_edge("start", "process")
    graph.add_edge("process", "end")
    return graph.compile()
""")
    
    # CrewAI artifacts
    (path / "crew.py").write_text("""
from crewai import Crew, Agent, Task

researcher = Agent(
    role="Researcher",
    goal="Research topics",
    backstory="Expert researcher"
)

task = Task(
    description="Research AI trends",
    agent=researcher
)

crew = Crew(
    agents=[researcher],
    tasks=[task]
)
""")
    
    print(f"✓ Created mixed workspace at {path}")


def detect_all_runtimes(workspace_path: Path):
    """Detect all runtimes in the workspace."""
    print(f"\n{'='*70}")
    print("Multi-Adapter Detection")
    print(f"{'='*70}")
    print(f"Workspace: {workspace_path}\n")
    
    # Initialize all adapters
    adapters = [
        SwarmGraphAdapter(),
        LangGraphAdapter(),
        CrewAIAdapter(),
        OpenAIAgentsAdapter(),
    ]
    
    # Run detection for each adapter
    results = []
    for adapter in adapters:
        detected, confidence, evidence = adapter.detect(workspace_path)
        results.append({
            'adapter': adapter,
            'detected': detected,
            'confidence': confidence,
            'evidence': evidence
        })
    
    return results


def display_results(results):
    """Display detection results in a formatted table."""
    print(f"{'Runtime':<20} {'Detected':<12} {'Confidence':<12} {'Evidence'}")
    print("-" * 70)
    
    for result in results:
        adapter = result['adapter']
        detected = "✓ Yes" if result['detected'] else "✗ No"
        confidence = f"{result['confidence']:.2%}"
        evidence_count = len(result['evidence'])
        evidence_str = f"{evidence_count} file(s)" if evidence_count > 0 else "None"
        
        print(f"{adapter.adapter_name:<20} {detected:<12} {confidence:<12} {evidence_str}")
        
        # Show evidence details for detected runtimes
        if result['detected'] and result['evidence']:
            for item in result['evidence'][:3]:  # Show first 3 items
                print(f"  {'':20}   • {item}")
            if len(result['evidence']) > 3:
                print(f"  {'':20}   ... and {len(result['evidence']) - 3} more")


def analyze_conflicts(results):
    """Analyze potential conflicts when multiple runtimes are detected."""
    detected = [r for r in results if r['detected']]
    
    if len(detected) == 0:
        print("\n⚠ No runtimes detected")
        return
    
    if len(detected) == 1:
        adapter = detected[0]['adapter']
        print(f"\n✓ Single runtime detected: {adapter.adapter_name}")
        print("  No conflicts - clear runtime choice")
        return
    
    print(f"\n⚠ Multiple runtimes detected ({len(detected)})")
    print("  This workspace contains artifacts from multiple frameworks:")
    
    for result in detected:
        adapter = result['adapter']
        print(f"    • {adapter.adapter_name} (confidence: {result['confidence']:.2%})")
    
    # Find highest confidence
    best = max(detected, key=lambda r: r['confidence'])
    print(f"\n  Recommended: {best['adapter'].adapter_name} (highest confidence)")
    print("  Note: You may need to manually select the intended runtime")


def show_capabilities(results):
    """Show capabilities for detected runtimes."""
    detected = [r for r in results if r['detected']]
    
    if not detected:
        return
    
    print(f"\n{'='*70}")
    print("Runtime Capabilities")
    print(f"{'='*70}")
    
    for result in detected:
        adapter = result['adapter']
        caps = adapter.capabilities()
        
        print(f"\n{adapter.adapter_name}:")
        print(f"  Can Run: {caps.can_run}")
        print(f"  Can Inspect: {caps.can_inspect}")
        print(f"  Can Export Workflows: {caps.can_export_workflows}")
        print(f"  Can Export Schemas: {caps.can_export_schemas}")
        print(f"  Can Stream Events: {caps.can_stream_events}")


def main():
    """Main example function."""
    print("ARC Adapter Example 2: Multi-Adapter Detection")
    print("=" * 70)
    
    # Get workspace path from args or create a sample
    if len(sys.argv) > 1:
        workspace_path = Path(sys.argv[1])
        print(f"\nUsing provided workspace: {workspace_path}")
    else:
        # Create a temporary mixed workspace
        temp_dir = tempfile.mkdtemp(prefix="arc_example_multi_")
        workspace_path = Path(temp_dir) / "mixed_project"
        print(f"\nNo workspace provided, creating mixed workspace...")
        create_mixed_workspace(workspace_path)
    
    # Detect all runtimes
    results = detect_all_runtimes(workspace_path)
    
    # Display results
    display_results(results)
    
    # Analyze conflicts
    analyze_conflicts(results)
    
    # Show capabilities
    show_capabilities(results)
    
    # Key takeaways
    print(f"\n{'='*70}")
    print("Key Takeaways:")
    print("  1. Multiple adapters can run simultaneously on the same workspace")
    print("  2. Detection is independent - each adapter uses its own heuristics")
    print("  3. Multiple runtimes may be detected in polyglot projects")
    print("  4. Confidence scores help choose the primary runtime")
    print("  5. Capability reports show what each runtime can do")


if __name__ == "__main__":
    main()
