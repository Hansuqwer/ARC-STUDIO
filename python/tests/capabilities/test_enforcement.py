"""Tests for capabilities/enforcement.py — Capability Card enforcement gate."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.capabilities import (
    CARD_SCHEMA_VERSION,
    AuditLevel,
    AuditProfile,
    CapabilityCard,
    CapabilitySet,
    CostCapability,
    EntityType,
    HitlRequirement,
    TrustLevel,
    TrustProfile,
)
from agent_runtime_cockpit.capabilities.enforcement import (
    DenialReason,
    enforce_card,
    enforce_card_by_id,
    resolve_mode,
)
from agent_runtime_cockpit.capabilities.signing import sign_card
from agent_runtime_cockpit.security.context import EnforcementContext


# ─── resolve_mode ─────────────────────────────────────────────────────────────


class TestResolveMode:
    def test_default_is_warn(self):
        assert resolve_mode(env={}) == "warn"

    def test_env_strict(self):
        assert resolve_mode(env={"ARC_CAPABILITIES_ENFORCE": "strict"}) == "strict"

    def test_env_off(self):
        assert resolve_mode(env={"ARC_CAPABILITIES_ENFORCE": "off"}) == "off"

    def test_cli_override_takes_priority(self):
        assert resolve_mode(env={"ARC_CAPABILITIES_ENFORCE": "strict"}, cli_override="off") == "off"

    def test_invalid_env_falls_back_to_warn(self):
        assert resolve_mode(env={"ARC_CAPABILITIES_ENFORCE": "bogus"}) == "warn"


# ─── enforce_card: mode off ───────────────────────────────────────────────────


class TestEnforceOff:
    def test_mode_off_always_allows(self, minimal_card):
        r = enforce_card(card=minimal_card, signed=None, mode="off")
        assert r.decision == "allow"
        assert r.reason == "ok"
        assert r.card_id == minimal_card.id

    def test_mode_off_no_card_allows(self):
        r = enforce_card(card=None, signed=None, mode="off")
        assert r.decision == "allow"


# ─── enforce_card: card not found ─────────────────────────────────────────────


class TestCardNotFound:
    def test_no_card_warn_mode(self):
        ctx = EnforcementContext()
        r = enforce_card(card=None, signed=None, ctx=ctx, mode="warn")
        assert r.decision == "warn"
        assert r.reason == DenialReason.CARD_NOT_FOUND.value

    def test_no_card_strict_mode(self):
        ctx = EnforcementContext()
        r = enforce_card(card=None, signed=None, ctx=ctx, mode="strict")
        assert r.decision == "deny"
        assert r.reason == DenialReason.CARD_NOT_FOUND.value


# ─── enforce_card: schema version ─────────────────────────────────────────────


class TestSchemaVersion:
    def test_mismatched_schema_version(self, minimal_card):
        bad_card = minimal_card.model_copy(update={"schema_version": 999})
        r = enforce_card(card=bad_card, signed=None, mode="warn")
        assert r.decision == "warn"
        assert r.reason == DenialReason.SCHEMA_VERSION_UNSUPPORTED.value
        assert r.details["expected"] == str(CARD_SCHEMA_VERSION)
        assert r.details["got"] == "999"


# ─── enforce_card: opaque / requires_review ───────────────────────────────────


class TestOpaqueAndReview:
    def test_opaque_card_denied(self):
        card = CapabilityCard(
            id="opaque-1",
            name="Opaque",
            entity_type=EntityType.IR_NODE,
            description="x",
            opaque=True,
        )
        r = enforce_card(card=card, signed=None, mode="strict")
        assert r.decision == "deny"
        assert r.reason == DenialReason.CARD_OPAQUE.value

    def test_requires_review_card_warned(self):
        card = CapabilityCard(
            id="review-1",
            name="Review",
            entity_type=EntityType.MCP_TOOL,
            description="x",
            requires_review=True,
        )
        r = enforce_card(card=card, signed=None, mode="warn")
        assert r.decision == "warn"
        assert r.reason == DenialReason.REQUIRES_REVIEW.value


# ─── enforce_card: signature ──────────────────────────────────────────────────


class TestSignature:
    def test_signed_valid_allows(self, minimal_card):
        signed = sign_card(minimal_card, secret_key="test-secret")
        r = enforce_card(card=None, signed=signed, mode="strict", verifier_secret_key="test-secret")
        assert r.decision == "allow"

    def test_signed_invalid_denies(self, minimal_card):
        signed = sign_card(minimal_card, secret_key="test-secret")
        r = enforce_card(
            card=None, signed=signed, mode="strict", verifier_secret_key="wrong-secret"
        )
        assert r.decision == "deny"
        assert r.reason == DenialReason.SIGNATURE_INVALID.value

    def test_signed_no_verifier_denies_strict(self, minimal_card):
        signed = sign_card(minimal_card, secret_key="test-secret")
        r = enforce_card(card=None, signed=signed, mode="strict")
        assert r.decision == "deny"
        assert r.reason == DenialReason.SIGNATURE_MISSING.value

    def test_unsigned_strict_denies(self, minimal_card):
        r = enforce_card(card=minimal_card, signed=None, mode="strict")
        assert r.decision == "deny"
        assert r.reason == DenialReason.SIGNATURE_MISSING.value

    def test_unsigned_warn_allows(self, minimal_card):
        r = enforce_card(card=minimal_card, signed=None, mode="warn")
        assert r.decision == "allow"


# ─── enforce_card: trust level ────────────────────────────────────────────────


class TestTrustLevel:
    def test_privileged_without_trust_workspace(self):
        card = CapabilityCard(
            id="priv-1",
            name="Priv",
            entity_type=EntityType.IR_NODE,
            description="x",
            trust=TrustProfile(trust_level=TrustLevel.PRIVILEGED),
        )
        ctx = EnforcementContext(trust_workspace=False)
        r = enforce_card(card=card, signed=None, ctx=ctx, mode="warn")
        assert r.decision == "warn"
        assert r.reason == DenialReason.TRUST_LEVEL_REQUIRED.value

    def test_privileged_with_trust_workspace(self):
        card = CapabilityCard(
            id="priv-2",
            name="Priv",
            entity_type=EntityType.IR_NODE,
            description="x",
            trust=TrustProfile(trust_level=TrustLevel.PRIVILEGED),
        )
        ctx = EnforcementContext(trust_workspace=True)
        r = enforce_card(card=card, signed=None, ctx=ctx, mode="warn")
        assert r.decision == "allow"


# ─── enforce_card: paid call gate ─────────────────────────────────────────────


class TestPaidCallGate:
    def test_paid_denied_without_allow_paid(self):
        card = CapabilityCard(
            id="paid-1",
            name="Paid",
            entity_type=EntityType.IR_NODE,
            description="x",
            capabilities=CapabilitySet(can_make_paid_calls=True),
        )
        ctx = EnforcementContext(allow_paid=False)
        r = enforce_card(card=card, signed=None, ctx=ctx, mode="warn")
        assert r.decision == "warn"
        assert r.reason == DenialReason.PAID_CALL_NOT_ALLOWED.value

    def test_paid_allowed_with_allow_paid(self):
        card = CapabilityCard(
            id="paid-2",
            name="Paid",
            entity_type=EntityType.IR_NODE,
            description="x",
            cost=CostCapability(paid_call_gate=True),
        )
        ctx = EnforcementContext(allow_paid=True)
        r = enforce_card(card=card, signed=None, ctx=ctx, mode="warn")
        assert r.decision == "allow"


# ─── enforce_card: audit level ────────────────────────────────────────────────


class TestAuditLevel:
    def test_audit_insufficient_warns(self):
        card = CapabilityCard(
            id="audit-1",
            name="Audit",
            entity_type=EntityType.IR_NODE,
            description="x",
            audit=AuditProfile(audit_level=AuditLevel.FULL),
        )
        r = enforce_card(card=card, signed=None, mode="warn", current_audit_mode="sha256")
        assert r.decision == "warn"
        assert r.reason == DenialReason.AUDIT_LEVEL_INSUFFICIENT.value

    def test_audit_sufficient_allows(self):
        card = CapabilityCard(
            id="audit-2",
            name="Audit",
            entity_type=EntityType.IR_NODE,
            description="x",
            audit=AuditProfile(audit_level=AuditLevel.ARC_SHA256),
        )
        r = enforce_card(card=card, signed=None, mode="warn", current_audit_mode="sha256")
        assert r.decision == "allow"


# ─── enforce_card: HITL ───────────────────────────────────────────────────────


class TestHitl:
    def test_hitl_blocking_without_gate(self):
        card = CapabilityCard(
            id="hitl-1",
            name="HITL",
            entity_type=EntityType.IR_NODE,
            description="x",
            trust=TrustProfile(hitl_requirement=HitlRequirement.BLOCKING),
        )
        r = enforce_card(card=card, signed=None, mode="warn", run_has_hitl_gate=False)
        assert r.decision == "warn"
        assert r.reason == DenialReason.HITL_REQUIRED.value

    def test_hitl_blocking_with_gate(self):
        card = CapabilityCard(
            id="hitl-2",
            name="HITL",
            entity_type=EntityType.IR_NODE,
            description="x",
            trust=TrustProfile(hitl_requirement=HitlRequirement.BLOCKING),
        )
        r = enforce_card(card=card, signed=None, mode="warn", run_has_hitl_gate=True)
        assert r.decision == "allow"


# ─── enforce_card_by_id ───────────────────────────────────────────────────────


class TestEnforceById:
    def test_card_not_in_registry(self, tmp_path):
        from agent_runtime_cockpit.capabilities import CardRegistry

        registry = CardRegistry(workspace=tmp_path)
        r = enforce_card_by_id(card_id="nonexistent", registry=registry, mode="warn")
        assert r.decision == "warn"
        assert r.reason == DenialReason.CARD_NOT_FOUND.value

    def test_card_found_in_registry(self, tmp_path, minimal_card):
        from agent_runtime_cockpit.capabilities import CardRegistry

        registry = CardRegistry(workspace=tmp_path)
        registry.save(minimal_card)
        r = enforce_card_by_id(card_id=minimal_card.id, registry=registry, mode="warn")
        assert r.decision == "allow"


# ─── EnforcementResult structure ──────────────────────────────────────────────


class TestResultStructure:
    def test_result_is_frozen(self, minimal_card):
        r = enforce_card(card=minimal_card, signed=None, mode="warn")
        with pytest.raises(Exception):
            r.decision = "deny"  # type: ignore[misc]

    def test_result_has_correlation_id(self, minimal_card):
        r = enforce_card(card=minimal_card, signed=None, mode="warn")
        assert r.correlation_id is not None
        assert len(r.correlation_id) == 12
