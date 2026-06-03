"""Tests for CapabilityCard models."""

from __future__ import annotations


from agent_runtime_cockpit.capabilities import (
    CARD_SCHEMA_VERSION,
    CapabilityCard,
    CapabilitySet,
    EntityType,
    RiskLevel,
    TrustLevel,
    AuditLevel,
    HitlRequirement,
    ApprovalMode,
    CostCapability,
    TrustProfile,
    AuditProfile,
    ReplayProfile,
    PermissionRequirement,
    DataAccess,
    DataSensitivity,
    SideEffectProfile,
    CapabilityProvenance,
)


class TestCapabilitySet:
    """Tests for CapabilitySet model."""

    def test_defaults_are_false(self):
        """All capability flags default to False for fail-closed behavior."""
        caps = CapabilitySet()
        assert caps.can_read is False
        assert caps.can_write is False
        assert caps.can_delete is False
        assert caps.can_execute is False
        assert caps.can_network is False
        assert caps.can_call_tools is False
        assert caps.can_call_mcp is False
        assert caps.can_call_models is False
        assert caps.can_read_secrets is False
        assert caps.can_make_paid_calls is False
        assert caps.can_request_hitl is False
        assert caps.can_replay is False

    def test_set_capabilities(self):
        """Can set capability flags."""
        caps = CapabilitySet(
            can_read=True,
            can_write=True,
            can_network=True,
        )
        assert caps.can_read is True
        assert caps.can_write is True
        assert caps.can_network is True


class TestCapabilityCard:
    """Tests for CapabilityCard model."""

    def test_minimal_card(self, minimal_card: CapabilityCard):
        """Minimal card has required fields."""
        assert minimal_card.id == "test-card-001"
        assert minimal_card.name == "Test Card"
        assert minimal_card.entity_type == EntityType.IR_NODE
        assert minimal_card.schema_version == CARD_SCHEMA_VERSION

    def test_full_card(self, full_card: CapabilityCard):
        """Full card has all fields populated."""
        assert full_card.capabilities.can_read is True
        assert full_card.capabilities.can_write is True
        assert full_card.capabilities.can_network is True
        assert full_card.trust.requires_workspace_trust is True
        assert full_card.audit.audit_required is True
        assert full_card.replay.replayable is True

    def test_enums_are_serializable(self):
        """Enum values serialize correctly to JSON."""
        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.MCP_TOOL,
            risk_level=RiskLevel.HIGH,
            trust=TrustProfile(trust_level=TrustLevel.WORKSPACE),
            audit=AuditProfile(audit_level=AuditLevel.ARC_SHA256),
        )
        json_str = card.model_dump_json()
        assert "mcp_tool" in json_str
        assert "high" in json_str
        assert "workspace" in json_str
        assert "arc_sha256" in json_str

    def test_forward_compat_extra_fields(self):
        """Unknown fields are ignored for forward compatibility."""
        card_data = {
            "id": "test",
            "name": "Test",
            "schema_version": CARD_SCHEMA_VERSION,
            "unknown_field": "should_be_ignored",
            "nested": {"unknown": "value"},
        }
        card = CapabilityCard.model_validate(card_data)
        assert card.id == "test"
        assert "unknown_field" not in card.model_dump()

    def test_mcp_capability(self, mcp_tool_card: CapabilityCard):
        """MCP tool cards have MCP capability."""
        assert mcp_tool_card.mcp is not None
        assert mcp_tool_card.mcp.server_id == "test-server"
        assert mcp_tool_card.mcp.tool_name == "write_file"
        assert mcp_tool_card.mcp.approved is True
        assert mcp_tool_card.mcp.blocked is False
        assert mcp_tool_card.risk_level == RiskLevel.HIGH

    def test_opaque_card(self):
        """Opaque cards are allowed for unknown entity types."""
        card = CapabilityCard(
            id="opaque-test",
            name="Opaque Test",
            entity_type=EntityType.UNKNOWN,
            opaque=True,
            requires_review=True,
        )
        assert card.opaque is True
        assert card.requires_review is True

    def test_cost_capability(self):
        """Cost capability is properly structured."""
        card = CapabilityCard(
            id="paid-card",
            name="Paid Card",
            cost=CostCapability(
                paid=True,
                budget_required=True,
                max_cost_usd=0.01,
                max_tokens=1000,
                provider="openai",
                paid_call_gate=True,
            ),
        )
        assert card.cost is not None
        assert card.cost.paid is True
        assert card.cost.budget_required is True
        assert card.cost.max_cost_usd == 0.01
        assert card.cost.paid_call_gate is True


