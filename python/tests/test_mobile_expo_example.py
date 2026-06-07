"""Tests for T3 (Phase 6): Expo example app + hardened native-safety gate.

This is the CI safety gate for the Expo package. It recursively scans EVERY native/source
file (Swift, Kotlin, TS, TSX, JS) under the package for real device/sensor APIs — so any
future file is covered, not just the two original module files — and verifies the example
app demonstrates the SDK + config plugin under the simulator-preview posture.
"""

from __future__ import annotations

import json
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
EXAMPLE = EXPO_PKG / "example"

# Real device/sensor/permission APIs that must never appear anywhere in the package.
FORBIDDEN = [
    # iOS / Swift
    "AVCaptureSession",
    "AVCaptureDevice",
    "AVAudioSession.sharedInstance",
    "CLLocationManager",
    "CNContactStore",
    "CNContact",
    "PHPhotoLibrary",
    "PHAsset",
    "EKEventStore",
    "EKEvent",
    "CMMotionManager",
    "HKHealthStore",
    "CBCentralManager",
    "requestWhenInUseAuthorization",
    "requestAlwaysAuthorization",
    # Android / Kotlin
    "CameraDevice",
    "android.hardware.Camera",
    "LocationManager",
    "FusedLocationProvider",
    "ContactsContract",
    "CalendarContract",
    "MediaStore",
    "AudioRecord",
    "MediaRecorder",
    "ActivityCompat.requestPermissions",
    # JS / Expo / RN native-access modules
    "expo-camera",
    "expo-location",
    "expo-contacts",
    "expo-calendar",
    "expo-media-library",
    "expo-av",
    "getCurrentPositionAsync",
    "requestCameraPermissionsAsync",
    "react-native-camera",
    "@react-native-community/geolocation",
]

SCAN_SUFFIXES = {".swift", ".kt", ".ts", ".tsx", ".js"}
SKIP_DIRS = {"node_modules", "build", ".expo", "lib", "dist"}


def _source_files() -> list[Path]:
    out: list[Path] = []
    for p in EXPO_PKG.rglob("*"):
        if p.is_file() and p.suffix in SCAN_SUFFIXES and not any(s in p.parts for s in SKIP_DIRS):
            out.append(p)
    return out


@pytest.mark.skipif(not EXPO_PKG.exists(), reason="Expo package absent")
def test_no_real_device_apis_anywhere() -> None:
    """Hardened gate: recursively scan all native/source files for forbidden symbols."""
    violations: list[str] = []
    files = _source_files()
    assert files, "expected to scan Expo package source files"
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for sym in FORBIDDEN:
            if sym in text:
                violations.append(f"{f.relative_to(EXPO_PKG)}: {sym}")
    assert not violations, "real device APIs found in simulator-preview package:\n" + "\n".join(
        violations
    )


@pytest.mark.skipif(not EXAMPLE.exists(), reason="example app absent")
class TestExampleApp:
    def test_example_files_exist(self) -> None:
        assert (EXAMPLE / "App.tsx").is_file()
        assert (EXAMPLE / "app.json").is_file()
        assert (EXAMPLE / "package.json").is_file()

    def test_example_uses_sdk_surface(self) -> None:
        app = (EXAMPLE / "App.tsx").read_text(encoding="utf-8")
        assert 'from "arc-mobile-runtime"' in app
        for fn in ["getCapabilities", "simulate", "addSimulationListener"]:
            assert fn in app, f"example should demonstrate {fn}"

    def test_example_wires_config_plugin(self) -> None:
        cfg = json.loads((EXAMPLE / "app.json").read_text(encoding="utf-8"))
        plugins = cfg["expo"]["plugins"]
        assert any((isinstance(p, list) and p and p[0] == "arc-mobile-runtime") for p in plugins), (
            "example app.json must use the arc-mobile-runtime config plugin"
        )

    def test_example_is_private_and_preview_labeled(self) -> None:
        pkg = json.loads((EXAMPLE / "package.json").read_text(encoding="utf-8"))
        assert pkg.get("private") is True
        assert "simulator preview" in (EXAMPLE / "App.tsx").read_text(encoding="utf-8").lower()


@pytest.mark.skipif(not EXPO_PKG.exists(), reason="Expo package absent")
def test_package_build_readiness() -> None:
    pkg = json.loads((EXPO_PKG / "package.json").read_text(encoding="utf-8"))
    assert pkg.get("private") is True, "package must stay private until publishable"
    assert "build" in pkg.get("scripts", {}), "package needs a build script"
    assert (EXPO_PKG / "app.plugin.js").is_file(), "config plugin entry must exist"
    assert (EXPO_PKG / "expo-module.config.json").is_file()
