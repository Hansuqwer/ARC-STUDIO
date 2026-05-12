#!/usr/bin/env python3
"""
Example 4: Custom Adapter

This example demonstrates how to create a custom runtime adapter
for a hypothetical framework called "AgentFlow".

Usage:
    python 04_custom_adapter.py
"""
import sys
from pathlib import Path
from typing import Any, AsyncIterator

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent_runtime_cockpit.adapters.base import RuntimeAdapter, CapabilityReport
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities
from agent_runtime_cockpit.protocol.schemas import (
    WorkspaceInfo, WorkflowInfo, SchemaInfo, RunRecord, RunEvent
)


class AgentFlowAdapter(RuntimeAdapter):
    """
    Custom adapter for the hypothetical AgentFlow framework.
    
    AgentFlow is a fictional framework that uses:
    - agentflow.json for configuration
    - flows/ directory for workflow definitions
    - .flow files for individual flows
    """
    
    @property
    def adapter_id(self) -> str:
        """Unique adapter identifier."""
        return "agentflow"
    
    @property
    def adapter_name(self) -> str:
        """Human-readable adapter name."""
        return "AgentFlow"
    
    def capabilities(self) -> RuntimeCapabilities:
        """Return capabilities for this adapter."""
        return RuntimeCapabilities(
            can_run=False,  # Not implemented yet
            can_inspect=True,
            can_export_workflows=True,
            can_export_schemas=False,
            can_stream_events=False,
        )
    
    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """
        Detect whether AgentFlow is present in the workspace.
        
        Detection signals:
        - agentflow.json (high confidence)
        - flows/ directory (medium confidence)
        - *.flow files (low confidence)
        """
        evidence = []
        confidence = 0.0
        
        # Check for agentflow.json (strongest signal)
        if (workspace / "agentflow.json").exists():
            evidence.append("agentflow.json")
            confidence += 0.7
        
        # Check for flows/ directory
        flows_dir = workspace / "flows"
        if flows_dir.exists() and flows_dir.is_dir():
            evidence.append("flows/")
            confidence += 0.2
            
            # Count .flow files
            flow_files = list(flows_dir.glob("*.flow"))
            if flow_files:
                evidence.extend([f.name for f in flow_files[:3]])
                confidence += 0.1
        
        # Check for .flow files in root
        root_flow_files = list(workspace.glob("*.flow"))
        if root_flow_files and "flows/" not in evidence:
            evidence.extend([f.name for f in root_flow_files[:2]])
            confidence += 0.1
        
        # Detected if we have any evidence
        detected = len(evidence) > 0
        
        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)
        
        return detected, confidence, evidence
    
    def inspect_workspace(self, workspace: Path) -> WorkspaceInfo:
        """Inspect the workspace and return information."""
        import json
        
        config_file = workspace / "agentflow.json"
        
        if not config_file.exists():
            return WorkspaceInfo(
                workspace_path=str(workspace),
                valid=False,
                name="Unknown",
                description="No agentflow.json found"
            )
        
        # Parse configuration
        try:
            with open(config_file) as f:
                config = json.load(f)
            
            return WorkspaceInfo(
                workspace_path=str(workspace),
                valid=True,
                name=config.get("name", "AgentFlow Project"),
                description=config.get("description", ""),
                version=config.get("version", "1.0.0")
            )
        except Exception as e:
            return WorkspaceInfo(
                workspace_path=str(workspace),
                valid=False,
                name="Invalid",
                description=f"Failed to parse agentflow.json: {e}"
            )
    
    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Export workflow information from .flow files."""
        workflows = []
        
        # Check flows/ directory
        flows_dir = workspace / "flows"
        if flows_dir.exists():
            flow_files = list(flows_dir.glob("*.flow"))
        else:
            flow_files = list(workspace.glob("*.flow"))
        
        for flow_file in flow_files:
            # Parse .flow file (simplified - real implementation would parse properly)
            workflow_id = flow_file.stem
            
            workflows.append(WorkflowInfo(
                id=workflow_id,
                name=workflow_id.replace("_", " ").title(),
                description=f"Workflow from {flow_file.name}",
                nodes=[],  # Would parse actual nodes
                edges=[],  # Would parse actual edges
            ))
        
        return workflows


def create_sample_agentflow_workspace(path: Path):
    """Create a sample AgentFlow workspace."""
    import json
    
    path.mkdir(parents=True, exist_ok=True)
    
    # Create agentflow.json
    config = {
        "name": "Customer Support Bot",
        "description": "Multi-agent customer support system",
        "version": "1.0.0",
        "agents": [
            {"name": "classifier", "role": "Classify customer queries"},
            {"name": "responder", "role": "Generate responses"},
            {"name": "escalator", "role": "Escalate complex issues"}
        ]
    }
    
    with open(path / "agentflow.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Create flows directory
    flows_dir = path / "flows"
    flows_dir.mkdir(exist_ok=True)
    
    # Create sample .flow files
    (flows_dir / "support_flow.flow").write_text("""
