"""Tests for T7 (Phase 9): React Native TurboModule spec + Codegen scaffold (fixtures-only).

Static, CI-safe checks (the RN package is gitignored + standalone). Validates the Codegen
TurboModule spec, the `codegenConfig` wiring, the TS API + fixture fallback + capability
catalog (drift-guarded vs Python), TS<->iOS<->Android method parity, and a recursive
forbidden-symbol scan across every native/source file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RN_PKG = (
    Path(__file__).parent.parent.parent
    / "runtimes"
    / "mobile"
    / "react-native"
    / "packages"
    / "arc-mobile-runtime"
)
SPEC = RN_PKG / "src" / "NativeArcMobileRuntime.ts"
INDEX = RN_PKG / "src" / "index.ts"
IOS = RN_PKG / "ios" / "ArcMobileRuntime.mm"
ANDROID = (
    RN_PKG
    / "android"
    / "src"
    / "main"
    / "java"
    / "com"
    / "arcmobileruntime"
    / "ArcMobileRuntimeModule.kt"
)

FORBIDDEN = [
    "AVCaptureSession",
    "CLLocationManager",
    "CNContactStore",
    "PHPhotoLibrary",
    "EKEventStore",
    "CameraDevice",
    "android.hardware.Camera",
    "LocationManager",
    "ContactsContract",
    "CalendarContract",
    "MediaStore",
    "AudioRecord",
    "MediaRecorder",
    "requestWhenInUseAuthorization",
    "ActivityCompat.requestPermissions",
    "getCurrentPositionAsync",
    "react-native-camera",
    "@react-native-community/geolocation",
]
SCAN_SUFFIXES = {".ts", ".tsx", ".mm", ".m", ".h", ".kt", ".java", ".swift"}
SKIP = {"node_modules", "build", "lib", "dist"}


@pytest.mark.skipif(not RN_PKG.exists(), reason="RN package absent")
class TestRnTurboModule:
    def test_codegen_spec_is_valid_turbomodule(self) -> None:
        spec = SPEC.read_text(encoding="utf-8")
        assert "import type { TurboModule }" in spec
        assert "TurboModuleRegistry" in spec
        assert "export interface Spec extends TurboModule" in spec
        for fn in ["simulateAction", "doctor", "getPermissionState"]:
            assert fn in spec, f"spec missing method {fn}"

    def test_codegen_config_present(self) -> None:
        pkg = json.loads((RN_PKG / "package.json").read_text(encoding="utf-8"))
        cfg = pkg.get("codegenConfig")
        assert cfg and cfg.get("type") == "modules" and cfg.get("name")
        assert pkg.get("private") is True

    def test_index_uses_turbomodule_with_fallback(self) -> None:
        idx = INDEX.read_text(encoding="utf-8")
        assert 'from "./NativeArcMobileRuntime"' in idx
        assert "if (ArcMobileRuntime)" in idx  # native path
        assert "fixtureOutputs" in idx  # fallback path
        for fn in [
            "export async function simulateAction",
            "export async function simulate",
            "export function getCapabilities",
        ]:
            assert fn in idx

    def test_capability_catalog_mirrors_python_builtins(self) -> None:
        from agent_runtime_cockpit.mobile.capabilities import list_capabilities

        idx = INDEX.read_text(encoding="utf-8")
        for cap in list_capabilities():
            assert cap.id in idx, f"capability {cap.id} absent from RN catalog"

    def test_native_method_parity(self) -> None:
        ios, android = IOS.read_text(encoding="utf-8"), ANDROID.read_text(encoding="utf-8")
        for fn in ["simulateAction", "doctor", "getPermissionState"]:
            assert fn in ios, f"{fn} missing in iOS"
            assert fn in android, f"{fn} missing in Android"
        assert "not_requested" in ios and "not_requested" in android

    def test_no_real_device_apis_anywhere(self) -> None:
        violations = []
        for p in RN_PKG.rglob("*"):
            if p.is_file() and p.suffix in SCAN_SUFFIXES and not any(s in p.parts for s in SKIP):
                text = p.read_text(encoding="utf-8", errors="ignore")
                for sym in FORBIDDEN:
                    if sym in text:
                        violations.append(f"{p.relative_to(RN_PKG)}: {sym}")
        assert not violations, "real device APIs in RN simulator-preview package:\n" + "\n".join(
            violations
        )

    def test_simulator_preview_labeled(self) -> None:
        for f in [SPEC, IOS, ANDROID]:
            assert "simulator preview" in f.read_text(encoding="utf-8").lower()
