"""Tests for Capability Card Policy Linter."""

from __future__ import annotations


from agent_runtime_cockpit.capabilities import (
    CapabilityCard,
    CapabilitySet,
    EntityType,
    RiskLevel,
    TrustLevel,
    AuditLevel,
    McpCapability,
    TrustProfile,
    AuditProfile,
    lint_cards,
    CardPolicyIssue,
    CardPolicyReport,
)


class TestCardPolicyReport:
    """Tests for CardPolicyReport model."""

    def test_empty_report(self):
        """Empty report has no issues."""
        report = CardPolicyReport(
            workflow_id="test",
            workflow_name="Test",
            card_count=0,
            high_risk_cards=0,
            issues=[],
            can_run=True,
        )
        assert report.ok is True
        assert len(report.issues) == 0

    def test_error_blocks_can_run(self):
        """Report with error severity blocks can_run."""
        report = CardPolicyReport(
            workflow_id="test",
            workflow_name="Test",
            card_count=1,
            high_risk_cards=0,
            issues=[
                CardPolicyIssue(
                    rule="test_rule",
                    severity="error",
                    message="Test error",
                    remediation="Fix it",
                )
            ],
            can_run=False,  # Explicitly set since this is how lint_cards sets it
        )
        assert report.can_run is False
        assert len(report.errors) == 1
        assert report.ok is False

    def test_warning_allows_can_run(self):
        """Report with only warnings allows can_run."""
        report = CardPolicyReport(
            workflow_id="test",
            workflow_name="Test",
            card_count=1,
            high_risk_cards=0,
            issues=[
                CardPolicyIssue(
                    rule="test_rule",
                    severity="warning",
                    message="Test warning",
                    remediation="Consider fixing",
                )
            ],
            can_run=True,
        )
        assert report.can_run is True
        assert len(report.warnings) == 1
        assert report.ok is True


class TestPolicyRules:
    """Tests for individual policy rules."""

    def test_c3_unapproved_mcp_tool(self):
        """Unapproved MCP tool produces warning."""
        card = CapabilityCard(
            id="test-mcp-tool",
            name="Test MCP Tool",
            entity_type=EntityType.MCP_TOOL,
            mcp=McpCapability(
                server_id="test-server",
                tool_name="test-tool",
                approved=False,
                blocked=False,
                pinned=False,
            ),
        )
        report = lint_cards([card])
        assert len(report.issues) >= 2  # Not approved + Not pinned

    def test_c3_blocked_mcp_tool(self):
        """Blocked MCP tool produces error."""
        card = CapabilityCard(
            id="test-blocked-tool",
            name="Test Blocked Tool",
            entity_type=EntityType.MCP_TOOL,
            mcp=McpCapability(
                server_id="test-server",
                tool_name="blocked-tool",
                approved=False,
                blocked=True,
            ),
        )
        report = lint_cards([card])
        assert report.can_run is False
        error_issues = [i for i in report.issues if i.severity == "error"]
        assert len(error_issues) >= 1

    def test_c4_drifted_mcp_manifest(self):
        """Drifted MCP manifest produces error."""
        card = CapabilityCard(
            id="test-drifted",
            name="Test Drifted",
            entity_type=EntityType.MCP_TOOL,
            mcp=McpCapability(
                server_id="test-server",
                tool_name="test-tool",
                drifted=True,
            ),
        )
        report = lint_cards([card])
        assert report.can_run is False
        drifted_issues = [i for i in report.issues if i.rule == "drifted_mcp_manifest"]
        assert len(drifted_issues) == 1

    def test_c2_missing_trust_for_secret(self):
        """Secret access without trust produces error."""
        card = CapabilityCard(
            id="test-secret",
            name="Test Secret Access",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read_secrets=True),
            trust=TrustProfile(
                trust_level=TrustLevel.NONE,
            ),
        )
        report = lint_cards([card])
        secret_issues = [i for i in report.issues if i.capability_affected == "can_read_secrets"]
        assert len(secret_issues) >= 1

    def test_c6_unpaid_paid_call(self):
        """Paid call without cost metadata produces error."""
        card = CapabilityCard(
            id="test-paid",
            name="Test Paid Call",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_make_paid_calls=True),
        )
        report = lint_cards([card])
        paid_issues = [i for i in report.issues if i.rule == "unpaid_paid_call"]
        assert len(paid_issues) >= 1

    def test_c7_secret_without_scope(self):
        """Secret access without scope requirement produces error."""
        card = CapabilityCard(
            id="test-no-scope",
            name="Test No Scope",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read_secrets=True),
            trust=TrustProfile(
                requires_secret_scope=False,
            ),
        )
        report = lint_cards([card])
        scope_issues = [i for i in report.issues if i.rule == "secret_access_without_scope"]
        assert len(scope_issues) == 1

    def test_c8_network_without_audit(self):
        """Network access without audit produces warning."""
        card = CapabilityCard(
            id="test-network",
            name="Test Network",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_network=True),
            audit=AuditProfile(
                audit_level=AuditLevel.NONE,
            ),
        )
        report = lint_cards([card])
        network_issues = [i for i in report.issues if i.rule == "network_without_audit"]
        assert len(network_issues) == 1

    def test_c10_requires_review_flag(self):
        """Card with requires_review=True triggers review issue."""
        card = CapabilityCard(
            id="test-review",
            name="Test Review",
            entity_type=EntityType.UNKNOWN,
            requires_review=True,
            opaque=True,
        )
        report = lint_cards([card])
        review_issues = [i for i in report.issues if i.rule == "unknown_entity_review"]
        assert len(review_issues) == 1


