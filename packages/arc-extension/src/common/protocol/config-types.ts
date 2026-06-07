/**
 * Config Tab protocol types (Session B): provider key/catalog/account status,
 * provider test/model info, workspace trust, safe runtime config, profiles, and
 * isolation status.
 *
 * Extracted from `arc-protocol.ts` (CR-027) and re-exported from it via the barrel,
 * so existing `from '../../common/arc-protocol'` imports continue to work unchanged.
 * Self-contained: these types reference only each other and primitives.
 */


/**
 * Safe provider key status shown in Config tab.
 * Never contains raw key values — only source and configured status.
 */
export interface SafeProviderKeyStatus {
    provider: string;
    displayName: string;
    configured: boolean;
    source: 'keyring' | 'env' | 'file' | 'unset';
    defaultModel?: string;
    envOverride?: string;
}

export type ProviderAuthKind =
    | 'api_key'
    | 'bearer_token'
    | 'oauth_device'
    | 'oauth_web'
    | 'web_session'
    | 'local'
    | 'research_only';

export type ProviderCatalogStatus =
    | 'supported'
    | 'env_ref_only'
    | 'oauth_planned'
    | 'research_only'
    | 'not_recommended';

/**
 * Provider auth catalog entry. Contains only metadata, never raw credentials.
 */
export interface ProviderCatalogEntry {
    id: string;
    display_name: string;
    displayName?: string;
    category: string;
    auth_kind: ProviderAuthKind;
    authKind?: ProviderAuthKind;
    credential_label: string;
    credentialLabel?: string;
    env_key_names: string[];
    envKeyNames?: string[];
    default_base_url: string;
    defaultBaseUrl?: string;
    docs_url: string;
    docsUrl?: string;
    supports_chat: boolean;
    supports_tools: boolean;
    supports_embeddings: boolean;
    supports_images: boolean;
    supports_web_auth: boolean;
    status: ProviderCatalogStatus;
    warnings: string[];
}

export interface ProviderDiagnosticsInfo {
    providers?: Record<string, unknown>[];
    routing?: Record<string, unknown>;
    accounts?: Record<string, unknown>[];
    status?: Record<string, unknown>;
    warnings?: string[];
    metadata?: Record<string, unknown>;
}

export interface ProviderQuotaInfo {
    provider?: string;
    accounts?: Record<string, unknown>[];
    quota?: Record<string, unknown>;
    counters?: Record<string, unknown>;
    warnings?: string[];
    metadata?: Record<string, unknown>;
}

export interface ProviderQuotaResetResult {
    success: boolean;
    message: string;
}

/**
 * Request to save a provider key reference. envVar is a variable name only.
 */
export interface ProviderKeyRefRequest {
    provider: string;
    envVar: string;
    label?: string;
    model?: string;
}

/**
 * Provider account info returned by getProviderAccount.
 */
export interface ProviderAccountInfo {
    id: string;
    provider: string;
    label: string;
    enabled: boolean;
    key_env_var: string | null;
    key_fingerprint: string | null;
    masked_key: string | null;
    base_url: string | null;
    default_model: string | null;
    created_at: string;
}

/**
 * Provider account update fields.
 */
export interface ProviderAccountUpdate {
    label?: string;
    default_model?: string;
    base_url?: string;
    enabled?: boolean;
}

/**
 * Provider test result from `arc providers test <id>`.
 * Shows connection status and configuration details.
 */
export interface ProviderTestResult {
    provider: string;
    providerId: string;
    displayName: string;
    configured: boolean;
    status: 'success' | 'warning' | 'error';
    message: string;
    details?: {
        baseUrl?: string;
        docsUrl?: string;
        envVars?: string[];
    };
}

/**
 * Provider model information from `arc providers models`.
 * Lists available models and their capabilities.
 */
export interface ProviderModel {
    provider: string;
    model: string;
    configured: boolean;
    capabilities?: {
        supportsTools?: boolean;
        supportsChat?: boolean;
        supportsStreaming?: boolean;
    };
}

/**
 * Workspace trust status for Config tab.
 */
export interface TrustStatus {
    trusted: boolean;
    workspacePath: string;
    trustLevel: 'trusted' | 'untrusted' | 'auto' | 'unknown';
    reason?: string;
}

/**
 * Safe runtime config snapshot for Config tab display.
 * Contains only non-secret fields.
 */
export interface SafeRuntimeConfig {
    defaultRuntime: string;
    autoDetect: boolean;
    fallback: string;
    isolation: string;
    timeoutSeconds: number;
    allowPaidCalls: boolean;
    dryRun: boolean;
    routingMode: string;
}

/**
 * Full config status response for Config tab.
 * All secret values are stripped; only source/status metadata included.
 */
export interface ConfigStatus {
    workspace: TrustStatus;
    runtime: SafeRuntimeConfig;
    providers: SafeProviderKeyStatus[];
    mode: 'plan' | 'build' | 'auto';
    selectedProfile?: string;
    backendAvailable: boolean;
    backendMessage?: string;
}

/**
 * Safe config fields that can be saved from the Config tab.
 * Excludes all secret values.
 */
export interface SafeConfigUpdate {
    defaultRuntime?: string;
    mode?: 'plan' | 'build' | 'auto';
    isolation?: string;
    allowPaidCalls?: boolean;
    dryRun?: boolean;
    routingMode?: string;
    selectedProfile?: string;
}

export interface ArcProfileInfo {
    id: string;
    name: string;
    mode?: 'plan' | 'build' | 'auto' | string;
    description?: string;
    allowPaidCalls?: boolean;
    dryRun?: boolean;
    provider?: string;
    runtime?: string;
}

export interface IsolationProviderInfo {
    id: string;
    name: string;
    available: boolean;
    active?: boolean;
    reason?: string;
}

export interface IsolationStatus {
    current: string;
    available: boolean;
    providers: IsolationProviderInfo[];
    message?: string;
}
