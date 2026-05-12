#!/usr/bin/env python3
"""
Example 3: Workflow Inspection

This example demonstrates how to inspect a workspace and export
workflow information using adapters.

Usage:
    python 03_workflow_inspection.py [workspace_path]
"""
import sys
from pathlib import Path
import tempfile
import json

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from _adapter_loader import SwarmGraphAdapter


def create_swarmgraph_workspace_with_workflows(path: Path):
    """Create a SwarmGraph workspace with workflows."""
    path.mkdir(parents=True, exist_ok=True)
    
    # Create swarmgraph.yaml with workflow definitions
    (path / "swarmgraph.yaml").write_text("""
version: 1.0
name: Research Assistant
description: Multi-agent research and writing system

workflows:
  - id: research_workflow
    name: Research Workflow
    description: Research a topic and generate a report
    
  - id: analysis_workflow
    name: Analysis Workflow
    description: Analyze data and create visualizations
""")
    
    # Create agents directory
    agents_dir = path / "agents"
    agents_dir.mkdir(exist_ok=True)
    
    (agents_dir / "researcher.py").write_text("""
from swarmgraph import Agent

researcher = Agent(
    name="researcher",
    role="Research Specialist",
    goal="Gather comprehensive information on topics",
    backstory="Expert researcher with 10 years of experience"
)
""")
    
    (agents_dir / "writer.py").write_text("""
from swarmgraph import Agent

writer = Agent(
    name="writer",
    role="Content Writer",
    goal="Create engaging and informative content",
    backstory="Professional writer specializing in technical content"
)
""")
    
    (agents_dir / "analyst.py").write_text("""
from swarmgraph import Agent

analyst = Agent(
    name="analyst",
    role="Data Analyst",
    goal="Analyze data and extract insights",
    backstory="Data scientist with expertise in statistical analysis"
)
""")
    
    print(f"✓ Created SwarmGraph workspace with workflows at {path}")


def inspect_workspace(adapter, workspace_path: Path):
    """Inspect the workspace and display information."""
    print(f"\n{'='*70}")
    print("Workspace Inspection")
    print(f"{'='*70}")
    
    # First, detect the runtime
    detected, confidence, evidence = adapter.detect(workspace_path)
    
    if not detected:
        print(f"✗ {adapter.adapter_name} not detected in this workspace")
        return None
    
    print(f"✓ {adapter.adapter_name} detected (confidence: {confidence:.2%})")
    print(f"\nEvidence:")
    for item in evidence:
        print(f"  • {item}")
    
    # Inspect workspace
    try:
        workspace_info = adapter.inspect_workspace(workspace_path)
        print(f"\nWorkspace Information:")
        print(f"  Path: {workspace_info.workspace_path}")
        print(f"  Valid: {workspace_info.valid}")
        if workspace_info.name:
            print(f"  Name: {workspace_info.name}")
        if workspace_info.description:
            print(f"  Description: {workspace_info.description}")
        
        return workspace_info
    except NotImplementedError:
        print(f"\n⚠ {adapter.adapter_name} does not implement workspace inspection")
        return None


def export_workflows(adapter, workspace_path: Path):
    """Export workflow information from the workspace."""
    print(f"\n{'='*70}")
    print("Workflow Export")
    print(f"{'='*70}")
    
    try:
        workflows = adapter.export_workflow(workspace_path)
        
        if not workflows:
            print("No workflows found in this workspace")
            return
        
        print(f"Found {len(workflows)} workflow(s):\n")
        
        for i, workflow in enumerate(workflows, 1):
            print(f"{i}. {workflow.name}")
            print(f"   ID: {workflow.id}")
            if workflow.description:
                print(f"   Description: {workflow.description}")
            
            # Show nodes
            if workflow.nodes:
                print(f"   Nodes ({len(workflow.nodes)}):")
                for node in workflow.nodes[:5]:  # Show first 5
                    print(f"     • {node.id} ({node.type})")
                if len(workflow.nodes) > 5:
                    print(f"     ... and {len(workflow.nodes) - 5} more")
            
            # Show edges
            if workflow.edges:
                print(f"   Edges ({len(workflow.edges)}):")
                for edge in workflow.edges[:5]:  # Show first 5
                    print(f"     • {edge.source} → {edge.target}")
                if len(workflow.edges) > 5:
                    print(f"     ... and {len(workflow.edges) - 5} more")
            
            print()
        
        return workflows
    
    except NotImplementedError:
        print(f"⚠ {adapter.adapter_name} does not implement workflow export")
        return None