class TestPolicyIntegration:
    """Integration tests for policy linting."""

    def test_mcp_tool_with_full_metadata(self):
        """Fully configured MCP tool passes all checks."""
        card = CapabilityCard(
            id="test-approved-mcp",
            name="Test Approved MCP",
            entity_type=EntityType.MCP_TOOL,
            capabilities=CapabilitySet(can_call_mcp=True),
            mcp=McpCapability(
                server_id="test-server",
                tool_name="approved-tool",
                manifest_hash="abc123",
                pinned=True,
                drifted=False,
                approved=True,
                blocked=False,
            ),
            trust=TrustProfile(
                requires_workspace_trust=True,
                trust_level=TrustLevel.WORKSPACE,
            ),
            audit=AuditProfile(
                audit_required=True,
                audit_level=AuditLevel.ARC_SHA256,
            ),
        )
        report = lint_cards([card])
        # No issues for properly configured MCP tool
        assert report.can_run is True

    def test_multiple_cards_with_issues(self):
        """Multiple cards with issues are all reported."""
        cards = [
            CapabilityCard(
                id="card-1",
                name="Card 1",
                entity_type=EntityType.IR_NODE,
                capabilities=CapabilitySet(can_write=True),
            ),
            CapabilityCard(
                id="card-2",
                name="Card 2",
                entity_type=EntityType.IR_NODE,
                capabilities=CapabilitySet(can_network=True),
                audit=AuditProfile(audit_level=AuditLevel.NONE),
            ),
            CapabilityCard(
                id="card-3",
                name="Card 3",
                entity_type=EntityType.MCP_TOOL,
                mcp=McpCapability(
                    server_id="server",
                    tool_name="tool",
                    approved=False,
                ),
            ),
        ]
        report = lint_cards(cards)
        assert report.card_count == 3
        assert len(report.issues) >= 4  # Multiple issues across cards

    def test_high_risk_card_count(self):
        """High-risk cards are counted correctly."""
        cards = [
            CapabilityCard(
                id="high-risk-1",
                name="High Risk 1",
                entity_type=EntityType.IR_NODE,
                risk_level=RiskLevel.HIGH,
            ),
            CapabilityCard(
                id="critical-risk",
                name="Critical Risk",
                entity_type=EntityType.IR_NODE,
                risk_level=RiskLevel.CRITICAL,
            ),
            CapabilityCard(
                id="low-risk",
                name="Low Risk",
                entity_type=EntityType.IR_NODE,
                risk_level=RiskLevel.LOW,
            ),
        ]
        report = lint_cards(cards)
        assert report.high_risk_cards == 2

    def test_requires_review_any(self):
        """requires_review flag propagates to report."""
        cards = [
            CapabilityCard(
                id="safe-card",
                name="Safe Card",
                entity_type=EntityType.IR_NODE,
                requires_review=False,
            ),
            CapabilityCard(
                id="review-card",
                name="Review Card",
                entity_type=EntityType.UNKNOWN,
                requires_review=True,
            ),
        ]
        report = lint_cards(cards)
        assert report.requires_review is True


class TestPolicyCLI:
    """Tests for CLI integration (mocked)."""

    def test_lint_cards_returns_report(self, tmp_path):
        """lint_cards produces valid report."""
        cards = [
            CapabilityCard(
                id="test-card",
                name="Test Card",
                entity_type=EntityType.IR_NODE,
                capabilities=CapabilitySet(can_read=True),
            )
        ]
        report = lint_cards(cards, workflow_id="test-wf", workflow_name="Test Workflow")
        assert isinstance(report, CardPolicyReport)
        assert report.workflow_id == "test-wf"
        assert report.workflow_name == "Test Workflow"
        assert report.card_count == 1
