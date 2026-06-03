"""Static loading and inspection for runtime packs.

This module reads ``arc-runtime-pack.json`` from disk and produces typed models
and human/machine inspection summaries. It performs **only** file reads and JSON
parsing. It never imports pack modules, never executes entrypoints, never starts
servers, and never touches the network. There is intentionally no use of
``importlib`` here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import MANIFEST_FILENAME, RuntimePackManifest


class ManifestLoadError(Exception):
    """Raised when a manifest cannot be located or parsed."""


def find_manifest(path: Path | str) -> Path:
    """Resolve a path (file or directory) to a manifest file.

    If ``path`` is a directory, ``arc-runtime-pack.json`` inside it is used.
    """
    p = Path(path)
    if p.is_dir():
        candidate = p / MANIFEST_FILENAME
        if not candidate.is_file():
            raise ManifestLoadError(f"No {MANIFEST_FILENAME} found in directory: {p}")
        return candidate
    if p.is_file():
        return p
    raise ManifestLoadError(f"Manifest path does not exist: {p}")


def load_manifest_dict(path: Path | str) -> dict[str, Any]:
    """Load and JSON-parse a manifest into a plain dict (no validation)."""
    manifest_path = find_manifest(path)
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestLoadError(f"Could not read manifest: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestLoadError(f"Manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestLoadError("Manifest root must be a JSON object.")
    return data


def load_manifest(path: Path | str) -> RuntimePackManifest:
    """Load and parse a manifest into a typed model (raises on schema mismatch)."""
    from .models import RUNTIME_PACK_SCHEMA_VERSION  # noqa: PLC0415

    data = load_manifest_dict(path)
    schema_ver = data.get("schema_version")
    if schema_ver != RUNTIME_PACK_SCHEMA_VERSION:
        raise ManifestLoadError(
            f"Unsupported schema_version {schema_ver!r}; "
            f"expected {RUNTIME_PACK_SCHEMA_VERSION}. "
            "This manifest may require a newer version of ARC."
        )
    try:
        return RuntimePackManifest.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise ManifestLoadError(f"Manifest does not match schema: {exc}") from exc


def inspect_manifest(manifest: RuntimePackManifest) -> dict[str, Any]:
    """Produce a structured, machine-readable inspection of a manifest.

    The summary answers the questions a CLI agent needs before trusting a pack:
    what it is, what it can do, what it requires, whether it can make paid calls,
    whether it can export IR, and what its security surface looks like.
    """
    caps = manifest.capabilities
    return {
        "id": manifest.id,
        "name": manifest.name,
        "version": manifest.version,
        "schema_version": manifest.schema_version,
        "runtime": {
            "name": manifest.runtime.runtime_name,
            "kind": manifest.runtime.runtime_kind.value,
            "language": manifest.runtime.language,
            "framework": manifest.runtime.framework,
            "license": manifest.runtime.license,
        },
        "adapter": manifest.adapter,
        "entrypoints": manifest.entrypoints.as_mapping(),
        "permissions": [
            {
                "kind": p.kind,
                "required": p.required,
                "scope": p.scope,
                "default_decision": p.default_decision.value,
                "has_reason": bool(p.reason and p.reason.strip()),
            }
            for p in manifest.permissions
        ],
        "capabilities": [c.name for c in caps],
        "tools": [{"name": t.name, "kind": t.kind.value, "paid": t.paid} for t in manifest.tools],
        "mcp": [
            {"server_id": d.server_id, "required": d.required, "pinned": bool(d.manifest_hash)}
            for d in manifest.mcp
        ],
        "security_surface": {
            "can_call_paid_models": manifest.declares_paid(),
            "can_access_network": manifest.declares_network(),
            "can_access_filesystem": any(c.reads or c.writes for c in caps)
            or manifest.storage.enabled,
            "can_run_shell": any(c.shell for c in caps),
            "can_call_mcp": any(c.mcp for c in caps) or bool(manifest.mcp),
            "can_access_secrets": any(c.secrets for c in caps),
            "can_access_memory": manifest.memory.enabled,
            "can_search": manifest.search.enabled,
            "can_run_background": any(c.background for c in caps),
            "can_run_outside_workspace": any(c.outside_workspace for c in caps)
            or manifest.storage.outside_workspace,
        },
        "ir": {
            "can_export_ir": manifest.ir.can_export_ir,
            "supported_ir_version": manifest.ir.supported_ir_version,
            "opaque_node_policy": (
                manifest.ir.opaque_node_policy.value if manifest.ir.opaque_node_policy else None
            ),
        },
        "policy": {
            "supports_preflight": manifest.policy.supports_preflight,
            "fail_closed": manifest.policy.fail_closed,
            "required_rules": manifest.policy.required_rules,
        },
        "manifest_hash": manifest.manifest_hash,
    }


__all__ = [
    "ManifestLoadError",
    "find_manifest",
    "load_manifest_dict",
    "load_manifest",
    "inspect_manifest",
]
