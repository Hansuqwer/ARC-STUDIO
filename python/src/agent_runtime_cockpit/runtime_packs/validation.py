"""Static validation for runtime pack manifests.

All validation is **static** and **fail-closed**: no pack code is imported or
executed, no network call is made, and unknown/under-specified inputs are
rejected rather than silently accepted.

Rules (mirrors the structure of ``capabilities/validation.py``):

* R1  schema_version must equal ``RUNTIME_PACK_SCHEMA_VERSION``.
* R2  ``id`` is required, stable, and safe (no path separators or traversal).
* R3  ``version`` must be semver-like.
* R4  entrypoints must not be absolute executable paths or shell invocations.
* R5  unknown permission kinds fail closed (error).
* R6  dangerous permissions (network/paid/secrets/shell/outside_workspace) must
      carry a ``reason``.
* R7  a capability flag that is dangerous must be backed by a matching permission.
* R8  a dangerous permission whose ``default_decision`` is ``allow`` is a warning
      (capability expansion should require explicit trust/approval).
* R9  MCP declarations marked ``required`` must include a ``manifest_hash``.
* R10 IR export claims must specify a supported IR version and an opaque-node
      policy; a version mismatch with the local reader is a warning.
* R11 no secrets may appear anywhere in the manifest.
* R12 if a ``manifest_hash`` is present it must match the recomputed hash; if it
      is absent that is a warning (manifest not hash-pinned).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel

from .hashing import manifest_hash
from .models import (
    DANGEROUS_PERMISSION_KINDS,
    KNOWN_PERMISSION_KINDS,
    RUNTIME_PACK_SCHEMA_VERSION,
    DefaultDecision,
    PermissionKind,
    RuntimePackManifest,
)
from .redaction import find_secrets

# Stable, safe pack id: starts alphanumeric; dotted/dashed segments only.
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
# Semver-like: MAJOR.MINOR.PATCH with optional pre-release / build metadata.
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.\-]+)?$")
# 64-char lowercase hex sha256.
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Tokens that indicate a shell entrypoint (never executed in the MVP).
_SHELL_PREFIXES = ("sh ", "bash ", "zsh ", "./", "cmd ", "powershell ")
_SHELL_METACHARS = ("&&", "||", "|", ";", "`", "$(")


class ValidationFinding(BaseModel):
    """A single validation finding."""

    rule: str
    field: str
    message: str
    severity: str = "error"  # "error" | "warning" | "info"
    remediation: str = ""


class RuntimePackValidationReport(BaseModel):
    """Result of validating a runtime pack manifest."""

    ok: bool = True
    manifest_id: Optional[str] = None
    manifest_hash: Optional[str] = None
    computed_hash: Optional[str] = None
    findings: list[ValidationFinding] = []

    @property
    def errors(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


def _looks_absolute(value: str) -> bool:
    return value.startswith("/") or bool(re.match(r"^[A-Za-z]:[\\/]", value))


def _looks_shell(value: str) -> bool:
    low = value.strip()
    if low.endswith(".sh") or low.endswith(".bat") or low.endswith(".cmd"):
        return True
    if any(low.startswith(p) for p in _SHELL_PREFIXES):
        return True
    return any(meta in low for meta in _SHELL_METACHARS)


def _local_ir_version() -> Optional[int]:
    """Best-effort lookup of the local SwarmGraph IR schema version (optional)."""
    try:  # pragma: no cover - depends on optional repo module
        from ..swarmgraph_ir.models import IR_SCHEMA_VERSION  # type: ignore

        return int(IR_SCHEMA_VERSION)
    except Exception:
        return None


def validate_manifest(
    manifest: Any,
    *,
    allow_absolute_entrypoints: bool = False,
) -> RuntimePackValidationReport:
    """Validate a ``RuntimePackManifest`` (or dict) and return a structured report.

    ``allow_absolute_entrypoints`` only relaxes R4 and is intended for explicitly
    trusted, locally authored packs. The default (``False``) is fail-closed.
    """
    findings: list[ValidationFinding] = []

    if isinstance(manifest, RuntimePackManifest):
        m = manifest
    else:
        # Loading must not crash on malformed input; surface a single error.
        try:
            m = RuntimePackManifest.model_validate(manifest)
        except Exception as exc:  # noqa: BLE001
            return RuntimePackValidationReport(
                ok=False,
                findings=[
                    ValidationFinding(
                        rule="parse",
                        field="manifest",
                        message=f"Manifest does not match schema: {exc}",
                        remediation="Fix the manifest structure to match arc-runtime-pack.json.",
                    )
                ],
            )

    data = m.model_dump(mode="json")

    # ── R1: schema version ───────────────────────────────────────────────
    if m.schema_version != RUNTIME_PACK_SCHEMA_VERSION:
        findings.append(
            ValidationFinding(
                rule="schema_version",
                field="schema_version",
                message=(
                    f"Schema version mismatch: expected {RUNTIME_PACK_SCHEMA_VERSION}, "
                    f"got {m.schema_version}"
                ),
                remediation=f"Set schema_version to {RUNTIME_PACK_SCHEMA_VERSION}.",
            )
        )

    # ── R2: id stable and safe ───────────────────────────────────────────
    if not m.id:
        findings.append(
            ValidationFinding(
                rule="id",
                field="id",
                message="Pack id is required.",
                remediation="Add a stable id such as 'org.my-runtime'.",
            )
        )
    elif not _ID_RE.match(m.id) or ".." in m.id or "/" in m.id or "\\" in m.id:
        findings.append(
            ValidationFinding(
                rule="id",
                field="id",
                message=f"Pack id '{m.id}' is not stable/safe.",
                remediation="Use only [A-Za-z0-9._-]; no path separators or '..'.",
            )
        )

    # ── R3: semver-like version ──────────────────────────────────────────
    if not _SEMVER_RE.match(m.version):
        findings.append(
            ValidationFinding(
                rule="version",
                field="version",
                message=f"Version '{m.version}' is not semver-like (MAJOR.MINOR.PATCH).",
                remediation="Use a semver string such as '0.1.0'.",
            )
        )

    # ── R4: entrypoints must be safe references ──────────────────────────
    for name, value in m.entrypoints.as_mapping().items():
        if _looks_shell(value):
            findings.append(
                ValidationFinding(
                    rule="entrypoint_shell",
                    field=f"entrypoints.{name}",
                    message=f"Entrypoint '{name}' looks like a shell invocation: {value!r}.",
                    remediation="Use a module:function reference; shell entrypoints are not"
                    " executed in the MVP.",
                )
            )
        elif _looks_absolute(value) and not allow_absolute_entrypoints:
            findings.append(
                ValidationFinding(
                    rule="entrypoint_absolute",
                    field=f"entrypoints.{name}",
                    message=f"Entrypoint '{name}' is an absolute path: {value!r}.",
                    remediation="Use a relative module:function reference, or explicitly trust"
                    " the pack to allow absolute paths.",
                )
            )

    # ── R5/R6/R8: permissions ────────────────────────────────────────────
    for idx, perm in enumerate(m.permissions):
        if perm.kind not in KNOWN_PERMISSION_KINDS:
            findings.append(
                ValidationFinding(
                    rule="unknown_permission",
                    field=f"permissions[{idx}].kind",
                    message=f"Unknown permission kind '{perm.kind}' (fails closed).",
                    remediation="Use one of: " + ", ".join(sorted(KNOWN_PERMISSION_KINDS)) + ".",
                )
            )
            continue
        if perm.kind in DANGEROUS_PERMISSION_KINDS and not (perm.reason and perm.reason.strip()):
            findings.append(
                ValidationFinding(
                    rule="dangerous_permission_no_reason",
                    field=f"permissions[{idx}].reason",
                    message=f"Dangerous permission '{perm.kind}' must declare a reason.",
                    remediation="Add a 'reason' explaining why this permission is required.",
                )
            )
        if (
            perm.kind in DANGEROUS_PERMISSION_KINDS
            and perm.default_decision == DefaultDecision.ALLOW
        ):
            findings.append(
                ValidationFinding(
                    rule="dangerous_permission_default_allow",
                    field=f"permissions[{idx}].default_decision",
                    message=(
                        f"Dangerous permission '{perm.kind}' defaults to 'allow'; capability "
                        "expansion should require explicit trust or approval."
                    ),
                    severity="warning",
                    remediation="Set default_decision to 'deny' or 'prompt'.",
                )
            )

    declared = m.permission_kinds()

    # ── R7: dangerous capability flags must be backed by permissions ─────
    flag_to_permission = {
        "network": PermissionKind.NETWORK.value,
        "paid": PermissionKind.PAID_MODELS.value,
        "secrets": PermissionKind.SECRETS.value,
        "shell": PermissionKind.SHELL.value,
        "outside_workspace": PermissionKind.OUTSIDE_WORKSPACE.value,
    }
    soft_flag_to_permission = {
        "mcp": PermissionKind.MCP.value,
        "background": PermissionKind.BACKGROUND.value,
    }
    for idx, cap in enumerate(m.capabilities):
        for flag, required_perm in flag_to_permission.items():
            if getattr(cap, flag) and required_perm not in declared:
                findings.append(
                    ValidationFinding(
                        rule="capability_missing_permission",
                        field=f"capabilities[{idx}].{flag}",
                        message=(
                            f"Capability '{cap.name}' sets {flag}=true but does not declare the "
                            f"'{required_perm}' permission."
                        ),
                        remediation=f"Add a '{required_perm}' permission with a reason.",
                    )
                )
        for flag, required_perm in soft_flag_to_permission.items():
            if getattr(cap, flag) and required_perm not in declared:
                findings.append(
                    ValidationFinding(
                        rule="capability_missing_permission_soft",
                        field=f"capabilities[{idx}].{flag}",
                        message=(
                            f"Capability '{cap.name}' sets {flag}=true without a matching "
                            f"'{required_perm}' permission."
                        ),
                        severity="warning",
                        remediation=f"Consider declaring a '{required_perm}' permission.",
                    )
                )

    # ── R9: MCP declarations require a manifest hash when required ────────
    for idx, mcp in enumerate(m.mcp):
        if mcp.required and not mcp.manifest_hash:
            findings.append(
                ValidationFinding(
                    rule="mcp_missing_hash",
                    field=f"mcp[{idx}].manifest_hash",
                    message=(f"Required MCP server '{mcp.server_id}' must pin a manifest_hash."),
                    remediation="Pin the MCP server card hash from your local MCP registry.",
                )
            )
        elif mcp.manifest_hash and not _SHA256_RE.match(mcp.manifest_hash):
            findings.append(
                ValidationFinding(
                    rule="mcp_hash_format",
                    field=f"mcp[{idx}].manifest_hash",
                    message=f"MCP manifest_hash for '{mcp.server_id}' is not a sha256 hex digest.",
                    severity="warning",
                    remediation="Use a 64-character lowercase hex sha256 digest.",
                )
            )

    # ── R10: IR export claims ────────────────────────────────────────────
    if m.ir.can_export_ir:
        if m.ir.supported_ir_version is None:
            findings.append(
                ValidationFinding(
                    rule="ir_missing_version",
                    field="ir.supported_ir_version",
                    message="Pack claims can_export_ir but does not declare supported_ir_version.",
                    remediation="Set ir.supported_ir_version to the IR schema version you target.",
                )
            )
        if m.ir.opaque_node_policy is None:
            findings.append(
                ValidationFinding(
                    rule="ir_missing_opaque_policy",
                    field="ir.opaque_node_policy",
                    message=(
                        "Pack can export IR but does not declare an opaque_node_policy; any "
                        "exporter may emit nodes it cannot classify."
                    ),
                    remediation="Set ir.opaque_node_policy to reject, mark_opaque, or"
                    " require_review.",
                )
            )
        local_ir = _local_ir_version()
        if (
            local_ir is not None
            and m.ir.supported_ir_version is not None
            and m.ir.supported_ir_version != local_ir
        ):
            findings.append(
                ValidationFinding(
                    rule="ir_version_mismatch",
                    field="ir.supported_ir_version",
                    message=(
                        f"Pack targets IR version {m.ir.supported_ir_version}; local reader is "
                        f"version {local_ir}."
                    ),
                    severity="warning",
                    remediation="Confirm the pack's IR output is compatible with this ARC build.",
                )
            )

    # ── R11: no secrets anywhere ─────────────────────────────────────────
    secrets = find_secrets(data)
    if secrets:
        findings.append(
            ValidationFinding(
                rule="secret_in_manifest",
                field="manifest",
                message="Manifest appears to contain secret material: "
                + ", ".join(sorted(set(secrets))),
                remediation="Remove all secrets; manifests are committed and hashed.",
            )
        )

    # ── R12: manifest hash integrity ─────────────────────────────────────
    computed = manifest_hash(m)
    if m.manifest_hash:
        if m.manifest_hash != computed:
            findings.append(
                ValidationFinding(
                    rule="manifest_hash_mismatch",
                    field="manifest_hash",
                    message="Stored manifest_hash does not match content (drift detected).",
                    remediation="Recompute the hash after edits (the pack may have drifted).",
                )
            )
    else:
        findings.append(
            ValidationFinding(
                rule="manifest_not_pinned",
                field="manifest_hash",
                message="Manifest is not hash-pinned.",
                severity="warning",
                remediation="Compute and store manifest_hash so drift can be detected.",
            )
        )

    ok = not any(f.severity == "error" for f in findings)
    return RuntimePackValidationReport(
        ok=ok,
        manifest_id=m.id or None,
        manifest_hash=m.manifest_hash,
        computed_hash=computed,
        findings=findings,
    )


__all__ = [
    "ValidationFinding",
    "RuntimePackValidationReport",
    "validate_manifest",
]