class TestEnums:
    """Tests for enum values."""

    def test_entity_type_values(self):
        """All entity types are valid."""
        for entity_type in EntityType:
            card = CapabilityCard(
                id=f"test-{entity_type.value}",
                name="Test",
                entity_type=entity_type,
            )
            assert card.entity_type == entity_type

    def test_risk_level_values(self):
        """All risk levels are valid."""
        for level in RiskLevel:
            card = CapabilityCard(
                id=f"test-{level.value}",
                name="Test",
                risk_level=level,
            )
            assert card.risk_level == level

    def test_trust_level_values(self):
        """All trust levels are valid."""
        trust = TrustProfile(trust_level=TrustLevel.PRIVILEGED)
        assert trust.trust_level == TrustLevel.PRIVILEGED

    def test_hitl_requirement_values(self):
        """All HITL requirements are valid."""
        trust = TrustProfile(hitl_requirement=HitlRequirement.REQUIRED)
        assert trust.hitl_requirement == HitlRequirement.REQUIRED

    def test_approval_mode_values(self):
        """All approval modes are valid."""
        perm = PermissionRequirement(
            kind="test",
            approval_mode=ApprovalMode.MANUAL_APPROVAL,
        )
        assert perm.approval_mode == ApprovalMode.MANUAL_APPROVAL


class TestSubModels:
    """Tests for sub-models."""

    def test_permission_requirement(self):
        """Permission requirements are properly structured."""
        perm = PermissionRequirement(
            kind="fs.write",
            required=True,
            reason="Write to workspace",
            scope="workspace",
            default_decision="deny",
        )
        assert perm.kind == "fs.write"
        assert perm.required is True
        assert perm.default_decision == "deny"

    def test_data_access(self):
        """Data access is properly structured."""
        access = DataAccess(
            reads=["workspace://*.py"],
            writes=["workspace://output/"],
            sensitivity=DataSensitivity.CONFIDENTIAL,
            scope="workspace",
            redaction_required=True,
        )
        assert len(access.reads) == 1
        assert len(access.writes) == 1
        assert access.sensitivity == DataSensitivity.CONFIDENTIAL

    def test_side_effect_profile(self):
        """Side effect profiles are properly structured."""
        effect = SideEffectProfile(
            kind="write",
            target="workspace://output/",
            reversible=False,
            idempotent=True,
            requires_hitl=False,
            requires_audit=True,
            requires_trust=True,
        )
        assert effect.kind == "write"
        assert effect.requires_audit is True
        assert effect.requires_trust is True

    def test_replay_profile(self):
        """Replay profiles are properly structured."""
        replay = ReplayProfile(
            replayable=True,
            deterministic=False,
            requires_recorded_inputs=True,
            non_replayable_reasons=["model_call_non_deterministic"],
        )
        assert replay.replayable is True
        assert replay.deterministic is False
        assert len(replay.non_replayable_reasons) == 1

    def test_capability_provenance(self):
        """Provenance is properly structured."""
        prov = CapabilityProvenance(
            source_type="ir_node",
            ir_graph_id="test-graph",
            ir_graph_hash="hash123",
            ir_node_id="test-node",
        )
        assert prov.source_type == "ir_node"
        assert prov.ir_graph_id == "test-graph"
        assert prov.ir_node_id == "test-node"
