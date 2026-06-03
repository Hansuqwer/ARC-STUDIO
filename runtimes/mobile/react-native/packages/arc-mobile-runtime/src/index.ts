/**
 * ARC Mobile Runtime SDK — React Native stub.
 * MVP: mock/simulator-only. No real TurboModules/JSI bridges.
 */

export type ArcMobileCapabilityId = string;
export const ARC_MOBILE_SDK_VERSION = "0.1.0";
export const ARC_MOBILE_MOCK_MODE = true;

export async function simulateAction(
  capabilityId: ArcMobileCapabilityId,
  _inputs: Record<string, unknown> = {}
): Promise<{ simulated: true; capability_id: string; mock: true }> {
  return { simulated: true, capability_id: capabilityId, mock: true };
}
