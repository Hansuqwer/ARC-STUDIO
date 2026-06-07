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

Strict-mode additions:
  S1 stable namespaced capability IDs must match ``^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+(\.mock)?$``
  S2 duplicate capability IDs are errors
  S3 duplicate action step IDs are errors
  S4 write capabilities without HITL/trust are errors instead of warnings
  S5 missing manifest/capability hashes are errors instead of warnings/allowed
"""

from __future__ import annotations

import re
from collections import Counter
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

_CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+(\.mock)?$")


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


def _finding(
    rule: str,
    field: str,
    severity: str,
    message: str,
    remediation: str,
) -> ValidationFinding:
    return ValidationFinding(
        rule=rule,
        field=field,
        severity=severity,
        message=message,
        remediation=remediation,
    )


def _validate_capability(cap: MobileCapability, *, strict: bool = False) -> list[ValidationFinding]:
    findings = []

    # V1: ID required
    if not cap.id:
        findings.append(
            _finding(
                "capability_id_required",
                "id",
                "error",
                "Capability ID is required.",
                "Set a stable, namespaced ID e.g. 'device.camera.capture.mock'.",
            )
        )
    elif strict and not _CAPABILITY_ID_RE.match(cap.id):
        findings.append(
            _finding(
                "capability_id_invalid",
                "id",
                "error",
                f"Capability ID '{cap.id}' is not a stable lowercase dotted ID.",
                "Use lowercase dotted IDs such as 'app.memory.write.mock'.",
            )
        )

    # V2: platform required
    if not cap.platforms:
        findings.append(
            _finding(
                "platform_required",
                "platforms",
                "error",
                "At least one platform must be declared.",
                "Add at least one platform to 'platforms'.",
            )
        )

    # V3: sensitive capabilities require approval_mode
    if cap.data_sensitivity in (MobileDataSensitivity.HIGH, MobileDataSensitivity.CRITICAL):
        if cap.approval_mode.value == "none":
            findings.append(
                _finding(
                    "sensitive_requires_approval",
                    "approval_mode",
                    "error",
                    f"Capability '{cap.id}' is {cap.data_sensitivity.value} sensitivity but has no approval mode.",
                    "Set approval_mode to 'required' or 'blocking'.",
                )
            )

    # V4: writes require audit + hitl/trust
    if cap.writes:
        if not cap.auditable:
            findings.append(
                _finding(
                    "write_requires_audit",
                    "auditable",
                    "error",
                    f"Capability '{cap.id}' writes but auditable=False.",
                    "Set auditable=True for write capabilities.",
                )
            )
        if not cap.requires_hitl and not cap.requires_trust:
            findings.append(
                _finding(
                    "write_requires_hitl_or_trust",
                    "requires_hitl",
                    "error" if strict else "warning",
                    f"Write capability '{cap.id}' should require HITL or trust.",
                    "Set requires_hitl=True or requires_trust=True.",
                )
            )

    # V5: sensitive native capabilities must be mock-only
    cid = (cap.id or "").lower()
    is_sensitive_native = any(cid.startswith(p) for p in _SENSITIVE_PREFIXES)
    if is_sensitive_native and not cap.id.endswith(".mock"):
        findings.append(
            _finding(
                "sensitive_must_be_mock",
                "id",
                "error",
                f"Sensitive capability '{cap.id}' must be mock-only in MVP (id must end with '.mock').",
                "Rename to end with '.mock' or implement real native bridge in a future version.",
            )
        )

    # V6: background execution blocked in MVP
    if cap.background:
        findings.append(
            _finding(
                "background_blocked",
                "background",
                "error",
                f"Capability '{cap.id}' declares background=True. Background execution is blocked in MVP.",
                "Set background=False.",
            )
        )

    # V7: network blocked unless mock
    if cap.network and not cap.id.endswith(".mock"):
        findings.append(
            _finding(
                "network_blocked",
                "network",
                "error",
                f"Capability '{cap.id}' declares network=True but is not mock. Network is blocked in MVP.",
                "Set network=False or add '.mock' suffix.",
            )
        )

    # V8: mcp_exposable requires safe metadata flag
    if cap.mcp_exposable and not cap.metadata.get("mcp_safe_reviewed"):
        findings.append(
            _finding(
                "mcp_exposable_requires_review",
                "mcp_exposable",
                "error",
                f"Capability '{cap.id}' is mcp_exposable but has no 'mcp_safe_reviewed' metadata flag.",
                "Add metadata={'mcp_safe_reviewed': True} after security review.",
            )
        )

    # V10: capability_hash must match
    if cap.capability_hash:
        from .hashing import capability_hash as compute_hash

        computed = compute_hash(cap)
        if computed != cap.capability_hash:
            findings.append(
                _finding(
                    "capability_hash_mismatch",
                    "capability_hash",
                    "error",
                    f"Capability '{cap.id}' hash mismatch.",
                    "Recompute capability_hash.",
                )
            )
    elif strict:
        findings.append(
            _finding(
                "capability_not_pinned",
                "capability_hash",
                "error",
                f"Capability '{cap.id}' is not hash-pinned.",
                "Compute and set capability_hash.",
            )
        )

    return findings


def validate_capability(cap: MobileCapability, *, strict: bool = False) -> MobileValidationReport:
    findings = _validate_capability(cap, strict=strict)
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    return MobileValidationReport(
        ok=not errors,
        manifest_id=cap.id,
        errors=errors,
        warnings=warnings,
    )


def validate_manifest(
    manifest: MobileRuntimeManifest, *, strict: bool = False
) -> MobileValidationReport:
    errors: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []

    if not manifest.id:
        errors.append(
            _finding(
                "manifest_id_required",
                "id",
                "error",
                "Manifest ID is required.",
                "Set a stable manifest ID.",
            )
        )

    # S2: duplicate capability IDs
    cap_ids = [cap.id for cap in manifest.capabilities]
    for cap_id, count in Counter(cap_ids).items():
        if cap_id and count > 1:
            errors.append(
                _finding(
                    "duplicate_capability_id",
                    "capabilities",
                    "error",
                    f"Capability ID '{cap_id}' appears {count} times.",
                    "Use stable unique capability IDs within a manifest.",
                )
            )

    # V6: background execution blocked in MVP
    if manifest.background_execution:
        errors.append(
            _finding(
                "background_blocked_manifest",
                "background_execution",
                "error",
                "background_execution=True is blocked in MVP.",
                "Set background_execution=False.",
            )
        )

    # V7: network blocked in MVP
    if manifest.network_by_default:
        errors.append(
            _finding(
                "network_blocked_manifest",
                "network_by_default",
                "error",
                "network_by_default=True is blocked in MVP.",
                "Set network_by_default=False.",
            )
        )

    # V9: no secrets (check by redaction)
    from .redaction import redact_dict

    d = manifest.model_dump(mode="json")
    _, tokens = redact_dict(d)
    if tokens > 0:
        errors.append(
            _finding(
                "secret_in_manifest",
                "manifest",
                "error",
                f"Manifest contains {tokens} possible secret(s).",
                "Remove secrets from the manifest.",
            )
        )

    # V11: manifest_hash
    if manifest.manifest_hash:
        from .hashing import manifest_hash as compute_hash

        computed = compute_hash(manifest)
        if computed != manifest.manifest_hash:
            errors.append(
                _finding(
                    "manifest_hash_mismatch",
                    "manifest_hash",
                    "error",
                    "Manifest hash mismatch.",
                    "Recompute manifest_hash.",
                )
            )
    else:
        findings_target = errors if strict else warnings
        findings_target.append(
            _finding(
                "manifest_not_pinned",
                "manifest_hash",
                "error" if strict else "warning",
                "Manifest is not hash-pinned.",
                "Compute and set manifest_hash.",
            )
        )

    # Validate each capability
    for cap in manifest.capabilities:
        sub = _validate_capability(cap, strict=strict)
        errors.extend(f for f in sub if f.severity == "error")
        warnings.extend(f for f in sub if f.severity == "warning")

    return MobileValidationReport(
        ok=not errors,
        manifest_id=manifest.id,
        errors=errors,
        warnings=warnings,
    )


def validate_action_plan(
    plan: MobileActionPlan,
    known_capabilities: list[MobileCapability],
    *,
    strict: bool = False,
) -> MobileValidationReport:
    errors: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []
    known_ids = {c.id for c in known_capabilities}

    # S3: duplicate step IDs
    step_ids = [step.step_id for step in plan.steps]
    for step_id, count in Counter(step_ids).items():
        if step_id and count > 1:
            errors.append(
                _finding(
                    "duplicate_step_id",
                    "steps",
                    "error",
                    f"Step ID '{step_id}' appears {count} times.",
                    "Use stable unique step IDs within an action plan.",
                )
            )

    if plan.requires_background:
        errors.append(
            _finding(
                "background_blocked",
                "requires_background",
                "error",
                "Action plan requires background execution. Blocked in MVP.",
                "Set requires_background=False.",
            )
        )
    if plan.requires_network:
        errors.append(
            _finding(
                "network_blocked",
                "requires_network",
                "error",
                "Action plan requires network. Blocked in MVP.",
                "Set requires_network=False.",
            )
        )

    for step in plan.steps:
        if step.capability_id not in known_ids:
            errors.append(
                _finding(
                    "unknown_capability",
                    f"steps[{step.step_id}].capability_id",
                    "error",
                    f"Unknown capability '{step.capability_id}'.",
                    "Register the capability in the manifest first.",
                )
            )
        elif not step.mock:
            cid = step.capability_id.lower()
            if any(cid.startswith(p) for p in _SENSITIVE_PREFIXES):
                errors.append(
                    _finding(
                        "sensitive_must_be_mock",
                        f"steps[{step.step_id}].mock",
                        "error",
                        f"Step '{step.step_id}' uses sensitive capability '{step.capability_id}' without mock=True.",
                        "Set mock=True or use a .mock capability ID.",
                    )
                )
        if strict and not step.step_id:
            errors.append(
                _finding(
                    "step_id_required",
                    "steps.step_id",
                    "error",
                    "Strict validation requires every step to have a stable step_id.",
                    "Set step_id to a stable unique value.",
                )
            )

    return MobileValidationReport(
        ok=not errors,
        manifest_id=plan.plan_id,
        errors=errors,
        warnings=warnings,
    )
