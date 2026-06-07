"""Tests for T2 (Phase 6): Expo TS API + fixtures-only native bridge contract.

Static, CI-safe checks (the Expo package is gitignored + not a workspace member). Validates
the TS API routes through the native module with a fixture fallback, exposes the documented
surface (getCapabilities / simulate / simulateAction / events), keeps TS<->Swift<->Kotlin in
parity, declares the simulation event on every layer, mirrors the Python capability catalog,
and references no real device APIs.
"""

from __future__ import annotations

from pathlib import Path

EXPO_PKG = (
    Path(__file__).parent.parent.parent
    / "runtimes"
    / "mobile"
    / "expo"
    / "packages"
    / "arc-mobile-runtime"
)
TS = (EXPO_PKG / "src" / "index.ts").read_text(encoding="utf-8")
SWIFT = (EXPO_PKG / "ios" / "ArcMobileRuntimeModule.swift").read_text(encoding="utf-8")
KOTLIN = (EXPO_PKG / "android" / "ArcMobileRuntimeModule.kt").read_text(encoding="utf-8")


def test_ts_api_surface() -> None:
    for export in [
        "export async function simulateAction",
        "export async function simulate",
        "export function getCapabilities",
        "export async function doctor",
        "export async function getPermissionState",
        "export function addSimulationListener",
    ]:
        assert export in TS, f"missing TS export: {export}"


def test_ts_routes_through_native_with_fixture_fallback() -> None:
    assert 'requireNativeModule("ArcMobileRuntime")' in TS, "TS must resolve the native module"
    assert "function getNativeModule" in TS
    assert "fixtureOutputs" in TS, "TS must keep a deterministic fixture fallback"
    # both branches present: native call + fallback
    assert "native.simulateAction(" in TS
    assert "EventEmitter" in TS, "TS must use the Expo EventEmitter when native is present"


def test_simulation_event_wired_on_all_layers() -> None:
    assert '"onSimulate"' in TS or "SIMULATE_EVENT" in TS
    assert 'Events("onSimulate")' in SWIFT and 'sendEvent("onSimulate"' in SWIFT
    assert 'Events("onSimulate")' in KOTLIN and 'sendEvent("onSimulate"' in KOTLIN


def test_native_contract_parity() -> None:
    """The 3 native functions must exist in the TS interface, Swift, and Kotlin."""
    for fn in ["simulateAction", "doctor", "getPermissionState"]:
        assert fn in TS, f"{fn} missing in TS"
        assert f'Function("{fn}")' in SWIFT, f"{fn} missing in Swift"
        assert f'Function("{fn}")' in KOTLIN, f"{fn} missing in Kotlin"


def test_capability_catalog_mirrors_python_builtins() -> None:
    """Drift guard: every builtin Python capability ID appears in the TS catalog."""
    from agent_runtime_cockpit.mobile.capabilities import list_capabilities

    for cap in list_capabilities():
        assert cap.id in TS, f"capability {cap.id} absent from the Expo TS catalog"


def test_simulator_preview_labeled_and_no_real_device_apis() -> None:
    low = TS.lower()
    assert "simulator preview" in low
    assert "fixtures only" in low or "fixture" in low
    assert "no real" in low and "device access" in low
    forbidden = [
        "AVCaptureSession",
        "CLLocationManager",
        "CNContactStore",
        "PHPhotoLibrary",
        "EKEventStore",
        "getCurrentPositionAsync",
        "Camera.requestCameraPermissions",
        "expo-camera",
        "expo-location",
        "expo-contacts",
    ]
    hits = [s for s in forbidden if s in TS]
    assert not hits, f"TS references real device APIs: {hits}"
