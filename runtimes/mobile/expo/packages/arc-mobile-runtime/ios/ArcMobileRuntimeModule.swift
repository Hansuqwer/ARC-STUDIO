// ARC Mobile Runtime — Expo Module iOS implementation (mock-native simulator preview)
//
// SIMULATOR PREVIEW: This module returns fixture data only.
// No real camera, microphone, contacts, calendar, photos, location,
// files, health, or OS permission requests are made.
// All sensitive OS APIs are forbidden in this file.
//
// See docs/mobile/REAL_VS_MOCK.md

import ExpoModulesCore

public class ArcMobileRuntimeModule: Module {
    public func definition() -> ModuleDefinition {
        Name("ArcMobileRuntime")

        // Simulation event stream (fixtures only — never carries real device data).
        Events("onSimulate")

        Function("simulateAction") { (capabilityId: String, inputs: [String: Any]) -> [String: Any] in
            self.sendEvent("onSimulate", ["capability_id": capabilityId, "mock": true])
            return [
                "simulated": true,
                "capability_id": capabilityId,
                "mock": true,
                "outputs": self.mockOutputs(capabilityId: capabilityId, inputs: inputs)
            ]
        }

        Function("doctor") { () -> [String: Any] in
            return [
                "ok": true,
                "runtime_mode": "simulator",
                "mock_mode": true,
                "capability_count": 13,
                "note": "Simulator preview — no real native bridges."
            ]
        }

        Function("getPermissionState") { (capabilityId: String) -> [String: Any] in
            // Mock only — never requests real OS permissions
            return ["status": "not_requested", "mock": true]
        }
    }

    private func mockOutputs(capabilityId: String, inputs: [String: Any]) -> [String: Any] {
        if capabilityId.hasPrefix("device.camera") {
            return ["uri": "fixture://mock-image.jpg", "mock": true]
        }
        if capabilityId.hasPrefix("device.location") {
            return ["latitude": 37.7749, "longitude": -122.4194, "mock": true]
        }
        if capabilityId.hasPrefix("device.microphone") {
            return ["transcript": "Mock transcription.", "mock": true]
        }
        if capabilityId.hasPrefix("app.memory.write") {
            return ["stored": true, "mock": true]
        }
        if capabilityId.hasPrefix("app.memory.retrieve") {
            return ["found": false, "value": NSNull(), "mock": true]
        }
        return ["mock": true, "capability_id": capabilityId]
    }
}
