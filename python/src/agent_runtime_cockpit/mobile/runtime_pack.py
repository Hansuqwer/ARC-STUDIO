"""Bridge between ARC Mobile Runtime and Runtime Pack SDK.

Generates a valid runtime pack manifest from a mobile runtime manifest.
Uses the existing runtime_packs infrastructure (no code duplication).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import MobileRuntimeManifest


def build_runtime_pack_manifest(
    mobile_manifest: MobileRuntimeManifest,
    target_dir: Path,
) -> dict[str, Any]:
    """Generate an arc-runtime-pack.json for a mobile runtime.

    Returns the pack manifest dict. Writes to target_dir/arc-runtime-pack.json.
    """
    from ..runtime_packs.models import (
        RuntimeIdentity,
        RuntimePackManifest,
        RuntimeKind,
    )
    from ..runtime_packs.hashing import manifest_hash as pack_hash
    from ..runtime_packs.scaffold import MANIFEST_FILENAME as PACK_MANIFEST_FILENAME

    cap_ids = [c.id for c in mobile_manifest.capabilities]

    identity = RuntimeIdentity(
        runtime_name=mobile_manifest.id,
        runtime_kind=RuntimeKind.MOBILE,
        language="dart/typescript/kotlin/swift",
        framework="flutter/expo/react_native",
        license=None,
    )

    pack = RuntimePackManifest(
        id=mobile_manifest.id,
        name=mobile_manifest.name,
        version=mobile_manifest.version,
        description=f"ARC Mobile Runtime Pack — {mobile_manifest.name}",
        runtime=identity,
        metadata={
            "mobile_manifest_hash": mobile_manifest.manifest_hash or "",
            "mobile_capabilities": cap_ids,
            "simulator_mode": mobile_manifest.simulator_mode,
            "background_execution": mobile_manifest.background_execution,
            "network_by_default": mobile_manifest.network_by_default,
        },
    )
    pack.manifest_hash = pack_hash(pack)

    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_data = pack.model_dump(mode="json")
    (target_dir / PACK_MANIFEST_FILENAME).write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_data
