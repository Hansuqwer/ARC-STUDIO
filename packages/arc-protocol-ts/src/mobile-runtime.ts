/**
 * ARC Mobile Runtime SDK — TypeScript mirror of Python mobile/models.py
 *
 * Local-first, privacy-first, simulator-first. Schema version 1.
 * All MVP capabilities are mock/simulator-only.
 */

export const MOBILE_SCHEMA_VERSION = 1;

export type MobilePlatform = "ios" | "android" | "flutter" | "expo" | "react_native" | "web" | "all";
export type MobileDataSensitivity = "none" | "low" | "medium" | "high" | "critical";
export type MobileApprovalMode = "none" | "recommended" | "required" | "blocking";
export type MobileCapabilityCategory = "device" | "app" | "network" | "storage" | "ui" | "sensor" | "media" | "communication";

export interface MobilePermissionRequirement {
  id: string;
  platform: MobilePlatform;
  required: boolean;
  reason?: string;
  mock_safe: boolean;
}

export interface MobileCapability {
  schema_version: number;
  id: string;
  name: string;
  description: string;
  category: MobileCapabilityCategory;
  platforms: MobilePlatform[];
  required_permissions: MobilePermissionRequirement[];
  approval_mode: MobileApprovalMode;
  data_sensitivity: MobileDataSensitivity;
  reads: boolean;
  writes: boolean;
  network: boolean;
  paid: boolean;
  background: boolean;
  replayable: boolean;
  auditable: boolean;
  mcp_exposable: boolean;
  simulator_supported: boolean;
  test_fixture_supported: boolean;
  requires_trust: boolean;
  requires_hitl: boolean;
  metadata: Record<string, unknown>;
  capability_hash?: string;
}

export interface MobilePlatformSupport {
  platform: MobilePlatform;
  min_os_version?: string;
  stub_only: boolean;
  framework?: string;
}

export interface MobileRuntimeManifest {
  schema_version: number;
  id: string;
  name: string;
  version: string;
  description: string;
  platforms: MobilePlatformSupport[];
  capabilities: MobileCapability[];
  background_execution: boolean;
  network_by_default: boolean;
  simulator_mode: boolean;
  privacy_manifest: boolean;
  manifest_hash?: string;
}

export interface MobileActionStep {
  step_id: string;
  capability_id: string;
  description: string;
  mock: boolean;
  inputs: Record<string, unknown>;
  expected_outputs: Record<string, unknown>;
}

export interface MobileActionPlan {
  schema_version: number;
  plan_id: string;
  name: string;
  steps: MobileActionStep[];
  requires_network: boolean;
  requires_background: boolean;
  plan_hash?: string;
}

export interface MobileSimulationStepResult {
  step_id: string;
  capability_id: string;
  allowed: boolean;
  mock: boolean;
  blocked_reason?: string;
  predicted_permissions: string[];
  predicted_approvals: string[];
  audit_required: boolean;
  replayable: boolean;
}

export interface MobileActionSimulationReport {
  schema_version: number;
  plan_id: string;
  overall_allowed: boolean;
  steps: MobileSimulationStepResult[];
  blocked_steps: string[];
  requires_permissions: string[];
  requires_approvals: string[];
  risk_level: string;
  warnings: string[];
  report_hash?: string;
}

// ── Type guards ───────────────────────────────────────────────────────────────

export function isMobileCapability(obj: unknown): obj is MobileCapability {
  return typeof obj === "object" && obj !== null && "id" in obj && "simulator_supported" in obj;
}

export function isMobileRuntimeManifest(obj: unknown): obj is MobileRuntimeManifest {
  return typeof obj === "object" && obj !== null && "capabilities" in obj && "simulator_mode" in obj;
}

export function isMockCapability(cap: MobileCapability): boolean {
  return cap.id.endsWith(".mock") && cap.simulator_supported;
}
