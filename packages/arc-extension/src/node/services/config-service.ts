/**
 * ConfigService - Provider and workspace configuration management
 * 
 * Handles:
 * - Provider status, catalog, diagnostics, quota
 * - Workspace and config status
 * - Profile management
 * - Isolation provider configuration
 * - Provider key references
 */

import { injectable } from '@theia/core/shared/inversify';
import { execFileSync } from 'child_process';
import {
    ProviderStatus,
    ConfigStatus,
    ArcProfileInfo,
    IsolationProviderInfo,
    IsolationStatus,
    SafeConfigUpdate,
    ProviderCatalogEntry,
    ProviderDiagnosticsInfo,
    ProviderQuotaInfo,
    ProviderQuotaResetResult,
    ProviderKeyRefRequest,
    GatedProviderActionRequest,
    GatedProviderActionResult,
} from '../../common/arc-protocol';

const ARC_CLI_ENV_ALLOWLIST = ['PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR'];

function buildArcCliEnv(): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {};
    for (const key of ARC_CLI_ENV_ALLOWLIST) {
        const value = process.env[key];
        if (value !== undefined) {
            env[key] = value;
        }
    }
    return env;
}

@injectable()
export class ConfigService {
    // Methods will be moved from ArcBackendService in subsequent commits
    
    async getProviderStatus(provider: string, baseUrl?: string): Promise<ProviderStatus> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getWorkspaceStatus(): Promise<{ frontendPath: string; backendPath: string; source: string }> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getConfigStatus(): Promise<ConfigStatus> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async saveConfig(update: SafeConfigUpdate): Promise<{ success: boolean; message: string }> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async listProfiles(): Promise<ArcProfileInfo[]> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getIsolationStatus(): Promise<IsolationStatus> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async listIsolationProviders(): Promise<IsolationProviderInfo[]> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getProviderCatalog(): Promise<ProviderCatalogEntry[]> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getProviderDiagnostics(): Promise<ProviderDiagnosticsInfo> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async getProviderQuota(provider?: string): Promise<ProviderQuotaInfo> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async resetProviderQuota(): Promise<ProviderQuotaResetResult> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async runGatedProviderAction(request: GatedProviderActionRequest): Promise<GatedProviderActionResult> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async setProviderKeyRef(request: ProviderKeyRefRequest): Promise<{ success: boolean; message: string }> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }

    async unsetProviderKeyRef(providerOrAccountId: string): Promise<{ success: boolean; message: string }> {
        // TODO: Move implementation from ArcBackendService
        throw new Error('Not yet implemented');
    }
}
