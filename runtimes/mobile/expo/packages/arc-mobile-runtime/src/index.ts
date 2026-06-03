/**
 * ARC Mobile Runtime SDK — Expo stub.
 * MVP: mock/simulator-only. No real native bridges.
 */

export type ArcMobileCapabilityId = string;

export interface ArcMobileCapabilityStub {
  id: ArcMobileCapabilityId;
  name: string;
  isMock: true;
  simulatorSupported: true;
}

export const ARC_MOBILE_SDK_VERSION = "0.1.0";
export const ARC_MOBILE_MOCK_MODE = true;

/** Simulate an action — always mock in MVP. */
export async function simulateAction(
  capabilityId: ArcMobileCapabilityId,
  inputs: Record<string, unknown> = {}
): Promise<{ simulated: true; capability_id: string; mock: true }> {
  return { simulated: true, capability_id: capabilityId, mock: true };
}
