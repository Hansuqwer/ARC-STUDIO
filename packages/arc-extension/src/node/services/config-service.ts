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

import { injectable, inject } from '@theia/core/shared/inversify';
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
    TrustStatus,
    SafeRuntimeConfig,
    SafeProviderKeyStatus,
    ProviderTestResult,
    ProviderModel,
    ArcError,
    ArcErrorCode,
} from '../../common/arc-protocol';
import { buildArcCliEnv, SAFE_CONFIG_KEYS, UNSAFE_CONFIG_KEY_PATTERN } from './arc-cli-utils';

@injectable()
export class ConfigService {
    constructor(
        @inject('WorkspaceRoot') private readonly workspaceRoot: string
    ) {}

    async getProviderStatus(provider: string, baseUrl?: string): Promise<ProviderStatus> {
        try {
            const output = execFileSync('arc', ['providers', 'status', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && Array.isArray(parsed.data)) {
                const found = parsed.data.find((p: { provider: string }) => p.provider === provider);
                if (found) return found as ProviderStatus;
            }
            // Return a default status if provider not found
            return {
                provider,
                baseUrlConfigured: !!baseUrl,
                apiKeyConfigured: false,
                runtimeAvailable: false,
                message: 'Provider not configured',
            };
        } catch (error) {
            return {
                provider,
                baseUrlConfigured: !!baseUrl,
                apiKeyConfigured: false,
                runtimeAvailable: false,
                message: `Status unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async getWorkspaceStatus(): Promise<{ frontendPath: string; backendPath: string; source: string }> {
        return {
            frontendPath: this.workspaceRoot,
            backendPath: this.workspaceRoot,
            source: 'filesystem',
        };
    }

    async getConfigStatus(): Promise<ConfigStatus> {
        const trustStatus: TrustStatus = {
            trusted: false,
            workspacePath: this.workspaceRoot,
            trustLevel: 'unknown',
            reason: 'status_unverified',
        };

        const runtimeConfig: SafeRuntimeConfig = {
            defaultRuntime: 'swarmgraph',
            autoDetect: true,
            fallback: 'stub',
            isolation: 'none',
            timeoutSeconds: 300,
            allowPaidCalls: false,
            dryRun: true,
            routingMode: 'manual',
        };

        let providers: SafeProviderKeyStatus[] = [];
        let backendAvailable = true;
        let backendMessage: string | undefined;
        let selectedProfile: string | undefined;

        try {
            const output = execFileSync('arc', ['providers', 'status', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && Array.isArray(parsed.data)) {
                providers = parsed.data.map((p: any) => ({
                    provider: p.provider || 'unknown',
                    displayName: p.display_name || p.provider || 'Unknown',
                    configured: !!p.apiKeyConfigured || !!p.api_key_configured,
                    source: p.apiKeySource || (p.apiKeyConfigured ? 'env' : 'unset'),
                    defaultModel: p.default_model,
                    envOverride: p.api_key_env,
                })) as SafeProviderKeyStatus[];
            }
        } catch (error) {
            backendAvailable = false;
            backendMessage = `Backend unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`;
            providers = [
                { provider: 'openai', displayName: 'OpenAI', configured: false, source: 'unset' },
                { provider: 'anthropic', displayName: 'Anthropic', configured: false, source: 'unset' },
                { provider: 'ollama', displayName: 'Ollama', configured: false, source: 'unset' },
            ];
        }

        try {
            const configOutput = execFileSync('arc', ['config', 'show', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const configParsed = JSON.parse(configOutput);
            if (configParsed.ok && configParsed.data) {
                const data = configParsed.data;
                if (data.runtime) {
                    runtimeConfig.defaultRuntime = data.runtime.default || runtimeConfig.defaultRuntime;
                    runtimeConfig.autoDetect = data.runtime.auto_detect ?? runtimeConfig.autoDetect;
                    runtimeConfig.fallback = data.runtime.fallback || runtimeConfig.fallback;
                }
                if (data.execution) {
                    runtimeConfig.isolation = data.execution.isolation || runtimeConfig.isolation;
                    runtimeConfig.timeoutSeconds = data.execution.timeout_seconds || runtimeConfig.timeoutSeconds;
                    runtimeConfig.allowPaidCalls = data.execution.allow_paid_calls ?? runtimeConfig.allowPaidCalls;
                }
                if (data.providers) {
                    runtimeConfig.dryRun = data.providers.dry_run ?? runtimeConfig.dryRun;
                    runtimeConfig.routingMode = data.providers.routing_mode || runtimeConfig.routingMode;
                }
                if (data.profiles) {
                    selectedProfile = data.profiles.selected_profile || data.profiles.selected || data.profiles.default;
                }
                if (data.workspace) {
                    trustStatus.trustLevel = data.workspace.trust_level || trustStatus.trustLevel;
                    trustStatus.trusted = trustStatus.trustLevel === 'trusted';
                }
            }
        } catch {
            // Config show failed; keep defaults
        }

        return {
            workspace: trustStatus,
            runtime: runtimeConfig,
            providers,
            mode: 'build',
            selectedProfile,
            backendAvailable,
            backendMessage,
        };
    }

    async saveConfig(update: SafeConfigUpdate): Promise<{ success: boolean; message: string }> {
        const safeKeys = SAFE_CONFIG_KEYS;
        const updateKeys = Object.keys(update);

        for (const key of updateKeys) {
            if (!safeKeys.includes(key) || UNSAFE_CONFIG_KEY_PATTERN.test(key)) {
                return {
                    success: false,
                    message: `Rejected unsafe config field: ${key}. Only non-secret fields are allowed.`,
                };
            }
        }

        if (updateKeys.length === 0) {
            return { success: false, message: 'No config fields to update.' };
        }

        try {
            const args = ['config', 'set'];
            if (update.defaultRuntime) {
                args.push(`runtime.default=${update.defaultRuntime}`);
            }
            if (update.mode) {
                args.push(`execution.mode=${update.mode}`);
            }
            if (update.isolation) {
                args.push(`execution.isolation=${update.isolation}`);
            }
            if (update.allowPaidCalls !== undefined) {
                args.push(`execution.allow_paid_calls=${update.allowPaidCalls}`);
            }
            if (update.dryRun !== undefined) {
                args.push(`providers.dry_run=${update.dryRun}`);
            }
            if (update.routingMode) {
                args.push(`providers.routing_mode=${update.routingMode}`);
            }
            if (update.selectedProfile) {
                args.push(`profiles.selected_profile=${update.selectedProfile}`);
            }

            execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });

            return { success: true, message: 'Configuration saved.' };
        } catch (error) {
            return {
                success: false,
                message: `Failed to save config: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async listProfiles(): Promise<ArcProfileInfo[]> {
        try {
            const output = execFileSync('arc', ['profiles', 'list', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            const profiles = Array.isArray(parsed?.data) ? parsed.data : Array.isArray(parsed?.profiles) ? parsed.profiles : [];
            return profiles.map((profile: any) => ({
                id: String(profile.id || profile.profile_id || profile.name || 'unknown'),
                name: String(profile.name || profile.id || profile.profile_id || 'Unknown'),
                mode: profile.mode,
                description: profile.description,
                allowPaidCalls: profile.allow_paid_calls ?? profile.allowPaidCalls,
                dryRun: profile.dry_run ?? profile.dryRun,
                provider: profile.provider,
                runtime: profile.runtime,
            }));
        } catch {
            return [
                { id: 'local-safe', name: 'local-safe', allowPaidCalls: false, dryRun: true },
                { id: 'local-paid', name: 'local-paid', allowPaidCalls: true, dryRun: false },
            ];
        }
    }

    async getIsolationStatus(): Promise<IsolationStatus> {
        try {
            const output = execFileSync('arc', ['isolation', 'status', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            const data = parsed?.data || parsed || {};
            return {
                current: String(data.current || data.provider || data.isolation || 'none'),
                available: data.available !== false,
                providers: this.mapIsolationProviders(data.providers || []),
                message: data.message,
            };
        } catch (error) {
            return {
                current: 'none',
                available: true,
                providers: [{ id: 'none', name: 'None', available: true, active: true }],
                message: `Isolation status unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async listIsolationProviders(): Promise<IsolationProviderInfo[]> {
        try {
            const output = execFileSync('arc', ['isolation', 'list', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            const providers = Array.isArray(parsed?.data) ? parsed.data : Array.isArray(parsed?.providers) ? parsed.providers : [];
            return this.mapIsolationProviders(providers);
        } catch {
            return [{ id: 'none', name: 'None', available: true, active: true }];
        }
    }

    async getProviderCatalog(): Promise<ProviderCatalogEntry[]> {
        const output = execFileSync('arc', ['providers', 'catalog', '--json'], {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        const parsed = JSON.parse(output);
        if (parsed.ok && Array.isArray(parsed.data)) {
            return parsed.data.map((p: any) => ({
                ...p,
                displayName: p.display_name,
                authKind: p.auth_kind,
                credentialLabel: p.credential_label,
                envKeyNames: p.env_key_names,
                defaultBaseUrl: p.default_base_url,
                docsUrl: p.docs_url,
            })) as ProviderCatalogEntry[];
        }
        return [];
    }

    async getProviderDiagnostics(): Promise<ProviderDiagnosticsInfo> {
        try {
            const output = execFileSync('arc', ['providers', 'diagnostics', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok) {
                throw new ArcError(
                    ArcErrorCode.RUN_FAILED,
                    parsed?.error?.message || 'Provider diagnostics failed',
                    { error: parsed?.error }
                );
            }
            return (parsed.data || {}) as ProviderDiagnosticsInfo;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Provider diagnostics unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    async getProviderQuota(provider?: string): Promise<ProviderQuotaInfo> {
        try {
            const args = ['providers', 'quota', 'show'];
            if (provider) {
                args.push('--provider', provider);
            }
            args.push('--json');
            const output = execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok) {
                throw new ArcError(
                    ArcErrorCode.RUN_FAILED,
                    parsed?.error?.message || 'Provider quota failed',
                    { error: parsed?.error }
                );
            }
            return (parsed.data || {}) as ProviderQuotaInfo;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Provider quota unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    async resetProviderQuota(): Promise<ProviderQuotaResetResult> {
        try {
            const output = execFileSync('arc', ['providers', 'quota', 'reset', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok) {
                throw new ArcError(
                    ArcErrorCode.RUN_FAILED,
                    parsed?.error?.message || 'Provider quota reset failed',
                    { error: parsed?.error }
                );
            }
            return {
                success: true,
                message:
                    typeof parsed?.data?.message === 'string'
                        ? parsed.data.message
                        : 'Local provider quota counters reset',
            };
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Provider quota reset unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    async runGatedProviderAction(request: GatedProviderActionRequest): Promise<GatedProviderActionResult> {
        const dryRun = request.dryRun !== false;
        const model = request.model || 'gpt-4o-mini';
        const args = ['providers', 'action', '--provider', request.provider, '--prompt', request.prompt, '--json'];
        if (model) {
            args.push('--model', model);
        }
        if (!dryRun) {
            args.push('--live');
        }
        if (request.allowPaidCalls) {
            args.push('--allow-paid-calls');
        }
        if (request.confirmProviderCall) {
            args.push('--confirm', `RUN_PROVIDER_ACTION:${request.provider}:${model}`);
        }

        try {
            const output = execFileSync('arc', args, {
                timeout: 30000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            return this.mapGatedProviderActionOutput(output, dryRun, { ...request, model });
        } catch (error: any) {
            const output = String(error?.stdout || error?.stderr || '');
            if (output.trim()) {
                return this.mapGatedProviderActionOutput(output, dryRun, { ...request, model }, true);
            }
            return {
                success: false,
                blocked: true,
                dryRun,
                providerCall: false,
                provider: request.provider,
                model,
                message: `Provider action unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async setProviderKeyRef(request: ProviderKeyRefRequest): Promise<{ success: boolean; message: string }> {
        if (/sk-|bearer\s+|token[:=]|api[_-]?key[:=]/i.test(request.envVar)) {
            return { success: false, message: 'Rejected raw key material. Enter an environment variable name only.' };
        }
        const args = ['providers', 'key', 'set', request.provider, '--env', request.envVar, '--json'];
        if (request.label) {
            args.push('--label', request.label);
        }
        if (request.model) {
            args.push('--model', request.model);
        }
        execFileSync('arc', args, {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        return { success: true, message: `Saved ${request.provider} key reference (${request.envVar}).` };
    }

    async unsetProviderKeyRef(providerOrAccountId: string): Promise<{ success: boolean; message: string }> {
        execFileSync('arc', ['providers', 'key', 'unset', providerOrAccountId, '--json'], {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        return { success: true, message: `Removed provider key reference: ${providerOrAccountId}.` };
    }

    async testProvider(providerId: string): Promise<ProviderTestResult> {
        try {
            const output = execFileSync('arc', ['providers', 'test', providerId, '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            
            if (parsed.ok && parsed.data) {
                const data = parsed.data;
                const configured = data.configured !== false;
                return {
                    provider: data.provider || providerId,
                    providerId: data.provider_id || data.providerId || providerId,
                    displayName: data.display_name || data.displayName || providerId,
                    configured,
                    status: configured ? 'success' : 'warning',
                    message: data.message || 'Provider test successful',
                    details: {
                        baseUrl: data.base_url || data.baseUrl,
                        docsUrl: data.docs_url || data.docsUrl,
                        envVars: data.env_vars || data.envVars,
                    },
                };
            }
            
            // Handle error response
            return {
                provider: providerId,
                providerId,
                displayName: providerId,
                configured: false,
                status: 'error',
                message: parsed.error?.message || 'Provider test failed',
            };
        } catch (error: any) {
            // Try to parse error output
            const output = String(error?.stdout || error?.stderr || '');
            if (output.trim()) {
                try {
                    const parsed = JSON.parse(output);
                    if (parsed.data) {
                        const data = parsed.data;
                        const configured = data.configured !== false;
                        return {
                            provider: data.provider || providerId,
                            providerId: data.provider_id || data.providerId || providerId,
                            displayName: data.display_name || data.displayName || providerId,
                            configured,
                            status: configured ? 'warning' : 'error',
                            message: data.message || parsed.error?.message || 'Provider test failed',
                            details: {
                                baseUrl: data.base_url || data.baseUrl,
                                docsUrl: data.docs_url || data.docsUrl,
                                envVars: data.env_vars || data.envVars,
                            },
                        };
                    }
                } catch {
                    // Fall through to default error
                }
            }
            
            return {
                provider: providerId,
                providerId,
                displayName: providerId,
                configured: false,
                status: 'error',
                message: `Provider test unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async listProviderModels(providerId?: string): Promise<ProviderModel[]> {
        try {
            const args = ['providers', 'models', '--json'];
            if (providerId) {
                args.push('--provider', providerId);
            }
            
            const output = execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            
            if (parsed.ok && Array.isArray(parsed.data)) {
                return parsed.data.map((model: any) => ({
                    provider: model.provider || 'unknown',
                    model: model.model || model.id || 'unknown',
                    configured: model.configured !== false,
                    capabilities: {
                        supportsTools: model.supports_tools ?? model.supportsTools,
                        supportsChat: model.supports_chat ?? model.supportsChat,
                        supportsStreaming: model.supports_streaming ?? model.supportsStreaming,
                    },
                }));
            }
            
            return [];
        } catch (error) {
            // Return empty array on error - graceful degradation
            return [];
        }
    }

    // ========== Private Helper Methods ==========

    private mapIsolationProviders(providers: any[]): IsolationProviderInfo[] {
        return providers.map((provider: any) => ({
            id: String(provider.id || provider.name || 'unknown'),
            name: String(provider.display_name || provider.name || provider.id || 'Unknown'),
            available: provider.available !== false,
            active: !!provider.active,
            reason: provider.reason || provider.message,
        }));
    }

    private mapGatedProviderActionOutput(
        output: string,
        dryRun: boolean,
        request: GatedProviderActionRequest,
        cliFailed = false
    ): GatedProviderActionResult {
        try {
            const parsed = JSON.parse(output);
            const data = parsed?.data || {};
            const error = parsed?.error;
            const ok = parsed?.ok === true && !cliFailed;
            return {
                success: ok,
                blocked: !ok || data.blocked === true,
                dryRun: data.dry_run ?? dryRun,
                providerCall: data.provider_call === true,
                provider: data.provider || request.provider,
                model: data.model || request.model,
                message: data.message || error?.message || (ok ? 'Provider action completed.' : 'Provider action blocked.'),
                quota: data.quota || data.provider_quota,
                estimatedCost: data.estimated_cost ?? null,
                data,
                error,
            };
        } catch {
            return {
                success: false,
                blocked: true,
                dryRun,
                providerCall: false,
                provider: request.provider,
                model: request.model,
                message: output.trim() || 'Provider action failed.',
            };
        }
    }
}
