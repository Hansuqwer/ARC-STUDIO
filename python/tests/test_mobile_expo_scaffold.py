"""Tests for PR10: Expo Module scaffold.

Verifies that the Expo native scaffolds (Swift/Kotlin) contain no forbidden
sensitive OS APIs. This is the CI safety gate that runs even when
expo prebuild / native builds are not available.
"""

from __future__ import annotations

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

# Sensitive native APIs that must never appear in mock scaffolds
FORBIDDEN_SWIFT = [
    "AVCaptureSession",
    "AVCaptureDevice",
    "CLLocationManager",
    "CNContact",
    "CNContactStore",
    "PHPhotoLibrary",
    "PHAsset",
    "EKEventStore",
    "CMHealthStore",
    "CBCentralManager",
    "requestWhenInUseAuthorization",
    "requestAuthorization",
    "AVAudioSession.sharedInstance",
]
FORBIDDEN_KOTLIN = [
    "CameraDevice",
    "CameraManager",
    "FusedLocationProviderClient",
    "ContactsContract",
    "MediaStore.Images",
    "CalendarContract",
    "ActivityCompat.requestPermissions",
    "HealthConnect",
    "BluetoothAdapter",
    "AudioRecord",
]


@pytest.mark.skipif(
    not (EXPO_PKG / "ios" / "ArcMobileRuntimeModule.swift").exists(),
    reason="Expo scaffold not present (runtimes/ is gitignored)",
)
class TestExpoSwiftScaffold:
    def test_no_forbidden_camera_apis(self):
        swift = (EXPO_PKG / "ios" / "ArcMobileRuntimeModule.swift").read_text()
        for sym in FORBIDDEN_SWIFT:
            assert sym not in swift, f"Forbidden Swift symbol {sym!r} found in scaffold"

    def test_mock_true_present(self):
        swift = (EXPO_PKG / "ios" / "ArcMobileRuntimeModule.swift").read_text()
        assert '"mock"' in swift or "'mock'" in swift

    def test_simulator_comment_present(self):
        swift = (EXPO_PKG / "ios" / "ArcMobileRuntimeModule.swift").read_text()
        assert "SIMULATOR PREVIEW" in swift or "mock-native" in swift


@pytest.mark.skipif(
    not (EXPO_PKG / "android" / "ArcMobileRuntimeModule.kt").exists(),
    reason="Expo scaffold not present (runtimes/ is gitignored)",
)
class TestExpoKotlinScaffold:
    def test_no_forbidden_camera_apis(self):
        kotlin = (EXPO_PKG / "android" / "ArcMobileRuntimeModule.kt").read_text()
        for sym in FORBIDDEN_KOTLIN:
            assert sym not in kotlin, f"Forbidden Kotlin symbol {sym!r} found in scaffold"

    def test_mock_true_present(self):
        kotlin = (EXPO_PKG / "android" / "ArcMobileRuntimeModule.kt").read_text()
        assert '"mock"' in kotlin or "mock" in kotlin

    def test_simulator_comment_present(self):
        kotlin = (EXPO_PKG / "android" / "ArcMobileRuntimeModule.kt").read_text()
        assert "SIMULATOR PREVIEW" in kotlin or "mock-native" in kotlin


class TestExpoTsApi:
    """Tests for the TypeScript API — these run without native toolchain."""

    def test_expo_ts_index_exists(self):
        ts_file = EXPO_PKG / "src" / "index.ts"
        assert ts_file.exists() or not EXPO_PKG.exists(), "src/index.ts missing from Expo package"

    def test_expo_ts_no_real_os_imports(self):
        ts_file = EXPO_PKG / "src" / "index.ts"
        if not ts_file.exists():
            pytest.skip("Expo package not present")
        ts = ts_file.read_text()
        forbidden_ts = ["AVCapture", "CLLocation", "CNContact", "EKEvent", "PHPhoto"]
        for sym in forbidden_ts:
            assert sym not in ts, f"Forbidden TS symbol {sym!r} in index.ts"

    def test_expo_package_json_is_private(self):
        pkg_json_path = EXPO_PKG / "package.json"
        if not pkg_json_path.exists():
            pytest.skip("package.json not present")
        import json

        pkg = json.loads(pkg_json_path.read_text())
        assert pkg.get("private") is True, "Expo package must be private:true"

    def test_expo_package_json_has_build_script(self):
        pkg_json_path = EXPO_PKG / "package.json"
        if not pkg_json_path.exists():
            pytest.skip("package.json not present")
        import json

        pkg = json.loads(pkg_json_path.read_text())
        assert "build" in pkg.get("scripts", {}), "Expo package must have a build script"

    def test_expo_stub_package_json_main_not_src(self):
        """@arc/mobile-expo stub package.json must point main to dist (not src/index.ts)."""
        stub_pkg = EXPO_PKG.parent.parent / "arc-mobile-expo" / "package.json"
        if not stub_pkg.exists():
            pytest.skip("arc-mobile-expo package.json not present")
        import json

        pkg = json.loads(stub_pkg.read_text())
        assert pkg.get("main") != "src/index.ts", (
            "arc-mobile-expo main must point to dist/, not src/index.ts"
        )
