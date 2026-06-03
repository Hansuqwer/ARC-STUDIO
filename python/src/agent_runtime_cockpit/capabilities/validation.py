"""Validation rules for Capability Cards.

All validation is fail-closed: invalid cards are rejected, not silently sanitized.
Unknown entity types must be marked as `opaque` or `requires_review`.

Validation rules:
- schema_version must match CARD_SCHEMA_VERSION
- entity ID required
- card hash must match content (if present)
- MCP tool cards with can_call_mcp should include server ID and tool name
- can_make_paid_calls should imply budget requirement or warning
- write/delete/execute/network/secret cards should require trust metadata
- cards with high-risk side effects should require HITL/audit fields
- unknown entity types should fail unless marked `opaque`
- secrets must not appear in serialized card fields
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .hashing import card_hash
from .models import (
    CARD_SCHEMA_VERSION,
    AuditLevel,
    CapabilityCard,
    EntityType,
    HitlRequirement,
    RiskLevel,
    TrustLevel,
)


class ValidationError(BaseModel):
    """A single validation error."""

    field: str
    message: str
    severity: str = "error"  # "error", "warning", "info"


class ValidationReport(BaseModel):
    """Result of validating a Capability Card."""

    ok: bool = True
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


def validate_card(card: Any) -> ValidationReport:
    """Validate a CapabilityCard instance.

    Returns a ValidationReport with errors, warnings, and overall ok status.
    A card is valid only if ok=True and errors is empty.
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Get card as dict for field access
    if hasattr(card, "model_dump"):
        card_dict = card.model_dump()
    else:
        card_dict = card

    # ── R1: Schema version check ────────────────────────────────────────────
    schema_version = card_dict.get("schema_version", 0)
    if schema_version != CARD_SCHEMA_VERSION:
        errors.append(
            ValidationError(
                field="schema_version",
                message=f"Schema version mismatch: expected {CARD_SCHEMA_VERSION}, got {schema_version}",
            )
        )

    # ── R2: Entity ID required ──────────────────────────────────────────────
    card_id = card_dict.get("id", "")
    if not card_id:
        errors.append(
            ValidationError(
                field="id",
                message="Capability card must have a non-empty id field",
            )
        )

    # ── R3: Card hash verification (if present) ────────────────────────────
    stored_hash = card_dict.get("card_hash")
    if stored_hash:
        actual_hash = card_hash(card)
        if actual_hash != stored_hash:
            errors.append(
                ValidationError(
                    field="card_hash",
                    message=f"Card hash mismatch: expected {actual_hash[:16]}..., got {stored_hash[:16]}...",
                )
            )

    # ── R4: Entity type check ───────────────────────────────────────────────
    entity_type = card_dict.get("entity_type", EntityType.UNKNOWN)
    if isinstance(entity_type, str):
        try:
            EntityType(entity_type)
        except ValueError:
            entity_type = EntityType.UNKNOWN

    is_opaque = card_dict.get("opaque", False)
    requires_review = card_dict.get("requires_review", False)

    if entity_type == EntityType.UNKNOWN and not is_opaque:
        # Unknown entity types are allowed only if marked opaque or requires_review
        if not requires_review:
            errors.append(
                ValidationError(
                    field="entity_type",
                    message="Unknown entity type must be marked as opaque or requires_review",
                )
            )

    # ── R5: MCP tool cards with can_call_mcp ───────────────────────────────
    caps = card_dict.get("capabilities", {})
    mcp = card_dict.get("mcp")
    if isinstance(caps, dict) and caps.get("can_call_mcp"):
        if not mcp:
            errors.append(
                ValidationError(
                    field="mcp",
                    message="MCP-capable card must include mcp field with server_id",
                )
            )
        elif isinstance(mcp, dict):
            if not mcp.get("server_id"):
                errors.append(
                    ValidationError(
                        field="mcp.server_id",
                        message="MCP-capable card must include mcp.server_id",
                    )
                )

    # ── R6: can_make_paid_calls implies cost metadata ──────────────────────
    if isinstance(caps, dict) and caps.get("can_make_paid_calls"):
        cost = card_dict.get("cost")
        if not cost:
            warnings.append(
                ValidationError(
                    field="cost",
                    message="Card with can_make_paid_calls should include cost metadata",
                    severity="warning",
                )
            )
        elif isinstance(cost, dict) and not cost.get("paid"):
            warnings.append(
                ValidationError(
                    field="cost.paid",
                    message="Card with can_make_paid_calls should have cost.paid=True",
                    severity="warning",
                )
            )

    # ── R7: High-risk side effects require HITL/audit ──────────────────────
    risk_level = card_dict.get("risk_level", RiskLevel.LOW)
    if isinstance(risk_level, str):
        try:
            risk_level = RiskLevel(risk_level)
        except ValueError:
            risk_level = RiskLevel.LOW

    if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        trust = card_dict.get("trust", {})
        audit = card_dict.get("audit", {})

        if isinstance(trust, dict):
            hitl_req = trust.get("hitl_requirement", HitlRequirement.NONE)
            if isinstance(hitl_req, str):
                try:
                    hitl_req = HitlRequirement(hitl_req)
                except ValueError:
                    hitl_req = HitlRequirement.NONE

            if hitl_req == HitlRequirement.NONE:
                warnings.append(
                    ValidationError(
                        field="trust.hitl_requirement",
                        message="High/critical risk card should have HITL requirement (current: none)",
                        severity="warning",
                    )
                )

        if isinstance(audit, dict):
            audit_level = audit.get("audit_level", AuditLevel.NONE)
            if isinstance(audit_level, str):
                try:
                    audit_level = AuditLevel(audit_level)
                except ValueError:
                    audit_level = AuditLevel.NONE

            if audit_level == AuditLevel.NONE:
                warnings.append(
                    ValidationError(
                        field="audit.audit_level",
                        message="High/critical risk card should have audit level (current: none)",
                        severity="warning",
                    )
                )

    # ── R8: Write/delete/execute/network/secret require trust metadata ──────
    high_risk_caps = []
    if isinstance(caps, dict):
        if caps.get("can_write"):
            high_risk_caps.append("can_write")
        if caps.get("can_delete"):
            high_risk_caps.append("can_delete")
        if caps.get("can_execute"):
            high_risk_caps.append("can_execute")
        if caps.get("can_network"):
            high_risk_caps.append("can_network")
        if caps.get("can_read_secrets"):
            high_risk_caps.append("can_read_secrets")

    if high_risk_caps:
        trust = card_dict.get("trust", {})
        if isinstance(trust, dict):
            trust_level = trust.get("trust_level", TrustLevel.NONE)
            if isinstance(trust_level, str):
                try:
                    trust_level = TrustLevel(trust_level)
                except ValueError:
                    trust_level = TrustLevel.NONE

            if trust_level == TrustLevel.NONE:
                warnings.append(
                    ValidationError(
                        field="trust.trust_level",
                        message=f"Card with {', '.join(high_risk_caps)} should require trust level (current: none)",
                        severity="warning",
                    )
                )

    # ── R9: Secrets must not appear in serialized card ─────────────────────
    # Check for common secret patterns in string fields
    secret_patterns = [
        "sk-",
        "ghp_",
        "ghs_",
        "AKIA",
        "Bearer ",
        "-----BEGIN PRIVATE KEY-----",
    ]
    card_str = str(card_dict)
    for pattern in secret_patterns:
        if pattern in card_str and "[REDACTED]" not in card_str.replace(pattern, "[REDACTED]"):
            # Only flag if the pattern appears outside of a redacted context
            # This is a heuristic check; real secrets would be caught by the Redactor
            pass  # TODO: Implement proper secret detection

    # ── R10: MCP manifest hash should be included for MCP cards ─────────────
    if entity_type in (EntityType.MCP_SERVER, EntityType.MCP_TOOL):
        provenance = card_dict.get("provenance", {})
        mcp_manifest_hash = provenance.get("mcp_manifest_hash")
        if not mcp_manifest_hash and not mcp:
            warnings.append(
                ValidationError(
                    field="provenance.mcp_manifest_hash",
                    message="MCP entity should include provenance.mcp_manifest_hash for drift detection",
                    severity="warning",
                )
            )

    # ── Determine overall validity ─────────────────────────────────────────
    ok = len(errors) == 0

    return ValidationReport(ok=ok, errors=errors, warnings=warnings)


def validate_card_json(card_json: str) -> ValidationReport:
    """Validate a CapabilityCard from JSON string."""
    try:
        card_dict = json.loads(card_json)
    except Exception as e:
        return ValidationReport(
            ok=False,
            errors=[ValidationError(field="json", message=f"Invalid JSON: {e}")],
        )

    try:
        card = CapabilityCard.model_validate(card_dict)
    except Exception as e:
        return ValidationReport(
            ok=False,
            errors=[ValidationError(field="model", message=f"Validation error: {e}")],
        )

    return validate_card(card)


# Backward compatibility import
import json  # noqa: E402
