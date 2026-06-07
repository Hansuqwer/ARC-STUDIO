// ARC Mobile Runtime — Expo Module Android implementation (mock-native simulator preview)
//
// SIMULATOR PREVIEW: This module returns fixture data only.
// No real camera, microphone, contacts, calendar, photos, location,
// files, health, or OS permission requests are made.
// All sensitive OS APIs are forbidden in this file.
//
// See docs/mobile/REAL_VS_MOCK.md

package expo.modules.arcmobileruntime

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinitionBuilder

class ArcMobileRuntimeModule : Module() {
    override fun definition() = ModuleDefinition {
        Name("ArcMobileRuntime")

        // Simulation event stream (fixtures only — never carries real device data).
        Events("onSimulate")

        Function("simulateAction") { capabilityId: String, inputs: Map<String, Any?> ->
            this@ArcMobileRuntimeModule.sendEvent("onSimulate", mapOf("capability_id" to capabilityId, "mock" to true))
            mapOf(
                "simulated" to true,
                "capability_id" to capabilityId,
                "mock" to true,
                "outputs" to mockOutputs(capabilityId, inputs)
            )
        }

        Function("doctor") {
            mapOf(
                "ok" to true,
                "runtime_mode" to "simulator",
                "mock_mode" to true,
                "capability_count" to 13,
                "note" to "Simulator preview — no real native bridges."
            )
        }

        Function("getPermissionState") { capabilityId: String ->
            // Mock only — never requests real OS permissions
            mapOf("status" to "not_requested", "mock" to true)
        }
    }

    private fun mockOutputs(capabilityId: String, inputs: Map<String, Any?>): Map<String, Any?> {
        return when {
            capabilityId.startsWith("device.camera") ->
                mapOf("uri" to "fixture://mock-image.jpg", "mock" to true)
            capabilityId.startsWith("device.location") ->
                mapOf("latitude" to 37.7749, "longitude" to -122.4194, "mock" to true)
            capabilityId.startsWith("device.microphone") ->
                mapOf("transcript" to "Mock transcription.", "mock" to true)
            capabilityId.startsWith("app.memory.write") ->
                mapOf("stored" to true, "mock" to true)
            capabilityId.startsWith("app.memory.retrieve") ->
                mapOf("found" to false, "value" to null, "mock" to true)
            else -> mapOf("mock" to true, "capability_id" to capabilityId)
        }
    }
}
