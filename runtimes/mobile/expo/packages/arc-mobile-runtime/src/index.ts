/**
 * ARC Mobile Runtime — Expo Module (mock-native simulator preview).
 *
 * SIMULATOR PREVIEW: All operations return mock/fixture data.
 * No real camera, microphone, contacts, calendar, photos, location,
 * files, health, background execution, or OS permission requests exist.
 *
 * See docs/mobile/REAL_VS_MOCK.md for the full status matrix.
 */

export const ARC_MOBILE_SDK_VERSION = "0.1.0";
export const ARC_MOBILE_MOCK_MODE = true;
export const ARC_MOBILE_RUNTIME_MODE = "simulator" as const;

export type RuntimeMode = "simulator" | "mock_native" | "native_gated";

export interface ArcSimulateResult {
  simulated: true;
  capability_id: string;
  mock: true;
  outputs: Record<string, unknown>;
}

export interface ArcDoctorResult {
  ok: boolean;
  runtime_mode: RuntimeMode;
  mock_mode: boolean;
  capability_count: number;
  note: string;
}

/**
 * Simulate a mobile action — always returns fixture data in MVP.
 * Never requests OS permissions, never accesses real device APIs.
 */
export async function simulateAction(
  capabilityId: string,
  inputs: Record<string, unknown> = {}
): Promise<ArcSimulateResult> {
  // Mock implementation — returns fixture outputs
  const outputs = _mockOutputs(capabilityId, inputs);
  return { simulated: true, capability_id: capabilityId, mock: true, outputs };
}

/**
 * Get runtime status (mock).
 */
export async function doctor(): Promise<ArcDoctorResult> {
  return {
    ok: true,
    runtime_mode: ARC_MOBILE_RUNTIME_MODE,
    mock_mode: true,
    capability_count: 13,
    note: "Simulator preview — no real native bridges.",
  };
}

/**
 * Get current permission state for a capability (mock — always returns "not_requested").
 */
export async function getPermissionState(
  capabilityId: string
): Promise<{ status: "not_requested" | "granted" | "denied"; mock: true }> {
  void capabilityId;
  return { status: "not_requested", mock: true };
}

// ── Internal fixture router ────────────────────────────────────────────────

function _mockOutputs(capId: string, inputs: Record<string, unknown>): Record<string, unknown> {
  if (capId.startsWith("app.memory.write")) {
    return { stored: true, key: inputs.key ?? "last" };
  }
  if (capId.startsWith("app.memory.retrieve")) {
    return { found: false, value: null, mock: true };
  }
  if (capId.startsWith("device.camera")) {
    return { uri: "fixture://mock-image.jpg", mock: true };
  }
  if (capId.startsWith("device.location")) {
    return { latitude: 37.7749, longitude: -122.4194, mock: true };
  }
  if (capId.startsWith("device.microphone")) {
    return { transcript: "Mock transcription.", mock: true };
  }
  if (capId.startsWith("device.contacts")) {
    return { contacts: [{ name: "Mock User" }], mock: true };
  }
  if (capId.startsWith("device.calendar")) {
    return { events: [{ title: "Mock Event" }], mock: true };
  }
  if (capId.startsWith("device.photos")) {
    return { uri: "fixture://mock-photo.jpg", mock: true };
  }
  if (capId.startsWith("device.notifications")) {
    return { scheduled: true, mock: true };
  }
  if (capId.startsWith("device.files")) {
    return { uri: "fixture://mock-file.txt", mock: true };
  }
  return { mock: true, capability_id: capId };
}
