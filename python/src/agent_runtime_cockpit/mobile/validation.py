"""Fail-closed validation for mobile runtime manifests and capabilities.

Rules:
  V1  capability ID required
  V2  platform support required
  V3  sensitive capabilities require approval_mode
  V4  write capabilities require audit + hitl/trust
  V5  sensitive native capabilities must be mock-only in MVP
  V6  background execution blocked in MVP
  V7  network blocked unless mock
  V8  mcp_exposable requires explicit safe metadata flag
  V9  no secrets in manifests
  V10 capability_hash must match content when set
  V11 manifest_hash must match content when set
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .models import (
    MobileActionPlan,
    MobileCapability,
    MobileDataSensitivity,
    MobileRuntimeManifest,
)

_SENSITIVE_PREFIXES = (
    "device.camera",
    "device.microphone",
    "device.location",
    "device.calendar",
    "device.contacts",
    "device.photos",
    "device.health",
    "device.biometric",
)


class ValidationFinding(BaseModel):
    rule: str
    field: str
    severity: str  # "error" | "warning"
    message: str
    remediation: str


class MobileValidationReport(BaseModel):
    ok: bool = True
    manifest_id: Optional[str] = None
    errors: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[ValidationFinding] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def findings(self) -> list[ValidationFinding]:
        return self.errors + self.warnings


def _validate_capability(cap: MobileCapability) -> list[ValidationFinding]:
    findings = []

    # V1: ID required
    if not cap.id:
        findings.append(
            ValidationFinding(
                rule="capability_id_required",
                field="id",
                severity="error",
                message="Capability ID is required.",
                remediation="Set a stable, namespaced ID e.g. 'device.camera.capture.mock'.",
            )
        )

    # V2: platform required
    if not cap.platforms:
        findings.append(
            ValidationFinding(
                rule="platform_required",
                field="platforms",
                severity="error",
                message="At least one platform must be declared.",
                remediation="Add at least one platform to 'platforms'.",
            )
        )

    # V3: sensitive capabilities require approval_mode
    if cap.data_sensitivity in (MobileDataSensitivity.HIGH, MobileDataSensitivity.CRITICAL):
        if cap.approval_mode.value == "none":
            findings.append(
                ValidationFinding(
                    rule="sensitive_requires_approval",
                    field="approval_mode",
                    severity="error",
                    message=f"Capability '{cap.id}' is {cap.data_sensitivity.value} sensitivity but has no approval mode.",
                    remediation="Set approval_mode to 'required' or 'blocking'.",
                )
            )

    # V4: writes require audit + hitl/trust
    if cap.writes:
        if not cap.auditable:
            findings.append(
                ValidationFinding(
                    rule="write_requires_audit",
                    field="auditable",
                    severity="error",
                    message=f"Capability '{cap.id}' writes but auditable=False.",
                    remediation="Set auditable=True for write capabilities.",
                )
            )
        if not cap.requires_hitl and not cap.requires_trust:
            findings.append(
                ValidationFinding(
                    rule="write_requires_hitl_or_trust",
                    field="requires_hitl",
                    severity="warning",
                    message=f"Write capability '{cap.id}' should require HITL or trust.",
                    remediation="Set requires_hitl=True or requires_trust=True.",
                )
            )

    # V5: sensitive native capabilities must be mock-only
    cid = (cap.id or "").lower()
    is_sensitive_native = any(cid.startswith(p) for p in _SENSITIVE_PREFIXES)
    if is_sensitive_native and not cap.id.endswith(".mock"):
        findings.append(
            ValidationFinding(
                rule="sensitive_must_be_mock",
                field="id",
                severity="error",
                message=f"Sensitive capability '{cap.id}' must be mock-only in MVP (id must end with '.mock').",
                remediation="Rename to end with '.mock' or implement real native bridge in a future version.",
            )
        )

    # V6: background execution blocked in MVP
    if cap.background:
        findings.append(
            ValidationFinding(
                rule="background_blocked",
                field="background",
                severity="error",
                message=f"Capability '{cap.id}' declares background=True. Background execution is blocked in MVP.",
                remediation="Set background=False.",
            )
        )

    # V7: network blocked unless mock
    if cap.network and not cap.id.endswith(".mock"):
        findings.append(
            ValidationFinding(
                rule="network_blocked",
                field="network",
                severity="error",
                message=f"Capability '{cap.id}' declares network=True but is not mock. Network is blocked in MVP.",
                remediation="Set network=False or add '.mock' suffix.",
            )
        )

    # V8: mcp_exposable requires safe metadata flag
    if cap.mcp_exposable and not cap.metadata.get("mcp_safe_reviewed"):
        findings.append(
            ValidationFinding(
                rule="mcp_exposable_requires_review",
                field="mcp_exposable",
                severity="error",
                message=f"Capability '{cap.id}' is mcp_exposable but has no 'mcp_safe_reviewed' metadata flag.",
                remediation="Add metadata={'mcp_safe_reviewed': True} after security review.",
            )
        )

    # V10: capability_hash must match
    if cap.capability_hash:
        from .hashing import capability_hash as compute_hash

        computed = compute_hash(cap)
        if computed != cap.capability_hash:
            findings.append(
                ValidationFinding(
                    rule="capability_hash_mismatch",
                    field="capability_hash",
                    severity="error",
                    message=f"Capability '{cap.id}' hash mismatch.",
                    remediation="Recompute capability_hash.",
                )
            )

    return findings


def validate_capability(cap: MobileCapability) -> MobileValidationReport:
    findings = _validate_capability(cap)
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    return MobileValidationReport(
        ok=not errors,
        manifest_id=cap.id,
        errors=errors,
        warnings=warnings,
    )


def validate_manifest(manifest: MobileRuntimeManifest) -> MobileValidationReport:
    errors: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []

    if not manifest.id:
        errors.append(
            ValidationFinding(
                rule="manifest_id_required",
                field="id",
                severity="error",
                message="Manifest ID is required.",
                remediation="Set a stable manifest ID.",
            )
        )

    # V6: background execution blocked in MVP
    if manifest.background_execution:
        errors.append(
            ValidationFinding(
                rule="background_blocked_manifest",
                field="background_execution",
                severity="error",
                message="background_execution=True is blocked in MVP.",
                remediation="Set background_execution=False.",
            )
        )

    # V7: network blocked in MVP
    if manifest.network_by_default:
        errors.append(
            ValidationFinding(
                rule="network_blocked_manifest",
                field="network_by_default",
                severity="error",
                message="network_by_default=True is blocked in MVP.",
                remediation="Set network_by_default=False.",
            )
        )

    # V9: no secrets (check by redaction)
    from .redaction import redact_dict

    d = manifest.model_dump(mode="json")
    _, tokens = redact_dict(d)
    if tokens > 0:
        errors.append(
            ValidationFinding(
                rule="secret_in_manifest",
                field="manifest",
                severity="error",
                message=f"Manifest contains {tokens} possible secret(s).",
                remediation="Remove secrets from the manifest.",
            )
        )

    # V11: manifest_hash
    if manifest.manifest_hash:
        from .hashing import manifest_hash as compute_hash

        computed = compute_hash(manifest)
        if computed != manifest.manifest_hash:
            errors.append(
                ValidationFinding(
                    rule="manifest_hash_mismatch",
                    field="manifest_hash",
                    severity="error",
                    message="Manifest hash mismatch.",
                    remediation="Recompute manifest_hash.",
                )
            )
    else:
        warnings.append(
            ValidationFinding(
                rule="manifest_not_pinned",
                field="manifest_hash",
                severity="warning",
                message="Manifest is not hash-pinned.",
                remediation="Compute and set manifest_hash.",
            )
        )

    # Validate each capability
    for cap in manifest.capabilities:
        sub = _validate_capability(cap)
        errors.extend(f for f in sub if f.severity == "error")
        warnings.extend(f for f in sub if f.severity == "warning")

    return MobileValidationReport(
        ok=not errors,
        manifest_id=manifest.id,
        errors=errors,
        warnings=warnings,
    )


def validate_action_plan(
    plan: MobileActionPlan, known_capabilities: list[MobileCapability]
) -> MobileValidationReport:
    errors: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []
    known_ids = {c.id for c in known_capabilities}

    if plan.requires_background:
        errors.append(
            ValidationFinding(
                rule="background_blocked",
                field="requires_background",
                severity="error",
                message="Action plan requires background execution. Blocked in MVP.",
                remediation="Set requires_background=False.",
            )
        )
    if plan.requires_network:
        errors.append(
            ValidationFinding(
                rule="network_blocked",
                field="requires_network",
                severity="error",
                message="Action plan requires network. Blocked in MVP.",
                remediation="Set requires_network=False.",
            )
        )

    for step in plan.steps:
        if step.capability_id not in known_ids:
            errors.append(
                ValidationFinding(
                    rule="unknown_capability",
                    field=f"steps[{step.step_id}].capability_id",
                    severity="error",
                    message=f"Unknown capability '{step.capability_id}'.",
                    remediation="Register the capability in the manifest first.",
                )
            )
        elif not step.mock:
            cid = step.capability_id.lower()
            if any(cid.startswith(p) for p in _SENSITIVE_PREFIXES):
                errors.append(
                    ValidationFinding(
                        rule="sensitive_must_be_mock",
                        field=f"steps[{step.step_id}].mock",
                        severity="error",
                        message=f"Step '{step.step_id}' uses sensitive capability '{step.capability_id}' without mock=True.",
                        remediation="Set mock=True or use a .mock capability ID.",
                    )
                )

    return MobileValidationReport(
        ok=not errors,
        manifest_id=plan.plan_id,
        errors=errors,
        warnings=warnings,
    )
