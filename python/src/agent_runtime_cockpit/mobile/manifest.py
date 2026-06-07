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


def load_manifest(path: str | Path) -> MobileRuntimeManifest:
    p = Path(path)
    if p.is_dir():
        p = p / MANIFEST_FILENAME
    if not p.exists():
        raise MobileManifestLoadError(f"Manifest not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return MobileRuntimeManifest.model_validate(data)
    except Exception as exc:
        raise MobileManifestLoadError(f"Cannot load manifest: {exc}") from exc


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
        privacy_manifest_intent=True,
    )
    manifest.manifest_hash = _manifest_hash(manifest)
    return manifest
