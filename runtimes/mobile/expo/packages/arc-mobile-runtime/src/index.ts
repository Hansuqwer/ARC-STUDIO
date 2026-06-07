/**
 * ARC Mobile Runtime — Expo Module TS API (simulator preview).
 *
 * Typed JS API over the native module (`ArcMobileRuntime`). The native Swift/Kotlin
 * implementations return deterministic FIXTURES ONLY — no real camera, microphone,
 * contacts, calendar, photos, location, files, health, background execution, or OS
 * permission requests. When the native module is unavailable (web, tests, bare node),
 * the same deterministic fixtures are produced in JS so behavior is identical everywhere.
 *
 * Nothing here grants real device access. See docs/mobile/REAL_VS_MOCK.md.
 */

export const ARC_MOBILE_SDK_VERSION = "0.1.0";
export const ARC_MOBILE_MOCK_MODE = true;
export const ARC_MOBILE_RUNTIME_MODE = "simulator" as const;

export type RuntimeMode = "simulator" | "mock_native" | "native_gated";
export type DataSensitivity = "none" | "low" | "medium" | "high" | "critical";

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

export interface ArcCapabilityInfo {
  id: string;
  simulated: true;
  data_sensitivity: DataSensitivity;
}

export interface ArcActionStep {
  capability_id: string;
  inputs?: Record<string, unknown>;
}

export interface ArcActionPlan {
  plan_id: string;
  steps: ArcActionStep[];
}

export interface ArcPlanResult {
  plan_id: string;
  simulated: true;
  mock: true;
  steps: ArcSimulateResult[];
}

export interface ArcSimulationEvent {
  capability_id: string;
  mock: true;
}

/** Native module contract — kept in parity with ios/ArcMobileRuntimeModule.swift + the Kotlin module. */
interface ArcMobileRuntimeNativeModule {
  simulateAction(capabilityId: string, inputs: Record<string, unknown>): ArcSimulateResult;
  doctor(): ArcDoctorResult;
  getPermissionState(capabilityId: string): { status: string; mock: true };
  addListener?(eventName: string): void;
  removeListeners?(count: number): void;
}

const SIMULATE_EVENT = "onSimulate";

/** The simulated capability catalog (mirrors the Python builtin set; all fixture-backed). */
const CAPABILITY_CATALOG: ArcCapabilityInfo[] = [
  { id: "device.camera.capture.mock", simulated: true, data_sensitivity: "high" },
  { id: "device.microphone.transcribe.mock", simulated: true, data_sensitivity: "critical" },
  { id: "device.location.current.mock", simulated: true, data_sensitivity: "high" },
  { id: "device.calendar.read.mock", simulated: true, data_sensitivity: "high" },
  { id: "device.calendar.write.mock", simulated: true, data_sensitivity: "high" },
  { id: "device.contacts.search.mock", simulated: true, data_sensitivity: "critical" },
  { id: "device.files.pick.mock", simulated: true, data_sensitivity: "medium" },
  { id: "device.photos.pick.mock", simulated: true, data_sensitivity: "high" },
  { id: "device.notifications.schedule.mock", simulated: true, data_sensitivity: "low" },
  { id: "app.memory.write.mock", simulated: true, data_sensitivity: "low" },
  { id: "app.memory.retrieve.mock", simulated: true, data_sensitivity: "low" },
  { id: "app.local_search.query.mock", simulated: true, data_sensitivity: "low" },
  { id: "app.ui.action_plan.mock", simulated: true, data_sensitivity: "none" },
];

let _nativeModule: ArcMobileRuntimeNativeModule | null | undefined;

/** Lazily resolve the native module; returns null in non-native contexts (web/tests/node). */
function getNativeModule(): ArcMobileRuntimeNativeModule | null {
  if (_nativeModule !== undefined) return _nativeModule;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { requireNativeModule } = require("expo-modules-core");
    _nativeModule = requireNativeModule("ArcMobileRuntime") as ArcMobileRuntimeNativeModule;
  } catch {
    _nativeModule = null; // fixture-fallback mode
  }
  return _nativeModule;
}

// ── JS fixture fallback (identical shape to the native fixtures) ────────────

