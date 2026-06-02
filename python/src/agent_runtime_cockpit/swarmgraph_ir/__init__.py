"""SwarmGraph IR — typed, inspectable, policy-aware intermediate representation.

A normalization & analysis layer over ARC runtime adapters. NOT a runtime engine.

Package name is ``swarmgraph_ir`` (not a submodule of
``agent_runtime_cockpit.swarmgraph``) to avoid the SwarmGraph bridge
MetaPathFinder, which rewrites ``agent_runtime_cockpit.swarmgraph.*`` to the
top-level ``swarmgraph`` SDK distribution.
"""

from __future__ import annotations

from .compiler import CompileResult, compile_from_json, compile_workflow
from .exporters import from_dict, from_json, to_dict, to_json, to_workflow_info
from .hashing import canonical_json, graph_hash
from .models import (
    IR_SCHEMA_VERSION,
    IRAdapterProvenance,
    IRAuditBoundary,
    IRBudget,
    IRCapabilityRequirement,
    IRConsensusHint,
    IREdge,
    IRGraph,
    IRHumanGate,
    IRMcpToolRef,
    IRModelCall,
    IRNode,
    IRNodeKind,
    IRReplayMarker,
    IRRisk,
    IRSideEffect,
    IRToolRef,
    IRValidationReport,
    SideEffectKind,
)
from .validation import validate_graph

__all__ = [
    "IR_SCHEMA_VERSION",
    # models
    "IRGraph",
    "IRNode",
    "IREdge",
    "IRToolRef",
    "IRMcpToolRef",
    "IRModelCall",
    "IRHumanGate",
    "IRConsensusHint",
    "IRRisk",
    "IRCapabilityRequirement",
    "IRSideEffect",
    "IRBudget",
    "IRAuditBoundary",
    "IRReplayMarker",
    "IRAdapterProvenance",
    "IRValidationReport",
    "IRNodeKind",
    "SideEffectKind",
    # compiler
    "compile_workflow",
    "compile_from_json",
    "CompileResult",
    # validation
    "validate_graph",
    # exporters
    "to_workflow_info",
    "to_json",
    "from_json",
    "to_dict",
    "from_dict",
    # hashing
    "graph_hash",
    "canonical_json",
]
