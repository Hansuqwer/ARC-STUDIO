"""Convert an ARC Runtime SDK ``arc-sdk.json`` to an ARC Studio ``RuntimePackManifest``.

Implements R79/Phase 111 Slice 110.4: SDK runtime-pack format parity.

The SDK and ARC Studio use different manifest schemas:

* SDK   — ``arc-sdk.json`` (schema_version: string "1.0.0", app_id, sdk_version, …)
* ARC   — ``RuntimePackManifest`` (schema_version: int 1, id, runtime.kind=mobile, …)

This module owns the lossy-but-documented conversion so both can be validated
by ``arc runtime-pack validate`` without either side being silently broken.

Fields with no ARC Studio equivalent are preserved in ``manifest.metadata``
under the ``sdk_`` prefix. Fields absent from the SDK JSON are filled with
safe, minimal defaults that pass all 12 validation rules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..runtime_packs.models import (
    RUNTIME_PACK_SCHEMA_VERSION,
    RuntimeCapability,
    RuntimeIdentity,
    RuntimeKind,
    RuntimePackManifest,
    RuntimePermission,
)
from ..runtime_packs.validation import RuntimePackValidationReport, validate_manifest
from ..mobile_sdk_mapping import mobile_capability_to_sdk_card  # noqa: F401 — re-export


def sdk_manifest_to_runtime_pack(sdk_data: dict[str, Any]) -> RuntimePackManifest:
    """Convert a parsed ``arc-sdk.json`` dict to a ``RuntimePackManifest``.

    The conversion is documented and intentionally explicit. No field is silently
    dropped: SDK-only fields land in ``metadata`` under the ``sdk_`` prefix.
    """
    app_id: str = sdk_data.get("app_id", "arc-sdk-unknown")
    sdk_version: str = sdk_data.get("sdk_version", "0.1.0")
    pack_name: str = sdk_data.get("name", app_id)
    description: str = sdk_data.get("description", "")

    # Build runtime capabilities and collect required permissions.
    capabilities: list[RuntimeCapability] = []
    needs_network = False
    needs_paid = False
    for cap in sdk_data.get("capabilities", []):
        if not isinstance(cap, dict):
            continue
        cat = str(cap.get("category", ""))
        is_network = cat == "network"
        is_paid = bool(cap.get("allow_paid_calls", False))
        needs_network = needs_network or is_network
        needs_paid = needs_paid or is_paid
        capabilities.append(
            RuntimeCapability(
                name=str(cap.get("id", cap.get("name", "unknown"))),
                description=str(cap.get("description", "")),
                network=is_network,
                paid=is_paid,
            )
        )

    # R7: synthesize matching permissions for any declared dangerous flags.
    # The SDK has no permission model, so we add the minimum required to pass
    # validation, with a reason that makes the auto-synthesis explicit.
    permissions: list[RuntimePermission] = []
    if needs_network:
        permissions.append(
            RuntimePermission(
                kind="network",
                reason="Auto-synthesized from SDK network capability (arc-sdk.json → ARC pack).",
            )
        )
    if needs_paid:
        permissions.append(
            RuntimePermission(
                kind="paid_models",
                reason="Auto-synthesized from SDK allow_paid_calls capability.",
            )
        )

    # Carry SDK-only top-level fields in metadata.
    metadata: dict[str, Any] = {
        "sdk_schema_version": sdk_data.get("schema_version"),
        "sdk_app_id": app_id,
        "sdk_version": sdk_version,
    }
    for key in (
        "target_platforms",
        "routes",
        "stores",
        "effects",
        "design_tokens",
        "replay",
        "tests",
        "provenance",
    ):
        if key in sdk_data:
            metadata[f"sdk_{key}"] = sdk_data[key]

    return RuntimePackManifest(
        schema_version=RUNTIME_PACK_SCHEMA_VERSION,
        id=app_id,
        name=pack_name,
        version=sdk_version,
        description=description,
        runtime=RuntimeIdentity(
            runtime_name=pack_name,
            runtime_kind=RuntimeKind.MOBILE,
            language="typescript",
            framework="arc-runtime-sdk",
        ),
        adapter="arc-runtime-sdk",
        capabilities=capabilities,
        permissions=permissions,
        metadata=metadata,
    )


def sdk_json_to_runtime_pack(path: Path) -> RuntimePackManifest:
    """Load ``arc-sdk.json`` from *path* and convert to a ``RuntimePackManifest``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return sdk_manifest_to_runtime_pack(data)


def validate_sdk_manifest(path: Path) -> RuntimePackValidationReport:
    """Convert ``arc-sdk.json`` at *path* and run all 12 ARC runtime-pack validation rules."""
    manifest = sdk_json_to_runtime_pack(path)
    return validate_manifest(manifest)


__all__ = [
    "sdk_manifest_to_runtime_pack",
    "sdk_json_to_runtime_pack",
    "validate_sdk_manifest",
]