function fixtureOutputs(capId: string, inputs: Record<string, unknown>): Record<string, unknown> {
  if (capId.startsWith("app.memory.write")) return { stored: true, key: inputs.key ?? "last", mock: true };
  if (capId.startsWith("app.memory.retrieve")) return { found: false, value: null, mock: true };
  if (capId.startsWith("device.camera")) return { uri: "fixture://mock-image.jpg", mock: true };
  if (capId.startsWith("device.location")) return { latitude: 37.7749, longitude: -122.4194, mock: true };
  if (capId.startsWith("device.microphone")) return { transcript: "Mock transcription.", mock: true };
  if (capId.startsWith("device.contacts")) return { contacts: [{ name: "Mock User" }], mock: true };
  if (capId.startsWith("device.calendar")) return { events: [{ title: "Mock Event" }], mock: true };
  if (capId.startsWith("device.photos")) return { uri: "fixture://mock-photo.jpg", mock: true };
  return { mock: true, capability_id: capId };
}

// ── Event emitter (real Expo emitter when native; JS registry as fallback) ──

type SimulationListener = (event: ArcSimulationEvent) => void;
const _fallbackListeners = new Set<SimulationListener>();
let _expoEmitter: { addListener: (e: string, l: SimulationListener) => { remove: () => void } } | null | undefined;

function getEmitter() {
  if (_expoEmitter !== undefined) return _expoEmitter;
  const native = getNativeModule();
  try {
    if (native) {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { EventEmitter } = require("expo-modules-core");
      _expoEmitter = new EventEmitter(native as object);
      return _expoEmitter;
    }
  } catch {
    /* fall through to JS registry */
  }
  _expoEmitter = null;
  return _expoEmitter;
}

/** Subscribe to simulation events. Returns a subscription with `remove()`. */
export function addSimulationListener(listener: SimulationListener): { remove: () => void } {
  const emitter = getEmitter();
  if (emitter) return emitter.addListener(SIMULATE_EVENT, listener);
  _fallbackListeners.add(listener);
  return { remove: () => _fallbackListeners.delete(listener) };
}

function emitSimulation(event: ArcSimulationEvent): void {
  // Native emits its own event via sendEvent; in fallback mode we notify JS listeners.
  if (!getNativeModule()) for (const l of _fallbackListeners) l(event);
}

// ── Public API ──────────────────────────────────────────────────────────────

/** Simulate a single capability. Native fixtures when available, identical JS fixtures otherwise. */
export async function simulateAction(
  capabilityId: string,
  inputs: Record<string, unknown> = {}
): Promise<ArcSimulateResult> {
  const native = getNativeModule();
  const result: ArcSimulateResult = native
    ? native.simulateAction(capabilityId, inputs)
    : { simulated: true, capability_id: capabilityId, mock: true, outputs: fixtureOutputs(capabilityId, inputs) };
  emitSimulation({ capability_id: capabilityId, mock: true });
  return result;
}

/** Simulate a full action plan step-by-step (all fixture-backed). */
export async function simulate(plan: ArcActionPlan): Promise<ArcPlanResult> {
  const steps: ArcSimulateResult[] = [];
  for (const step of plan.steps) {
    steps.push(await simulateAction(step.capability_id, step.inputs ?? {}));
  }
  return { plan_id: plan.plan_id, simulated: true, mock: true, steps };
}

/** List the simulated capability catalog (all fixture-backed, no real access). */
export function getCapabilities(): ArcCapabilityInfo[] {
  return CAPABILITY_CATALOG.map((c) => ({ ...c }));
}

/** Runtime status. */
export async function doctor(): Promise<ArcDoctorResult> {
  const native = getNativeModule();
  if (native) return native.doctor();
  return {
    ok: true,
    runtime_mode: ARC_MOBILE_RUNTIME_MODE,
    mock_mode: true,
    capability_count: CAPABILITY_CATALOG.length,
    note: "Simulator preview — no real native bridges.",
  };
}

/** Permission state — always "not_requested" (no real OS permission flow exists). */
export async function getPermissionState(
  capabilityId: string
): Promise<{ status: "not_requested" | "granted" | "denied"; mock: true }> {
  const native = getNativeModule();
  if (native) return native.getPermissionState(capabilityId) as { status: "not_requested"; mock: true };
  return { status: "not_requested", mock: true };
}
