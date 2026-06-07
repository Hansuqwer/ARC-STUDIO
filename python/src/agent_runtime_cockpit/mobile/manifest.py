"""Load and build MobileRuntimeManifest objects."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .hashing import manifest_hash as _manifest_hash
from .models import MobileCapability, MobileRuntimeManifest, MobilePlatformSupport, MobilePlatform

log = logging.getLogger(__name__)

MANIFEST_FILENAME = "arc-mobile-capabilities.json"


class MobileManifestLoadError(ValueError):
    pass


def load_manifest(path: str | Path, *, strict: bool = False) -> MobileRuntimeManifest:
    p = Path(path)
    if p.is_dir():
        p = p / MANIFEST_FILENAME
    if not p.exists():
        raise MobileManifestLoadError(f"Manifest not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if strict:
            from .schema_validator import validate_against_schema

            errors = validate_against_schema(data, "manifest")
            if errors:
                raise MobileManifestLoadError(
                    f"Manifest failed JSON Schema validation (strict mode): {errors[0]}"
                )
            known = set(MobileRuntimeManifest.model_fields)
            unknown = set(data) - known - {"manifest_hash"}
            if unknown:
                raise MobileManifestLoadError(
                    f"Manifest has unknown fields (strict mode): {sorted(unknown)}"
                )
        manifest = MobileRuntimeManifest.model_validate(data)
    except MobileManifestLoadError:
        raise
    except Exception as exc:
        raise MobileManifestLoadError(f"Cannot load manifest: {exc}") from exc

    # Always check for duplicate capability IDs
    ids = [c.id for c in manifest.capabilities]
    seen: set[str] = set()
    dups = [cid for cid in ids if cid in seen or seen.add(cid)]  # type: ignore[func-returns-value]
    if dups:
        raise MobileManifestLoadError(
            f"Manifest '{manifest.id}' contains duplicate capability IDs: {sorted(set(dups))}"
        )
    return manifest


def build_default_manifest(
    manifest_id: str,
    name: str,
    capabilities: Optional[list[MobileCapability]] = None,
) -> MobileRuntimeManifest:
    """Build a sealed (hash-pinned) manifest from capability list."""
    from .capabilities import MOCK_CAPABILITIES

    caps = capabilities if capabilities is not None else list(MOCK_CAPABILITIES)
    platforms = [
        MobilePlatformSupport(platform=MobilePlatform.IOS, stub_only=True, framework="native"),
        MobilePlatformSupport(platform=MobilePlatform.ANDROID, stub_only=True, framework="native"),
        MobilePlatformSupport(platform=MobilePlatform.FLUTTER, stub_only=True, framework="flutter"),
        MobilePlatformSupport(platform=MobilePlatform.EXPO, stub_only=True, framework="expo"),
        MobilePlatformSupport(
            platform=MobilePlatform.REACT_NATIVE, stub_only=True, framework="react_native"
        ),
    ]
    manifest = MobileRuntimeManifest(
        id=manifest_id,
        name=name,
        version="0.1.0",
        platforms=platforms,
        capabilities=caps,
        background_execution=False,
        network_by_default=False,
        simulator_mode=True,
        privacy_manifest=True,
    )
    manifest.manifest_hash = _manifest_hash(manifest)
    return manifest
