/**
 * ARC Mobile Runtime — React Native TurboModule Codegen spec (simulator preview).
 *
 * This is a New-Architecture TurboModule spec consumed by React Native Codegen. The native
 * implementations (iOS .mm / Android Kotlin) return FIXTURES ONLY — no real camera,
 * microphone, contacts, calendar, photos, location, files, health, background execution,
 * or OS permission requests. Nothing here grants real device access.
 */
import type { TurboModule } from "react-native";
import { TurboModuleRegistry } from "react-native";

export interface Spec extends TurboModule {
  /** Simulate a single capability — returns fixture outputs. */
  simulateAction(capabilityId: string, inputs: Object): Promise<Object>;
  /** Runtime status (mock). */
  doctor(): Promise<Object>;
  /** Permission state — always "not_requested" (no real OS permission flow). */
  getPermissionState(capabilityId: string): Promise<Object>;
}

// `getEnforcing` throws if the native module is absent; callers use the JS fixture
// fallback in index.ts for non-native contexts (Metro web, tests, bare node).
export default TurboModuleRegistry.get<Spec>("ArcMobileRuntime");
