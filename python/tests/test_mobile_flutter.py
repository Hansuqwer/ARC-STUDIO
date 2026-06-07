"""Tests for T8 (Phase 10): Flutter platform interface + Dart models (fixtures-only).

CI-safe static checks (Flutter toolchain absent in CI; `flutter analyze` + `flutter test`
are run locally — 5 Dart tests pass, analyze clean). Validates the federated platform
interface, Dart models, the capability catalog (drift-guarded vs Python), the fixtures-only
method channel, and a recursive forbidden-symbol scan of all Dart sources.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FL_PKG = (
    Path(__file__).parent.parent.parent
    / "runtimes"
    / "mobile"
    / "flutter"
    / "packages"
    / "arc_mobile_runtime"
)
LIB = FL_PKG / "lib"
MAIN = LIB / "arc_mobile_runtime.dart"
MODELS = LIB / "src" / "models.dart"
PLATFORM = LIB / "src" / "platform_interface.dart"
CHANNEL = LIB / "src" / "method_channel.dart"

FORBIDDEN = [
    "package:camera",
    "package:location",
    "package:geolocator",
    "package:contacts_service",
    "package:device_calendar",
    "package:image_picker",
    "package:permission_handler",
    "Camera(",
    "Geolocator.",
    "ContactsService",
    "AVCaptureSession",
    "CLLocationManager",
]


@pytest.mark.skipif(not FL_PKG.exists(), reason="Flutter package absent")
class TestFlutterPackage:
    def test_structure(self) -> None:
        for f in [
            MAIN,
            MODELS,
            PLATFORM,
            CHANNEL,
            FL_PKG / "test" / "arc_mobile_runtime_test.dart",
        ]:
            assert f.is_file(), f"missing {f}"

    def test_platform_interface(self) -> None:
        src = PLATFORM.read_text(encoding="utf-8")
        assert "abstract class ArcMobileRuntimePlatform" in src
        assert "static ArcMobileRuntimePlatform get instance" in src
        for fn in ["simulateAction", "doctor", "getPermissionState"]:
            assert fn in src

    def test_models_have_json_round_trip(self) -> None:
        src = MODELS.read_text(encoding="utf-8")
        for cls in ["ArcMobileCapability", "ArcMobileActionPlan", "ArcSimulateResult"]:
            assert f"class {cls}" in src
            assert f"factory {cls}.fromJson" in src
        assert "Map<String, dynamic> toJson()" in src

    def test_capability_catalog_mirrors_python_builtins(self) -> None:
        from agent_runtime_cockpit.mobile.capabilities import list_capabilities

        src = MAIN.read_text(encoding="utf-8")
        for cap in list_capabilities():
            assert cap.id in src, f"capability {cap.id} absent from Flutter catalog"

    def test_method_channel_has_fixture_fallback(self) -> None:
        src = CHANNEL.read_text(encoding="utf-8")
        assert "MethodChannel('arc_mobile_runtime')" in src
        assert "MissingPluginException" in src  # falls back to fixtures when no native plugin

    def test_no_real_device_packages(self) -> None:
        violations = []
        for p in FL_PKG.rglob("*.dart"):
            if ".dart_tool" in p.parts:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            for sym in FORBIDDEN:
                if sym in text:
                    violations.append(f"{p.relative_to(FL_PKG)}: {sym}")
        assert not violations, "real device packages/APIs in Flutter preview:\n" + "\n".join(
            violations
        )

    def test_simulator_preview_labeled(self) -> None:
        assert "simulator preview" in MAIN.read_text(encoding="utf-8").lower()
