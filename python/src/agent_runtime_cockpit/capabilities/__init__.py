"""Capability Cards — typed, versioned, hashable capability manifests.

A Capability Card is a deterministic, versioned, hashable metadata document that
describes what every runtime, adapter, workflow, agent, MCP tool, model call, and
SwarmGraph IR node can read, write, call, spend, expose, remember, and execute.

Package name is ``capabilities`` (NOT a submodule of
``agent_runtime_cockpit.swarmgraph``) to avoid the SwarmGraph bridge
MetaPathFinder, which rewrites ``agent_runtime_cockpit.swarmgraph.*`` to the
top-level ``swarmgraph`` SDK distribution.

Usage:
    from agent_runtime_cockpit.capabilities import (
        CapabilityCard,
        card_from_ir_graph,
        cards_from_ir_graph,
        cards_from_mcp_registry,
        validate_card,
        CardRegistry,
    )

    # Generate cards from IR
    from agent_runtime_cockpit.swarmgraph_ir import from_json
    graph = from_json(ir_json)
    cards = cards_from_ir_graph(graph)

    # Generate cards from MCP registry
    from agent_runtime_cockpit.capabilities import cards_from_mcp_registry
    mcp_cards = cards_from_mcp_registry(workspace=Path.cwd())

    # Validate a card
    report = validate_card(card)
    if not report.ok:
        print(f"Validation failed: {report.errors}")

    # Save cards to registry
    registry = CardRegistry(workspace=Path.cwd())
    for card in cards:
        path = registry.save(card)
        print(f"Saved: {path}")
"""

from __future__ import annotations

from .hashing import card_hash, canonical_json, verify_hash
from .models import (
    CARD_SCHEMA_VERSION,
    ApprovalMode,
    AuditLevel,
    AuditProfile,
    CapabilityCard,
    CapabilityProvenance,
    CapabilitySet,
    CostCapability,
    DataAccess,
    DataSensitivity,
    EntityType,
    HitlRequirement,
    McpCapability,
    PermissionRequirement,
    ReplayProfile,
    RiskLevel,
    SideEffectProfile,
    TrustLevel,
    TrustProfile,
)
from .redaction import is_safe_card, redact_card, redact_string
from .registry import CardRegistry, create_registry
from .validation import ValidationError, ValidationReport, validate_card, validate_card_json

# IR converters
from .from_ir import card_from_ir_graph, card_from_ir_node, cards_from_ir_graph

# MCP converters
from .from_mcp import (
    card_from_mcp_server,
    card_from_mcp_tool,
    cards_from_mcp_registry,
    cards_from_mcp_tools,
)

# Adapter converters
from .from_adapters import (
    card_from_adapter,
    card_from_capability_report,
    cards_from_adapters,
)

# Policy linter
from .policy import (
    lint_cards,
    lint_ir_cards,
    lint_registry,
    CardPolicyIssue,
    CardPolicyReport,
)

# Signing and verification
from .signing import (
    sign_card,
    verify_card,
    sign_card_file,
    verify_card_file,
    generate_secret_key,
    generate_ecdsa_keypair,
    SignatureAlgorithm,
    CardSignature,
    SignedCapabilityCard,
)

__all__ = [
    # Schema version
    "CARD_SCHEMA_VERSION",
    # Models
    "EntityType",
    "TrustLevel",
    "AuditLevel",
    "HitlRequirement",
    "ApprovalMode",
    "RiskLevel",
    "DataSensitivity",
    "CapabilitySet",
    "DataAccess",
    "SideEffectProfile",
    "PermissionRequirement",
    "McpCapability",
    "CostCapability",
    "TrustProfile",
    "AuditProfile",
    "ReplayProfile",
    "CapabilityProvenance",
    "CapabilityCard",
    # Hashing
    "card_hash",
    "canonical_json",
    "verify_hash",
    # Redaction
    "redact_card",
    "redact_string",
    "is_safe_card",
    # Registry
    "CardRegistry",
    "create_registry",
    # Validation
    "validate_card",
    "validate_card_json",
    "ValidationError",
    "ValidationReport",
    # IR converters
    "card_from_ir_node",
    "card_from_ir_graph",
    "cards_from_ir_graph",
    # MCP converters
    "card_from_mcp_server",
    "card_from_mcp_tool",
    "cards_from_mcp_registry",
    "cards_from_mcp_tools",
    # Adapter converters
    "card_from_adapter",
    "card_from_capability_report",
    "cards_from_adapters",
    # Policy linter
    "lint_cards",
    "lint_ir_cards",
    "lint_registry",
    "CardPolicyIssue",
    "CardPolicyReport",
    # Signing and verification
    "sign_card",
    "verify_card",
    "sign_card_file",
    "verify_card_file",
    "generate_secret_key",
    "generate_ecdsa_keypair",
    "SignatureAlgorithm",
    "CardSignature",
    "SignedCapabilityCard",
]
