#!/usr/bin/env python3
"""
Example 1: Basic Runtime Detection

This example demonstrates how to use a single adapter to detect
whether a specific runtime is present in a workspace.

Usage:
    python 01_basic_detection.py [workspace_path]
"""
import sys
from pathlib import Path
import tempfile

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from _adapter_loader import SwarmGraphAdapter, LangGraphAdapter, CrewAIAdapter


def create_sample_swarmgraph_workspace(path: Path):
    """Create a sample SwarmGraph workspace for demonstration."""
    path.mkdir(parents=True, exist_ok=True)
    
    # Create swarmgraph.yaml
    (path / "swarmgraph.yaml").write_text("""
version: 1.0
name: Sample SwarmGraph Project
description: A sample project for demonstration

agents:
  - name: researcher
    role: Research Agent
    goal: Gather information
  
  - name: writer
    role: Writing Agent
    goal: Create content
""")
    
    # Create agents directory
    agents_dir = path / "agents"
    agents_dir.mkdir(exist_ok=True)
    
    (agents_dir / "researcher.py").write_text("""
from swarmgraph import Agent

researcher = Agent(
    name="researcher",
    role="Research Agent",
    goal="Gather and analyze information"
)
""")
    
    print(f"✓ Created sample SwarmGraph workspace at {path}")


def detect_runtime(adapter, workspace_path: Path):
    """Detect a runtime in the given workspace."""
    print(f"\n{'='*60}")
    print(f"Detecting {adapter.adapter_name}")
    print(f"{'='*60}")
    
    # Run detection
    detected, confidence, evidence = adapter.detect(workspace_path)
    
    # Display results
    print(f"Workspace: {workspace_path}")
    print(f"Detected: {'✓ Yes' if detected else '✗ No'}")
    print(f"Confidence: {confidence:.2%}")
    
    if evidence:
        print(f"Evidence found:")
        for item in evidence:
            print(f"  • {item}")
    else:
        print("No evidence found")
    
    # Get capability report
    if detected:
        report = adapter.capability_report(workspace_path)
        print(f"\nCapability Report:")
        print(f"  Runtime ID: {report.runtime_id}")
        print(f"  Can Run: {report.can_run}")
        print(f"  Availability: {report.availability}")
        if report.reason:
            print(f"  Reason: {report.reason}")
    
    return detected, confidence


def main():
    """Main example function."""
    print("ARC Adapter Example 1: Basic Runtime Detection")
    print("=" * 60)
    
    # Get workspace path from args or create a sample
    if len(sys.argv) > 1:
        workspace_path = Path(sys.argv[1])
        print(f"\nUsing provided workspace: {workspace_path}")
    else:
        # Create a temporary sample workspace
        temp_dir = tempfile.mkdtemp(prefix="arc_example_")
        workspace_path = Path(temp_dir) / "sample_project"
        print(f"\nNo workspace provided, creating sample workspace...")
        create_sample_swarmgraph_workspace(workspace_path)
    
    # Initialize adapters
    swarmgraph_adapter = SwarmGraphAdapter()
    langgraph_adapter = LangGraphAdapter()
    crewai_adapter = CrewAIAdapter()
    
    # Detect each runtime
    results = []
    for adapter in [swarmgraph_adapter, langgraph_adapter, crewai_adapter]:
        detected, confidence = detect_runtime(adapter, workspace_path)
        results.append((adapter.adapter_name, detected, confidence))
    
    # Summary
    print(f"\n{'='*60}")
    print("Detection Summary")
    print(f"{'='*60}")
    
    detected_runtimes = [name for name, detected, _ in results if detected]
    
    if detected_runtimes:
        print(f"✓ Detected {len(detected_runtimes)} runtime(s):")
        for name, detected, confidence in results:
            if detected:
                print(f"  • {name} (confidence: {confidence:.2%})")
    else:
        print("✗ No runtimes detected in this workspace")
    
    print("\nKey Takeaways:")
    print("  1. Each adapter implements the detect() method")
    print("  2. Detection returns (detected, confidence, evidence)")
    print("  3. Confidence is a float between 0.0 and 1.0")
    print("  4. Evidence lists the files/patterns that triggered detection")
    print("  5. Capability reports provide detailed runtime information")


if __name__ == "__main__":
    main()
