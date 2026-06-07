"""Tests for T1 (Phase 6): Expo config plugin — advisory permission injection.

The Expo package lives under gitignored `runtimes/` and is not a pnpm workspace member,
so (like test_mobile_expo_scaffold.py) these are CI-safe checks that run from the Python
suite. They validate the permission map is complete + correctly formatted, the plugin is
advisory/simulator-preview labeled, references no real device APIs, and — when node is
available — actually injects the expected advisory permissions.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

EXPO_PKG = (
    Path(__file__).parent.parent.parent
    / "runtimes"
    / "mobile"
    / "expo"
    / "packages"
    / "arc-mobile-runtime"
)
PLUGIN_JS = EXPO_PKG / "app.plugin.js"
PERM_MAP = EXPO_PKG / "plugin" / "arc-permission-map.json"


@pytest.fixture(scope="module")
def perm_map() -> dict:
    data = json.loads(PERM_MAP.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def test_plugin_and_map_exist() -> None:
    assert PLUGIN_JS.is_file(), "app.plugin.js missing"
    assert PERM_MAP.is_file(), "arc-permission-map.json missing"


def test_map_covers_every_builtin_capability_permission(perm_map: dict) -> None:
    """Drift guard: any permission a builtin capability requires must be mapped."""
    from agent_runtime_cockpit.mobile.capabilities import list_capabilities

    required = {p.id for cap in list_capabilities() for p in cap.required_permissions}
    missing = sorted(required - set(perm_map))
    assert not missing, f"permission IDs absent from the Expo config-plugin map: {missing}"


def test_map_entries_are_well_formed(perm_map: dict) -> None:
    for arc_id, entry in perm_map.items():
        assert entry["platform"] in {"ios", "android"}, arc_id
        key = entry["manifestKey"]
        if entry["platform"] == "ios":
            assert key.startswith("NS") and key.endswith("UsageDescription"), key
            assert entry.get("label"), f"iOS entry {arc_id} needs a human-readable label"
        else:
            assert key.startswith("android.permission."), key


def test_plugin_is_advisory_and_simulator_labeled() -> None:
    src = PLUGIN_JS.read_text(encoding="utf-8")
    assert "withArcMobileRuntime" in src
    low = src.lower()
    assert "advisory" in low
    assert "simulator preview" in low
    assert "no real device access" in low
    assert "human review" in low


def test_plugin_references_no_real_device_apis() -> None:
    """The advisory plugin must not reference real OS capture/sensor APIs."""
    forbidden = [
        "AVCaptureSession",
        "CLLocationManager",
        "CNContactStore",
        "PHPhotoLibrary",
        "EKEventStore",
        "requestWhenInUseAuthorization",
        "getCurrentPositionAsync",
        "MediaStore",
        "LocationManager",
    ]
    src = PLUGIN_JS.read_text(encoding="utf-8")
    hits = [s for s in forbidden if s in src]
    assert not hits, f"config plugin references real device APIs: {hits}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_plugin_injects_expected_advisory_permissions(perm_map: dict) -> None:
    """Behavioral: run the real plugin and assert it injects advisory entries."""
    script = f"""
      const plugin = require({json.dumps(str(PLUGIN_JS))});
      const out = plugin({{}}, {{ permissions: ["ios.camera", "android.CAMERA", "unknown.bogus"] }});
      process.stdout.write(JSON.stringify(out));
    """
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    # iOS usage string injected + advisory-labeled
    cam = out["ios"]["infoPlist"]["NSCameraUsageDescription"]
    assert "ARC advisory" in cam and "no real device access" in cam
    # Android permission injected
    assert "android.permission.CAMERA" in out["android"]["permissions"]
    # unknown id ignored (allowlist-only)
    assert "unknown.bogus" not in out["extra"]["arcMobileRuntimeAdvisory"]["injectedPermissionIds"]
    assert out["extra"]["arcMobileRuntimeAdvisory"]["simulatorPreview"] is True
