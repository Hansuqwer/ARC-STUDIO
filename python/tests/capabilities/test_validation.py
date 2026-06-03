"""Tests for CapabilityCard validation."""

from __future__ import annotations


from agent_runtime_cockpit.capabilities import (
    validate_card,
    ValidationReport,
    CapabilityCard,
    EntityType,
    RiskLevel,
    CARD_SCHEMA_VERSION,
)


class TestValidationReport:
    """Tests for ValidationReport model."""

    def test_ok_report(self):
        """Valid card produces ok=True report."""
        card = CapabilityCard(
            id="valid-card",
            name="Valid Card",
            entity_type=EntityType.IR_NODE,
        )
        report = validate_card(card)
        assert report.ok is True
        assert len(report.errors) == 0

    def test_error_count(self):
        """Error count is computed correctly."""
        report = ValidationReport(
            ok=False,
            errors=[
                {"field": "id", "message": "required", "severity": "error"},
                {"field": "name", "message": "required", "severity": "error"},
            ],
        )
        assert report.error_count == 2
        assert report.warning_count == 0

    def test_warning_count(self):
        """Warning count is computed correctly."""
        report = ValidationReport(
            ok=True,
            warnings=[
                {"field": "cost", "message": "should include cost", "severity": "warning"},
            ],
        )
        assert report.error_count == 0
        assert report.warning_count == 1


class TestValidationRules:
    """Tests for validation rules."""

    def test_r1_schema_version_mismatch(self):
        """Schema version mismatch produces error."""
        card_data = {
            "id": "test",
            "name": "Test",
            "schema_version": 999,  # Invalid version
            "entity_type": "ir_node",
        }
        card = CapabilityCard.model_validate(card_data)
        report = validate_card(card)
        assert report.ok is False
        assert any(e.field == "schema_version" for e in report.errors)

    def test_r2_missing_id(self):
        """Missing ID produces error."""
        card_data = {
            "id": "",  # Empty ID
            "name": "Test",
            "schema_version": CARD_SCHEMA_VERSION,
            "entity_type": "ir_node",
        }
        card = CapabilityCard.model_validate(card_data)
        report = validate_card(card)
        assert report.ok is False
        assert any(e.field == "id" for e in report.errors)

    def test_r3_card_hash_mismatch(self):
        """Card hash mismatch produces error."""
        from agent_runtime_cockpit.capabilities import card_hash

        card = CapabilityCard(
            id="test",
            name="Test",
            schema_version=CARD_SCHEMA_VERSION,
            entity_type=EntityType.IR_NODE,
        )
        card_hash(card)  # compute for side-effects
        card.card_hash = "0" * 64  # Wrong hash

        report = validate_card(card)
        assert report.ok is False
        assert any(e.field == "card_hash" for e in report.errors)

    def test_r4_unknown_entity_type_requires_opaque_or_review(
        self,
    ):
        """Unknown entity type must be opaque or requires_review."""
        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.UNKNOWN,
            opaque=False,
            requires_review=False,
        )
        report = validate_card(card)
        assert report.ok is False
        assert any(e.field == "entity_type" for e in report.errors)

    def test_r4_unknown_entity_type_allowed_if_opaque(self):
        """Unknown entity type is allowed if marked opaque."""
        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.UNKNOWN,
            opaque=True,
        )
        report = validate_card(card)
        assert report.ok is True

    def test_r4_unknown_entity_type_allowed_if_requires_review(self):
        """Unknown entity type is allowed if requires_review=True."""
        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.UNKNOWN,
            requires_review=True,
        )
        report = validate_card(card)
        assert report.ok is True

    def test_r5_mcp_capable_without_mcp_field(self):
        """MCP-capable card without mcp field produces error."""
        from agent_runtime_cockpit.capabilities import CapabilitySet

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.MCP_TOOL,
            capabilities=CapabilitySet(can_call_mcp=True),
        )
        report = validate_card(card)
        assert report.ok is False
        assert any(e.field == "mcp" for e in report.errors)

    def test_r5_mcp_capable_with_mcp_field_passes(self):
        """MCP-capable card with mcp field passes validation."""
        from agent_runtime_cockpit.capabilities import CapabilitySet, McpCapability

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.MCP_TOOL,
            capabilities=CapabilitySet(can_call_mcp=True),
            mcp=McpCapability(server_id="test-server"),
        )
        report = validate_card(card)
        assert report.ok is True

    def test_r6_paid_calls_without_cost_warning(self):
        """Card with can_make_paid_calls but no cost metadata produces warning."""
        from agent_runtime_cockpit.capabilities import CapabilitySet

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_make_paid_calls=True),
        )
        report = validate_card(card)
        assert report.ok is True  # Warnings don't fail validation
        assert any(w.field == "cost" for w in report.warnings)

    def test_r6_paid_calls_with_cost_passes(self):
        """Card with can_make_paid_calls and cost metadata passes."""
        from agent_runtime_cockpit.capabilities import CapabilitySet, CostCapability

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_make_paid_calls=True),
            cost=CostCapability(paid=True, budget_required=True),
        )
        report = validate_card(card)
        assert report.ok is True
        assert not any(w.field == "cost" for w in report.warnings)

    def test_r7_high_risk_without_hitl_warning(self):
        """High-risk card without HITL requirement produces warning."""
        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            risk_level=RiskLevel.HIGH,
        )
        report = validate_card(card)
        assert report.ok is True  # Warnings don't fail validation
        assert any(w.field == "trust.hitl_requirement" for w in report.warnings)

    def test_r7_critical_risk_without_audit_warning(self):
        """Critical-risk card without audit level produces warning."""
        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            risk_level=RiskLevel.CRITICAL,
        )
        report = validate_card(card)
        assert report.ok is True
        assert any(w.field == "audit.audit_level" for w in report.warnings)

    def test_r8_write_capability_without_trust_warning(self):
        """Card with can_write but no trust level produces warning."""
        from agent_runtime_cockpit.capabilities import CapabilitySet

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_write=True),
        )
        report = validate_card(card)
        assert report.ok is True
        assert any(w.field == "trust.trust_level" for w in report.warnings)

    def test_r8_network_capability_without_trust_warning(self):
        """Card with can_network but no trust level produces warning."""
        from agent_runtime_cockpit.capabilities import CapabilitySet

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_network=True),
        )
        report = validate_card(card)
        assert report.ok is True
        assert any(w.field == "trust.trust_level" for w in report.warnings)


class TestValidationIntegration:
    """Integration tests for validation."""

    def test_valid_mcp_tool_card(self, mcp_tool_card):
        """Valid MCP tool card passes all validations."""
        report = validate_card(mcp_tool_card)
        assert report.ok is True

    def test_valid_full_card(self, full_card):
        """Full card with all required fields passes validation."""
        report = validate_card(full_card)
        assert report.ok is True

    def test_multiple_warnings(self):
        """Card can have multiple warnings."""
        from agent_runtime_cockpit.capabilities import CapabilitySet

        card = CapabilityCard(
            id="test",
            name="Test",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(
                can_write=True,
                can_network=True,
                can_make_paid_calls=True,
            ),
        )
        report = validate_card(card)
        assert report.ok is True
        assert report.warning_count >= 2  # At least cost and trust warnings

    def test_fail_closed_unknown_entity_type(self):
        """Unknown entity type without marking fails validation."""
        card = CapabilityCard(
            id="unknown-test",
            name="Unknown Test",
            entity_type=EntityType.UNKNOWN,
            opaque=False,
            requires_review=False,
        )
        report = validate_card(card)
        assert report.ok is False