def export_schemas(adapter, workspace_path: Path):
    """Export schema information from the workspace."""
    print(f"\n{'='*70}")
    print("Schema Export")
    print(f"{'='*70}")
    
    try:
        schemas = adapter.export_schemas(workspace_path)
        
        if not schemas:
            print("No schemas found in this workspace")
            return
        
        print(f"Found {len(schemas)} schema(s):\n")
        
        for i, schema in enumerate(schemas, 1):
            print(f"{i}. {schema.name}")
            print(f"   ID: {schema.id}")
            if schema.description:
                print(f"   Description: {schema.description}")
            if schema.schema_type:
                print(f"   Type: {schema.schema_type}")
            
            # Show schema preview
            if schema.schema_json:
                try:
                    schema_obj = json.loads(schema.schema_json)
                    if 'properties' in schema_obj:
                        prop_count = len(schema_obj['properties'])
                        print(f"   Properties: {prop_count}")
                except:
                    pass
            
            print()
        
        return schemas
    
    except NotImplementedError:
        print(f"⚠ {adapter.adapter_name} does not implement schema export")
        return None


def show_capabilities(adapter):
    """Show what the adapter can do."""
    print(f"\n{'='*70}")
    print("Adapter Capabilities")
    print(f"{'='*70}")
    
    caps = adapter.capabilities()
    
    print(f"{adapter.adapter_name}:")
    print(f"  ✓ Can Run: {caps.can_run}")
    print(f"  {'✓' if caps.can_inspect else '✗'} Can Inspect: {caps.can_inspect}")
    print(f"  {'✓' if caps.can_export_workflows else '✗'} Can Export Workflows: {caps.can_export_workflows}")
    print(f"  {'✓' if caps.can_export_schemas else '✗'} Can Export Schemas: {caps.can_export_schemas}")
    print(f"  {'✓' if caps.can_stream_events else '✗'} Can Stream Events: {caps.can_stream_events}")


def main():
    """Main example function."""
    print("ARC Adapter Example 3: Workflow Inspection")
    print("=" * 70)
    
    # Get workspace path from args or create a sample
    if len(sys.argv) > 1:
        workspace_path = Path(sys.argv[1])
        print(f"\nUsing provided workspace: {workspace_path}")
    else:
        # Create a temporary workspace with workflows
        temp_dir = tempfile.mkdtemp(prefix="arc_example_workflows_")
        workspace_path = Path(temp_dir) / "research_project"
        print(f"\nNo workspace provided, creating sample workspace...")
        create_swarmgraph_workspace_with_workflows(workspace_path)
    
    # Initialize adapter
    adapter = SwarmGraphAdapter()
    
    # Show capabilities first
    show_capabilities(adapter)
    
    # Inspect workspace
    workspace_info = inspect_workspace(adapter, workspace_path)
    
    if workspace_info:
        # Export workflows
        workflows = export_workflows(adapter, workspace_path)
        
        # Export schemas
        schemas = export_schemas(adapter, workspace_path)
    
    # Key takeaways
    print(f"\n{'='*70}")
    print("Key Takeaways:")
    print("  1. inspect_workspace() provides high-level workspace information")
    print("  2. export_workflow() extracts workflow topology and structure")
    print("  3. export_schemas() retrieves input/output schemas")
    print("  4. Not all adapters implement all methods (check capabilities)")
    print("  5. Exported data uses standard ARC protocol schemas")


if __name__ == "__main__":
    main()
