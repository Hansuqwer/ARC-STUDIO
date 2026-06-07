// ARC Mobile Runtime — React Native TurboModule Android implementation (simulator preview).
//
// SIMULATOR PREVIEW: returns fixture data only. No real camera, microphone, contacts,
// calendar, photos, location, files, health, or OS permission requests. All sensitive OS
// APIs are forbidden in this file (enforced by the recursive forbidden-symbol CI gate).

package com.arcmobileruntime

import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.ReadableMap
import com.facebook.react.bridge.Arguments

class ArcMobileRuntimeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "ArcMobileRuntime"

    private fun mockOutputs(capabilityId: String): com.facebook.react.bridge.WritableMap {
        val out = Arguments.createMap()
        when {
            capabilityId.startsWith("device.location") -> {
                out.putDouble("latitude", 37.7749)
                out.putDouble("longitude", -122.4194)
            }
            capabilityId.startsWith("device.camera") -> out.putString("uri", "fixture://mock-image.jpg")
            else -> out.putString("capability_id", capabilityId)
        }
        out.putBoolean("mock", true)
        return out
    }

    @ReactMethod
    fun simulateAction(capabilityId: String, inputs: ReadableMap, promise: Promise) {
        val result = Arguments.createMap()
        result.putBoolean("simulated", true)
        result.putString("capability_id", capabilityId)
        result.putBoolean("mock", true)
        result.putMap("outputs", mockOutputs(capabilityId))
        promise.resolve(result)
    }

    @ReactMethod
    fun doctor(promise: Promise) {
        val result = Arguments.createMap()
        result.putBoolean("ok", true)
        result.putString("runtime_mode", "simulator")
        result.putBoolean("mock_mode", true)
        result.putInt("capability_count", 13)
        result.putString("note", "Simulator preview — no real native bridges.")
        promise.resolve(result)
    }

    @ReactMethod
    fun getPermissionState(capabilityId: String, promise: Promise) {
        // Mock only — never requests real OS permissions.
        val result = Arguments.createMap()
        result.putString("status", "not_requested")
        result.putBoolean("mock", true)
        promise.resolve(result)
    }
}
