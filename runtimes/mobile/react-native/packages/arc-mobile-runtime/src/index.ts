/**
 * ARC Mobile Runtime SDK — React Native (New Architecture) TS API (simulator preview).
 *
 * Routes through the `ArcMobileRuntime` TurboModule when present; otherwise produces the
 * identical deterministic fixtures in JS. Fixtures only — no real device access.
 */
import ArcMobileRuntime from "./NativeArcMobileRuntime";

export type ArcMobileCapabilityId = string;
export const ARC_MOBILE_SDK_VERSION = "0.1.0";
export const ARC_MOBILE_MOCK_MODE = true;
export const ARC_MOBILE_RUNTIME_MODE = "simulator" as const;

export interface ArcSimulateResult {
  simulated: true;
  capability_id: string;
  mock: true;
  outputs: Record<string, unknown>;
}

const CAPABILITY_IDS: ArcMobileCapabilityId[] = [
  "device.camera.capture.mock",
  "device.microphone.transcribe.mock",
  "device.location.current.mock",
  "device.calendar.read.mock",
  "device.calendar.write.mock",
  "device.contacts.search.mock",
  "device.files.pick.mock",
  "device.photos.pick.mock",
  "device.notifications.schedule.mock",
  "app.memory.write.mock",
  "app.memory.retrieve.mock",
  "app.local_search.query.mock",
  "app.ui.action_plan.mock",
];

function fixtureOutputs(capId: string): Record<string, unknown> {
  if (capId.startsWith("device.camera")) return { uri: "fixture://mock-image.jpg", mock: true };
  if (capId.startsWith("device.location")) return { latitude: 37.7749, longitude: -122.4194, mock: true };
  if (capId.startsWith("device.microphone")) return { transcript: "Mock transcription.", mock: true };
  if (capId.startsWith("app.memory.retrieve")) return { found: false, value: null, mock: true };
  if (capId.startsWith("app.memory.write")) return { stored: true, mock: true };
  return { mock: true, capability_id: capId };
}

/** Simulate one capability — TurboModule when available, identical JS fixtures otherwise. */
export async function simulateAction(
  capabilityId: ArcMobileCapabilityId,
  inputs: Record<string, unknown> = {}
): Promise<ArcSimulateResult> {
  if (ArcMobileRuntime) {
    return (await ArcMobileRuntime.simulateAction(capabilityId, inputs)) as ArcSimulateResult;
  }
  return { simulated: true, capability_id: capabilityId, mock: true, outputs: fixtureOutputs(capabilityId) };
}

/** Run a simulated action plan step-by-step. */
export async function simulate(plan: {
  plan_id: string;
  steps: { capability_id: string; inputs?: Record<string, unknown> }[];
}): Promise<{ plan_id: string; simulated: true; mock: true; steps: ArcSimulateResult[] }> {
  const steps: ArcSimulateResult[] = [];
  for (const s of plan.steps) steps.push(await simulateAction(s.capability_id, s.inputs ?? {}));
  return { plan_id: plan.plan_id, simulated: true, mock: true, steps };
}

/** The simulated capability catalog (fixtures only). */
export function getCapabilities(): ArcMobileCapabilityId[] {
  return [...CAPABILITY_IDS];
}
