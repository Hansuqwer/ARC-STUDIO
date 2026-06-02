"""ARC Action Simulator — static dry-run prediction for SwarmGraph IR.

Pure static analysis. Never executes workflows, calls models, invokes tools,
starts MCP servers, makes network connections, or writes files.

Usage:
    from agent_runtime_cockpit.simulation import simulate_graph, SimulationConfig
    report = simulate_graph(ir_graph, SimulationConfig(workspace=str(path)))
"""

from .models import (
    EvalRecommendationRef,
    PolicySimulationSummary,
    SimulatedCost,
    SimulatedEdge,
    SimulatedGate,
    SimulatedMcp,
    SimulatedNode,
    SimulatedSideEffect,
    SimulatedToolCall,
    SimulationConfig,
    SimulationReport,
    SimulationSummary,
    SimulationWarning,
    SIMULATION_SCHEMA_VERSION,
)
from .simulator import simulate_graph

__all__ = [
    "simulate_graph",
    "SimulationConfig",
    "SimulationReport",
    "SimulationSummary",
    "SimulatedNode",
    "SimulatedEdge",
    "SimulatedSideEffect",
    "SimulatedToolCall",
    "SimulatedGate",
    "SimulatedMcp",
    "SimulatedCost",
    "PolicySimulationSummary",
    "SimulationWarning",
    "EvalRecommendationRef",
    "SIMULATION_SCHEMA_VERSION",
]
