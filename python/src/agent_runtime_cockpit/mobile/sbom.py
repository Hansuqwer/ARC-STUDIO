"""SBOM generator for the ARC Mobile Runtime SDK (Phase 12).

Emits a CycloneDX-style (1.5) Software Bill of Materials enumerating the mobile SDK's Python
submodules (introspected at runtime) plus the framework bindings (Expo, React Native,
Flutter). Deterministic (sorted, no timestamps) so it can be diffed in CI. No network.
"""

from __future__ import annotations

import pkgutil
from typing import Any

SBOM_SPEC_VERSION = "1.5"
DEFAULT_VERSION = "0.1.0"

# Framework bindings shipped under runtimes/mobile (simulator-preview, fixtures-only).
_BINDINGS = [
    ("arc-mobile-runtime-expo", "npm", "runtimes/mobile/expo/packages/arc-mobile-runtime"),
    (
        "arc-mobile-runtime-react-native",
        "npm",
        "runtimes/mobile/react-native/packages/arc-mobile-runtime",
    ),
    ("arc_mobile_runtime-flutter", "pub", "runtimes/mobile/flutter/packages/arc_mobile_runtime"),
]


def _python_module_components(version: str) -> list[dict[str, Any]]:
    import agent_runtime_cockpit.mobile as mob

    components = []
    names = sorted({m.name for m in pkgutil.iter_modules(mob.__path__)})
    for name in names:
        components.append(
            {
                "type": "library",
                "name": f"arc-mobile.{name}",
                "version": version,
                "scope": "required",
                "purl": f"pkg:pypi/agent-runtime-cockpit@{version}#mobile.{name}",
            }
        )
    return components


def _binding_components(version: str) -> list[dict[str, Any]]:
    out = []
    for name, eco, path in _BINDINGS:
        out.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "scope": "optional",
                "purl": f"pkg:{eco}/{name}@{version}",
                "properties": [{"name": "arc:source_path", "value": path}],
            }
        )
    return out


def generate_sbom(version: str = DEFAULT_VERSION) -> dict[str, Any]:
    """Return a deterministic CycloneDX-style SBOM for the mobile SDK."""
    components = _python_module_components(version) + _binding_components(version)
    components.sort(key=lambda c: c["name"])
    return {
        "bomFormat": "CycloneDX",
        "specVersion": SBOM_SPEC_VERSION,
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "arc-mobile-runtime",
                "version": version,
            },
            "properties": [{"name": "arc:simulator_preview", "value": "true"}],
        },
        "components": components,
    }