# AgentFlow: Customer Support Flow

start -> classifier
classifier -> responder [condition: simple]
classifier -> escalator [condition: complex]
responder -> end
escalator -> end
""")
    
    (flows_dir / "feedback_flow.flow").write_text("""
# AgentFlow: Feedback Collection Flow

start -> collector
collector -> analyzer
analyzer -> reporter
reporter -> end
""")
    
    print(f"✓ Created sample AgentFlow workspace at {path}")


def demonstrate_custom_adapter():
    """Demonstrate the custom adapter."""
    import tempfile
    
    print("ARC Adapter Example 4: Custom Adapter")
    print("=" * 70)
    
    # Create sample workspace
    temp_dir = tempfile.mkdtemp(prefix="arc_example_custom_")
    workspace_path = Path(temp_dir) / "agentflow_project"
    print("\nCreating sample AgentFlow workspace...")
    create_sample_agentflow_workspace(workspace_path)
    
    # Initialize custom adapter
    adapter = AgentFlowAdapter()
    
    print(f"\n{'='*70}")
    print("Custom Adapter Information")
    print(f"{'='*70}")
    print(f"Adapter ID: {adapter.adapter_id}")
    print(f"Adapter Name: {adapter.adapter_name}")
    
    # Show capabilities
    caps = adapter.capabilities()
    print(f"\nCapabilities:")
    print(f"  Can Run: {caps.can_run}")
    print(f"  Can Inspect: {caps.can_inspect}")
    print(f"  Can Export Workflows: {caps.can_export_workflows}")
    print(f"  Can Export Schemas: {caps.can_export_schemas}")
    print(f"  Can Stream Events: {caps.can_stream_events}")
    
    # Detect runtime
    print(f"\n{'='*70}")
    print("Detection")
    print(f"{'='*70}")
    detected, confidence, evidence = adapter.detect(workspace_path)
    print(f"Detected: {'✓ Yes' if detected else '✗ No'}")
    print(f"Confidence: {confidence:.2%}")
    print(f"Evidence: {', '.join(evidence)}")
    
    # Inspect workspace
    print(f"\n{'='*70}")
    print("Workspace Inspection")
    print(f"{'='*70}")
    workspace_info = adapter.inspect_workspace(workspace_path)
    print(f"Name: {workspace_info.name}")
    print(f"Description: {workspace_info.description}")
    print(f"Version: {workspace_info.version}")
    print(f"Valid: {workspace_info.valid}")
    
    # Export workflows
    print(f"\n{'='*70}")
    print("Workflow Export")
    print(f"{'='*70}")
    workflows = adapter.export_workflow(workspace_path)
    print(f"Found {len(workflows)} workflow(s):")
    for workflow in workflows:
        print(f"  • {workflow.name} (ID: {workflow.id})")
    
    # Key takeaways
    print(f"\n{'='*70}")
    print("Key Takeaways:")
    print("  1. Custom adapters extend RuntimeAdapter base class")
    print("  2. Must implement: adapter_id, adapter_name, capabilities(), detect()")
    print("  3. Optional methods: inspect_workspace(), export_workflow(), etc.")
    print("  4. Detection should use real evidence, not hardcoded values")
    print("  5. Capabilities must be honest - no false positives")
    print("  6. Custom adapters integrate seamlessly with ARC registry")


def show_adapter_interface():
    """Show the adapter interface that must be implemented."""
    print("\n" + "=" * 70)
    print("RuntimeAdapter Interface")
    print("=" * 70)
    print("""
Required Properties:
  • adapter_id: str          - Unique identifier (e.g., 'agentflow')
  • adapter_name: str        - Human-readable name (e.g., 'AgentFlow')

Required Methods:
  • capabilities() -> RuntimeCapabilities
      Return honest capabilities for this adapter
  
  • detect(workspace: Path) -> tuple[bool, float, list[str]]
      Detect runtime presence, return (detected, confidence, evidence)

Optional Methods (raise NotImplementedError if not supported):
  • inspect_workspace(workspace: Path) -> WorkspaceInfo
  • export_workflow(workspace: Path) -> list[WorkflowInfo]
  • export_schemas(workspace: Path) -> list[SchemaInfo]
  • run_workflow(workflow_id: str, inputs: dict) -> RunRecord
  • stream_events(run_id: str) -> AsyncIterator[RunEvent]
  • get_run(run_id: str) -> RunRecord
  • list_runs(workspace: Path) -> list[RunRecord]

Implementation Rules:
  1. capabilities() must never lie (no false positives)
  2. detect() must check for actual files, not just claim success
  3. Unsupported operations must raise NotImplementedError
  4. All file operations must handle missing/corrupt files gracefully
  5. Evidence must list actual file names or config keys found
""")


if __name__ == "__main__":
    demonstrate_custom_adapter()
    show_adapter_interface()
