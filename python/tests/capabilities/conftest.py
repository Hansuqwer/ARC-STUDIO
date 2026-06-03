"""Test fixtures for capabilities tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.capabilities import (
    CARD_SCHEMA_VERSION,
    CapabilityCard,
    CapabilityProvenance,
    CapabilitySet,
    EntityType,
    RiskLevel,
    TrustProfile,
    AuditProfile,
    ReplayProfile,
    McpCapability,
    CostCapability,
)


@pytest.fixture
def minimal_card() -> CapabilityCard:
    """Create a minimal valid CapabilityCard."""
    return CapabilityCard(
        id="test-card-001",
        name="Test Card",
        entity_type=EntityType.IR_NODE,
        description="A minimal test card",
        schema_version=CARD_SCHEMA_VERSION,
    )


@pytest.fixture
def full_card() -> CapabilityCard:
    """Create a full-featured CapabilityCard with all fields."""
    caps = CapabilitySet(
        can_read=True,
        can_write=True,
        can_network=True,
        can_call_mcp=True,
        can_make_paid_calls=True,
        can_read_secrets=False,
    )
    trust = TrustProfile(
        requires_workspace_trust=True,
        trust_level="workspace",
        hitl_requirement="none",
    )
    audit = AuditProfile(
        audit_required=True,
        audit_level="arc_sha256",
        receipt_required=True,
    )
    replay = ReplayProfile(replayable=True, deterministic=False)

    provenance = CapabilityProvenance(
        source_type="ir_node",
        ir_graph_id="test-graph",
        ir_graph_hash="abc123",
        ir_node_id="test-node",
    )

    mcp = McpCapability(
        server_id="test-mcp-server",
        tool_name=None,
        pinned=True,
        drifted=False,
        approved=True,
        blocked=False,
        risk_level=RiskLevel.LOW,
    )

    cost = CostCapability(
        paid=True,
        budget_required=True,
        max_cost_usd=0.01,
        provider="openai",
    )

    return CapabilityCard(
        id="test-full-card",
        name="Full Test Card",
        entity_type=EntityType.IR_NODE,
        description="A full-featured test card",
        capabilities=caps,
        mcp=mcp,
        cost=cost,
        trust=trust,
        audit=audit,
        replay=replay,
        provenance=provenance,
        risk_level=RiskLevel.MEDIUM,
        metadata={"test": "data"},
    )


@pytest.fixture
def mcp_tool_card() -> CapabilityCard:
    """Create a CapabilityCard for an MCP tool."""
    from agent_runtime_cockpit.capabilities import McpCapability, SideEffectProfile

    caps = CapabilitySet(can_call_mcp=True, can_write=True, can_network=True)
    mcp = McpCapability(
        server_id="test-server",
        tool_name="write_file",
        manifest_hash="hash123",
        pinned=True,
        drifted=False,
        approved=True,
        blocked=False,
        risk_level=RiskLevel.HIGH,
        risk_flags=["can_write", "can_network"],
    )
    side_effects = [
        SideEffectProfile(kind="write", requires_trust=True),
        SideEffectProfile(kind="network", requires_trust=True),
    ]

    return CapabilityCard(
        id="mcp-tool-test-server-write_file",
        name="write_file",
        entity_type=EntityType.MCP_TOOL,
        description="MCP tool that writes files",
        capabilities=caps,
        mcp=mcp,
        side_effects=side_effects,
        risk_level=RiskLevel.HIGH,
        requires_review=True,
    )


@pytest.fixture
def ir_graph_fixture_path(tmp_path: Path) -> Path:
    """Create a test IR graph JSON file."""
    ir_data = {
        "ir_version": 1,
        "id": "test-graph",
        "name": "Test Graph",
        "runtime": "native",
        "provenance": {
            "adapter_id": "native",
            "runtime": "native",
            "exported_via": "export_workflow",
        },
        "nodes": [
            {
                "id": "__start__",
                "label": "START",
                "kind": "start",
                "risk": {"level": "low", "score": 0.0, "signals": [], "source": "heuristic"},
                "side_effects": [],
            },
            {
                "id": "agent",
                "label": "Agent",
                "kind": "agent",
                "risk": {
                    "level": "medium",
                    "score": 0.5,
                    "signals": ["model_call"],
                    "source": "heuristic",
                },
                "side_effects": [{"kind": "paid_call", "paid": True}],
                "model_call": {"provider": "openai", "model": "gpt-4", "paid": True},
            },
            {
                "id": "__end__",
                "label": "END",
                "kind": "end",
                "risk": {"level": "low", "score": 0.0, "signals": [], "source": "heuristic"},
                "side_effects": [],
            },
        ],
        "edges": [
            {"id": "e1", "from_node": "__start__", "to_node": "agent"},
            {"id": "e2", "from_node": "agent", "to_node": "__end__"},
        ],
        "entry_points": ["__start__"],
        "risk": {"level": "medium", "score": 0.5, "signals": [], "source": "heuristic"},
        "consensus": {"source": "default"},
        "graph_hash": "abc123def456",
    }

    path = tmp_path / "test-graph.ir.json"
    path.write_text(json.dumps(ir_data))
    return path
