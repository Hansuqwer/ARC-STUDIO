/**
 * Runtime adapter status / capability report types (DoctorAction,
 * RuntimeCapabilityReport, RuntimeCapabilitiesResponse, ProviderStatus).
 * Extracted from arc-protocol.ts (CR-027); re-exported via the barrel. Self-contained.
 */


/**
 * A doctor action for a runtime capability report.
 */
export interface DoctorAction {
    id: string;
    label: string;
    description: string;
    command: string;
    safe_to_auto_run: boolean;
}

/**
 * Capability report for a runtime adapter.
 */
export interface RuntimeCapabilityReport {
    runtime_id: string;
    runtimeId?: string;
    detected: boolean;
    can_run: boolean;
    canRun?: boolean;
    availability: string;
    reason?: string | null;
    detected_artifacts: string[];
    detectedArtifacts?: string[];
    required_env: string[];
    requiredEnv?: string[];
    version?: string | null;
    requires_paid_calls: boolean;
    requiresPaidCalls?: boolean;
    doctor_actions: DoctorAction[];
    doctorActions?: DoctorAction[];
    metadata?: Record<string, unknown>;
    traceMetadata?: Record<string, unknown>;
    gates?: Record<string, unknown>;
    realRuntimeGate?: boolean;
    providerBacked?: boolean;
}

/**
 * Response envelope for runtime capability listing.
 */
export interface RuntimeCapabilitiesResponse {
    workspace: string;
    auto_priority: string[];
    runtimes: RuntimeCapabilityReport[];
}

/**
 * Provider configuration status for the adapter status widget.
 * Secrets are never exposed as raw values — only source/status metadata.
 */
export interface ProviderStatus {
    provider: string;
    display_name?: string;
    enabled?: boolean;
    dry_run?: boolean;
    base_url_configured?: boolean;
    baseUrlConfigured: boolean;
    api_key_configured?: boolean;
    apiKeyConfigured: boolean;
    apiKeySource?: string;
    runtimeAvailable: boolean;
    message: string;
}
