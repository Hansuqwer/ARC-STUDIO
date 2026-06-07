"""Aggregated compliance report for ARC Mobile Runtime (Phase 12).

Combines the per-artifact advisory generators (iOS usage strings + PrivacyInfo.xcprivacy,
Android manifest permissions + Data Safety, app-store review notes) into one report from a
single manifest. Advisory only — always marked ``requires_human_review`` and never
auto-submitted. Deterministic; no network.
"""

from __future__ import annotations

from typing import Any

from ..models import MobileRuntimeManifest
from .android import generate_data_safety_notes, generate_manifest_permissions
from .ios import generate_privacy_manifest, generate_usage_strings
from .review_notes import generate_review_notes


def generate_compliance_report(manifest: MobileRuntimeManifest) -> dict[str, Any]:
    """Aggregate all advisory compliance artifacts for a manifest into one report."""
    platforms = sorted({p.value for cap in manifest.capabilities for p in cap.platforms})
    return {
        "advisory": True,
        "requires_human_review": True,
        "simulator_preview": True,
        "manifest_id": manifest.id,
        "summary": {
            "capability_count": len(manifest.capabilities),
            "platforms": platforms,
            "sensitive_capabilities": sorted(
                cap.id
                for cap in manifest.capabilities
                if cap.data_sensitivity.value in ("high", "critical")
            ),
        },
        "ios": {
            "usage_strings": generate_usage_strings(manifest),
            "privacy_manifest": generate_privacy_manifest(manifest),
        },
        "android": {
            "manifest_permissions": generate_manifest_permissions(manifest),
            "data_safety": generate_data_safety_notes(manifest),
        },
        "review_notes": generate_review_notes(manifest),
        "disclaimer": (
            "Advisory artifacts generated from the declared manifest. NOT legal advice and "
            "NOT auto-submitted; a human must review before any app-store submission."
        ),
    }
