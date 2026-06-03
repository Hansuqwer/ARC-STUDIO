"""Optional integrations between runtime packs and adjacent ARC subsystems.

Every integration here is *optional*: it imports the relevant ARC subsystem
inside a ``try`` block and degrades gracefully (returning a plain dict / no-op)
when that subsystem is not installed. None of these functions execute pack code,
start servers, or open the network.

Covered:

* Capability Cards — derive a card (or card-shaped dict) for the pack.
* Policy linter — convert a validation report into policy-style findings.
* SwarmGraph IR — report version compatibility with the local reader.
* MCP registry — compare declared MCP manifest hashes against the local registry.
"""

from __future__ import annotations

from typing import Any, Optional

from .models import RuntimePackManifest
from .validation import RuntimePackValidationReport


def to_capability_card(manifest: RuntimePackManifest) -> Any:
    """Return a Capability Card for the pack, or a card-shaped dict if unavailable.

    The card summarizes the pack as a ``runtime_adapter`` entity. When the
    ``capabilities`` package is present a real ``CapabilityCard`` is returned;
    otherwise a structurally compatible dict is produced so callers always get a
    usable object.
    """
    surface = {
        "can_read": any(c.reads for c in manifest.capabilities) or manifest.storage.enabled,
        "can_write": any(c.writes for c in manifest.capabilities),
        "can_network": manifest.declares_network(),
        "can_call_tools": bool(manifest.tools),
        "can_make_paid_calls": manifest.declares_paid(),
        "can_access_secrets": any(c.secrets for c in manifest.capabilities),
        "can_call_mcp": any(c.mcp for c in manifest.capabilities) or bool(manifest.mcp),
        "can_run_shell": any(c.shell for c in manifest.capabilities),
        "can_run_outside_workspace": any(c.outside_workspace for c in manifest.capabilities),
        "can_run_background": any(c.background for c in manifest.capabilities),
    }
    card_dict = {
        "id": f"runtime-pack:{manifest.id}",
        "name": manifest.name,
        "entity_type": "runtime_adapter",
        "version": manifest.version,
        "description": manifest.description,
        "capabilities": surface,
        "metadata": {
            "runtime_pack_id": manifest.id,
            "runtime": manifest.runtime.runtime_name,
            "manifest_hash": manifest.manifest_hash,
        },
    }

    try:  # pragma: no cover - depends on optional repo module
        from ..capabilities.models import (  # type: ignore
            CapabilityCard,
            CapabilitySet,
            EntityType,
        )

        return CapabilityCard(
            id=card_dict["id"],
            name=manifest.name,
            entity_type=EntityType.RUNTIME_ADAPTER,
            version=manifest.version,
            description=manifest.description,
            # CapabilitySet uses extra="ignore", so unknown flags are dropped safely.
            capabilities=CapabilitySet(**surface),
            metadata=card_dict["metadata"],
        )
    except Exception:
        return card_dict


def to_policy_findings(report: RuntimePackValidationReport) -> list[Any]:
    """Convert a validation report into policy-linter-style findings.

    Returns ``PolicyIssue`` instances when the policy linter is importable, else
    plain dicts with the same ``rule``/``severity``/``message``/``remediation``
    keys so existing report renderers can consume them.
    """
    try:  # pragma: no cover - depends on optional repo module
        from ..security.policy_linter import PolicyIssue  # type: ignore

        return [
            PolicyIssue(
                rule=f"runtime_pack:{f.rule}",
                severity=f.severity,
                node_id=f.field,
                message=f.message,
                remediation=f.remediation,
            )
            for f in report.findings
        ]
    except Exception:
        return [
            {
                "rule": f"runtime_pack:{f.rule}",
                "severity": f.severity,
                "node_id": f.field,
                "message": f.message,
                "remediation": f.remediation,
            }
            for f in report.findings
        ]


def ir_compatibility(manifest: RuntimePackManifest) -> dict[str, Any]:
    """Report whether the pack's declared IR version matches the local reader."""
    local_version: Optional[int]
    try:  # pragma: no cover - depends on optional repo module
        from ..swarmgraph_ir.models import IR_SCHEMA_VERSION  # type: ignore

        local_version = int(IR_SCHEMA_VERSION)
    except Exception:
        local_version = None

    declared = manifest.ir.supported_ir_version
    if not manifest.ir.can_export_ir:
        compatible: Optional[bool] = None
        note = "Pack does not claim IR export."
    elif declared is None:
        compatible = False
        note = "Pack claims IR export but did not declare a version."
    elif local_version is None:
        compatible = None
        note = "Local SwarmGraph IR reader not available; cannot compare."
    else:
        compatible = declared == local_version
        note = "Compatible." if compatible else "Declared IR version differs from local reader."

    return {
        "can_export_ir": manifest.ir.can_export_ir,
        "declared_version": declared,
        "local_version": local_version,
        "compatible": compatible,
        "opaque_node_policy": (
            manifest.ir.opaque_node_policy.value if manifest.ir.opaque_node_policy else None
        ),
        "note": note,
    }


def verify_mcp_against_registry(
    manifest: RuntimePackManifest, store: Any | None = None
) -> list[dict[str, Any]]:
    """Compare each declared MCP manifest hash against a local MCP registry.

    This never starts an MCP server. If no ``store`` is given and the MCP
    registry cannot be imported, every declaration is reported as ``unknown``.
    """
    if store is None:
        try:  # pragma: no cover - depends on optional repo module
            from ..mcp.registry import McpRegistryStore  # type: ignore

            store = McpRegistryStore()
        except Exception:
            store = None

    results: list[dict[str, Any]] = []
    for decl in manifest.mcp:
        record = None
        if store is not None:
            try:
                record = store.get(decl.server_id)
            except Exception:
                record = None
        if record is None:
            status = "unknown"
            registry_hash = None
        else:
            registry_hash = getattr(record, "manifest_hash", None)
            if decl.manifest_hash and registry_hash:
                status = "match" if decl.manifest_hash == registry_hash else "mismatch"
            else:
                status = "unpinned"
        results.append(
            {
                "server_id": decl.server_id,
                "declared_hash": decl.manifest_hash,
                "registry_hash": registry_hash,
                "status": status,
            }
        )
    return results


__all__ = [
    "to_capability_card",
    "to_policy_findings",
    "ir_compatibility",
    "verify_mcp_against_registry",
]
