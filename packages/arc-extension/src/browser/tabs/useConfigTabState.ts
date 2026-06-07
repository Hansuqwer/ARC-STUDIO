/**
 * ConfigTab state + logic hook.
 * Owns all data loading, derived state, and gated action handlers for ConfigTab.
 * Presentation lives in ConfigTab.tsx; this module makes no provider network calls.
 */

import { useState, useEffect, useCallback } from '@theia/core/shared/react';
import {
    ArcProfileInfo,
    ArcService,
    ConfigStatus,
    IsolationProviderInfo,
    IsolationStatus,
    ProviderCatalogEntry,
    SafeConfigUpdate,
    RuntimeCapabilityReport,
    GatedProviderActionResult,
    ProviderTestResult,
    ProviderModel,
} from '../../common/arc-protocol';
import {
    buildLiveProviderGate,
    buildQuotaResetConfirmation,
    canResetQuota,
    parseProviderDiagnostics,
    parseQuotaCounters,
    summarizeProfileCostPolicy,
} from './provider-telemetry';
import { validateExportTarget } from './export-target';
import { buildRuntimeRemediationPlan } from './runtime-remediation';
import {
    RUNTIME_DISPLAY,
    FALLBACK_ISOLATION_OPTIONS,
    FALLBACK_PROFILE_OPTIONS,
    asObject,
} from './config-tab-helpers';

const DEFAULT_PROVIDER_ACTION_PROVIDER = '9router';
const DEFAULT_PROVIDER_ACTION_MODEL = 'qwen/qwen3-coder';
const DEFAULT_PROVIDER_ACTION_PROMPT = 'Return one short ARC Studio provider-action smoke sentence.';

type OptionalProviderTelemetryService = {
    getProviderDiagnostics?: () => Promise<unknown>;
    getProviderQuota?: (provider?: string) => Promise<unknown>;
    resetProviderQuota?: (provider?: string) => Promise<unknown>;
    confirmProviderAction?: (request: {
        provider: string;
        model?: string;
        prompt: string;
        dryRun: boolean;
        allowPaidCalls: boolean;
        confirmProviderCall: boolean;
    }) => Promise<unknown>;
};

export function useConfigTabState({ arcService }: { arcService?: ArcService }) {
    const [config, setConfig] = useState<ConfigStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState<string | null>(null);
    const [selectedRuntime, setSelectedRuntime] = useState('swarmgraph');
    const [selectedMode, setSelectedMode] = useState<'plan' | 'build' | 'auto'>('build');
    const [providerCatalog, setProviderCatalog] = useState<ProviderCatalogEntry[]>([]);
    const [selectedProvider, setSelectedProvider] = useState('openai');
    const [providerEnvVar, setProviderEnvVar] = useState('OPENAI_API_KEY');
    const [selectedIsolation, setSelectedIsolation] = useState('subprocess');
    const [selectedProfile, setSelectedProfile] = useState('local-safe');
    const [dryRun, setDryRun] = useState(true);
    const [allowPaidCalls, setAllowPaidCalls] = useState(false);
    const [capabilities, setCapabilities] = useState<RuntimeCapabilityReport[] | null>(null);
    const [capabilitiesLoading, setCapabilitiesLoading] = useState(false);
    const [profiles, setProfiles] = useState<ArcProfileInfo[]>(FALLBACK_PROFILE_OPTIONS);
    const [isolationStatus, setIsolationStatus] = useState<IsolationStatus | null>(null);
    const [isolationProviders, setIsolationProviders] = useState<IsolationProviderInfo[]>(FALLBACK_ISOLATION_OPTIONS);
    const [exportText, setExportText] = useState<string | null>(null);
    const [providerDiagnostics, setProviderDiagnostics] = useState<unknown>(null);
    const [providerQuota, setProviderQuota] = useState<unknown>(null);
    const [quotaProviderFilter, setQuotaProviderFilter] = useState('all');
    const [quotaResetting, setQuotaResetting] = useState(false);
    const [quotaResetConfirmOpen, setQuotaResetConfirmOpen] = useState(false);
    const [quotaResetPhrase, setQuotaResetPhrase] = useState('');
    const [liveProviderConfirmPhrase, setLiveProviderConfirmPhrase] = useState('');
    const [providerActionLaunching, setProviderActionLaunching] = useState(false);
    const [providerActionResult, setProviderActionResult] = useState<GatedProviderActionResult | null>(null);
    const [providerTestResults, setProviderTestResults] = useState<Map<string, ProviderTestResult>>(new Map());
    const [providerModels, setProviderModels] = useState<Map<string, ProviderModel[]>>(new Map());
    const [testingProviders, setTestingProviders] = useState(false);
    const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set());

    const loadConfig = useCallback(async () => {
        if (!arcService) {
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const status = await arcService.getConfigStatus();
            setConfig(status);
            setSelectedRuntime(status.runtime.defaultRuntime);
            setSelectedMode(status.mode);
            setSelectedIsolation(status.runtime.isolation || 'subprocess');
            setDryRun(Boolean(status.runtime.dryRun));
            setAllowPaidCalls(Boolean(status.runtime.allowPaidCalls));
            if (status.selectedProfile) {
                setSelectedProfile(status.selectedProfile);
            }
            if (arcService.getProviderCatalog) {
                const catalog = await arcService.getProviderCatalog();
                setProviderCatalog(catalog);
                if (catalog.length > 0) {
                    setSelectedProvider(catalog[0].id);
                    setProviderEnvVar(catalog[0].envKeyNames?.[0] || catalog[0].env_key_names?.[0] || '');
                }
            }
            if (arcService.listProfiles) {
                const loadedProfiles = await arcService.listProfiles();
                if (loadedProfiles.length > 0) {
                    setProfiles(loadedProfiles);
                    setSelectedProfile(currentProfile => (
                        loadedProfiles.some(profile => profile.id === currentProfile) ? currentProfile : loadedProfiles[0].id
                    ));
                }
            }
            if (arcService.getIsolationStatus) {
                const status = await arcService.getIsolationStatus();
                setIsolationStatus(status);
                setSelectedIsolation(status.current || status.providers?.find(provider => provider.active)?.id || status.providers?.[0]?.id || 'none');
            }
            if (arcService.listIsolationProviders) {
                const providers = await arcService.listIsolationProviders();
                if (providers.length > 0) {
                    setIsolationProviders(providers);
                }
            }
            const providerTelemetryService = arcService as ArcService & OptionalProviderTelemetryService;
            if (providerTelemetryService.getProviderDiagnostics) {
                setProviderDiagnostics(await providerTelemetryService.getProviderDiagnostics().catch(() => null));
            }
            if (providerTelemetryService.getProviderQuota) {
                const quotaProvider = quotaProviderFilter === 'all' ? undefined : quotaProviderFilter;
                setProviderQuota(await providerTelemetryService.getProviderQuota(quotaProvider).catch(() => null));
            }
            // Load runtime capabilities for disabled states
            setCapabilitiesLoading(true);
            if (arcService.listRuntimeCapabilities) {
                try {
                    const caps = await arcService.listRuntimeCapabilities();
                    setCapabilities(caps.runtimes || []);
                } catch {
                    setCapabilities(null);
                }
            }
            setCapabilitiesLoading(false);
        } catch {
            setConfig(null);
        } finally {
            setLoading(false);
        }
    }, [arcService, quotaProviderFilter]);

    const buildSafeExport = useCallback((): string => {
        const safeSnapshot = {
            runtime: {
                defaultRuntime: selectedRuntime,
                mode: selectedMode,
                isolation: selectedIsolation,
                dryRun,
                allowPaidCalls: dryRun ? false : allowPaidCalls,
            },
            selectedProfile,
            providers: config?.providers.map(provider => ({
                provider: provider.provider,
                configured: provider.configured,
                source: provider.source,
                defaultModel: provider.defaultModel,
                envOverride: provider.envOverride,
            })) ?? [],
            isolation: isolationStatus ? {
                current: isolationStatus.current,
                available: isolationStatus.available,
                providers: isolationProviders.map(provider => ({
                    id: provider.id,
                    available: provider.available,
                    active: provider.active,
                    reason: provider.reason,
                })),
            } : null,
        };
        return JSON.stringify(safeSnapshot, null, 2);
    }, [allowPaidCalls, config?.providers, dryRun, isolationProviders, isolationStatus, selectedIsolation, selectedMode, selectedProfile, selectedRuntime]);

    useEffect(() => {
        loadConfig();
    }, [loadConfig]);

    const handleSave = async () => {
        if (!arcService || !config) return;
        setSaving(true);
        setSaveMessage(null);
        try {
            const update: SafeConfigUpdate = {
                defaultRuntime: selectedRuntime,
                mode: selectedMode,
                isolation: selectedIsolation,
                dryRun,
                allowPaidCalls: dryRun ? false : allowPaidCalls,
                selectedProfile,
            };
            const result = await arcService.saveConfig(update);
            setSaveMessage(result.message);
            if (result.success) {
                await loadConfig();
            }
        } catch (error) {
            setSaveMessage(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setSaving(false);
        }
    };

    const testAllProviders = useCallback(async () => {
        if (!arcService || !config) return;
        
        const testProviderMethod = (arcService as any).testProvider;
        const listModelsMethod = (arcService as any).listProviderModels;
        
        if (!testProviderMethod || !listModelsMethod) return;
        
        setTestingProviders(true);
        const newTestResults = new Map<string, ProviderTestResult>();
        const newModels = new Map<string, ProviderModel[]>();
        
        try {
            // Test each configured provider
            for (const provider of config.providers) {
                try {
                    const testResult = await testProviderMethod.call(arcService, provider.provider);
                    newTestResults.set(provider.provider, testResult);
                    
                    // Load models for this provider
                    if (testResult.configured && testResult.status === 'success') {
                        const models = await listModelsMethod.call(arcService, provider.provider);
                        if (models && models.length > 0) {
                            newModels.set(provider.provider, models);
                        }
                    }
                } catch (error) {
                    // Set error result for this provider
                    newTestResults.set(provider.provider, {
                        provider: provider.provider,
                        providerId: provider.provider,
                        displayName: provider.displayName,
                        configured: false,
                        status: 'error',
                        message: `Test failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
                    });
                }
            }
            
            setProviderTestResults(newTestResults);
            setProviderModels(newModels);
        } finally {
            setTestingProviders(false);
        }
    }, [arcService, config]);

    const toggleProviderExpanded = useCallback((providerId: string) => {
        setExpandedProviders(prev => {
            const next = new Set(prev);
            if (next.has(providerId)) {
                next.delete(providerId);
            } else {
                next.add(providerId);
            }
            return next;
        });
    }, []);

    const runtimeOptionsWithCaps = Object.entries(RUNTIME_DISPLAY).map(([value, meta]) => {
        const cap = capabilities?.find(c => c.runtime_id === value) || null;
        const canRun = cap ? cap.can_run : (value === 'crewai+swarmgraph' ? true : false);
        const reason = cap?.reason || null;
        const availability = cap?.availability || (value === 'crewai+swarmgraph' ? 'runnable' : 'unknown');
        const paid = cap?.requires_paid_calls || false;
        let description: string;
        if (cap && !cap.can_run) {
            description = reason || availability.replace(/_/g, ' ');
        } else if (value === 'crewai+swarmgraph') {
            description = 'fake/offline; real provider mode gated';
        } else {
            description = meta.label.toLowerCase().includes('swarm') ? 'bundled/offline-capable' : availability;
        }
        return { value, ...meta, canRun, reason, availability, paid, description };
    });

    const diagnostics = parseProviderDiagnostics(providerDiagnostics);
    const quotaObject = asObject(providerQuota);
    const quotaCounters = parseQuotaCounters(providerQuota);
    const providerQuotaOptions = providerCatalog.length ? providerCatalog : [{ id: 'openai', displayName: 'OpenAI', display_name: 'OpenAI' } as ProviderCatalogEntry];
    const currentProfile = profiles.find(profile => profile.id === selectedProfile) || null;
    const costPolicySummary = summarizeProfileCostPolicy(currentProfile, dryRun, allowPaidCalls);
    const providerTelemetryService = arcService as ArcService & OptionalProviderTelemetryService | undefined;
    const providerDiagnosticsAvailable = Boolean(providerTelemetryService?.getProviderDiagnostics);
    const providerQuotaAvailable = Boolean(providerTelemetryService?.getProviderQuota);
    const providerActionLaunch = providerTelemetryService?.runGatedProviderAction || providerTelemetryService?.confirmProviderAction;
    const providerActionAvailable = Boolean(providerActionLaunch);
    const providerTelemetryUnavailable = !providerDiagnosticsAvailable && !providerQuotaAvailable;
    const providerTelemetryError = !providerTelemetryUnavailable && (providerDiagnostics === null || providerQuota === null);
    const providerTelemetryEmpty = providerQuotaAvailable && providerQuota !== null && quotaCounters.length === 0;
    const quotaResetAvailable = Boolean(providerTelemetryService?.resetProviderQuota) && canResetQuota(quotaObject);
    const quotaResetConfirmation = (buildQuotaResetConfirmation as (...args: unknown[]) => {
        phrase?: string;
        confirmationPhrase?: string;
        requiredPhrase?: string;
        confirmed?: boolean;
        canReset?: boolean;
        warning?: string;
        description?: string;
    })({ provider: quotaProviderFilter, typedPhrase: quotaResetPhrase, available: quotaResetAvailable });
    const quotaResetRequiredPhrase = quotaResetConfirmation.phrase || quotaResetConfirmation.confirmationPhrase || quotaResetConfirmation.requiredPhrase || 'RESET LOCAL QUOTA COUNTERS';
    const quotaResetConfirmed = quotaResetAvailable && (quotaResetConfirmation.confirmed || quotaResetConfirmation.canReset || quotaResetPhrase === quotaResetRequiredPhrase);
    const selectedRuntimeCapability = capabilities?.find(c => c.runtime_id === selectedRuntime) || null;
    const runtimeRemediationPlan = buildRuntimeRemediationPlan(selectedRuntimeCapability);
    const exportTargetValidation = validateExportTarget(selectedRuntime, {});
    const exportTargetCopyText = exportTargetValidation.envName ? `${exportTargetValidation.envName}=package.module:factory` : '';
    const liveProviderGate = (buildLiveProviderGate as (...args: unknown[]) => {
        state?: string;
        status?: string;
        label?: string;
        message?: string;
        providerCall?: boolean;
        enforcement?: string;
        requiredPhrase?: string;
        confirmed?: boolean;
        costWarning?: string;
        accountingLabel?: string;
    })({
        dryRun,
        allowPaidCalls,
        providerCall: false,
        diagnostics,
        costPolicySummary,
        provider: quotaProviderFilter === 'all' ? DEFAULT_PROVIDER_ACTION_PROVIDER : quotaProviderFilter,
        model: (currentProfile as { defaultModel?: string } | null)?.defaultModel || (config?.runtime as { defaultModel?: string } | undefined)?.defaultModel || DEFAULT_PROVIDER_ACTION_MODEL,
        liveTestsEnabled: diagnostics.liveTestsEnabled,
        backendActionAvailable: providerActionAvailable,
        confirmationText: liveProviderConfirmPhrase,
    });
    const liveProviderActionConfirmed = liveProviderGate.confirmed === true;
    const providerActionProvider = quotaProviderFilter === 'all' ? DEFAULT_PROVIDER_ACTION_PROVIDER : quotaProviderFilter;
    const providerActionModel = (currentProfile as { defaultModel?: string } | null)?.defaultModel || (config?.runtime as { defaultModel?: string } | undefined)?.defaultModel || DEFAULT_PROVIDER_ACTION_MODEL;
    const liveProviderActionDisabled = providerActionLaunching || !providerActionAvailable || !liveProviderActionConfirmed || liveProviderGate.providerCall !== false;

    const handleProviderAction = async () => {
        if (!providerActionLaunch || liveProviderActionDisabled) return;
        setProviderActionLaunching(true);
        setProviderActionResult(null);
        setSaveMessage(null);
        try {
            const result = await providerActionLaunch({
                provider: providerActionProvider,
                model: providerActionModel,
                prompt: DEFAULT_PROVIDER_ACTION_PROMPT,
                dryRun,
                allowPaidCalls: !dryRun && allowPaidCalls,
                confirmProviderCall: liveProviderActionConfirmed,
            }) as GatedProviderActionResult;
            setProviderActionResult(result);
            setSaveMessage(result.message || (result.success ? 'Narrow provider action completed.' : 'Narrow provider action blocked.'));
        } catch (error) {
            setProviderActionResult({
                success: false,
                blocked: true,
                dryRun,
                providerCall: false,
                provider: providerActionProvider,
                model: providerActionModel,
                message: `Narrow provider action failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            });
        } finally {
            setProviderActionLaunching(false);
        }
    };

    const handleResetQuota = async () => {
        if (!providerTelemetryService?.resetProviderQuota || !quotaResetConfirmed) return;
        setQuotaResetting(true);
        setSaveMessage(null);
        try {
            const quotaProvider = quotaProviderFilter === 'all' ? undefined : quotaProviderFilter;
            await providerTelemetryService.resetProviderQuota(quotaProvider);
            setSaveMessage('Local quota-counter reset complete. No provider network calls were made.');
            setQuotaResetConfirmOpen(false);
            setQuotaResetPhrase('');
            if (providerTelemetryService.getProviderQuota) {
                setProviderQuota(await providerTelemetryService.getProviderQuota(quotaProvider).catch(() => null));
            }
        } catch (error) {
            setSaveMessage(`Local quota-counter reset failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setQuotaResetting(false);
        }
    };

    const handleSaveKeyRef = async () => {
        if (!arcService?.setProviderKeyRef || !providerEnvVar.trim()) return;
        setSaving(true);
        setSaveMessage(null);
        try {
            const result = await arcService.setProviderKeyRef({
                provider: selectedProvider,
                envVar: providerEnvVar.trim(),
                label: 'ide',
            });
            setSaveMessage(result.message);
            if (result.success) {
                await loadConfig();
            }
        } catch (error) {
            setSaveMessage(`Save key reference failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setSaving(false);
        }
    };


    return {
        config,
        loading,
        saving,
        saveMessage,
        selectedRuntime,
        setSelectedRuntime,
        selectedMode,
        setSelectedMode,
        providerCatalog,
        selectedProvider,
        setSelectedProvider,
        providerEnvVar,
        setProviderEnvVar,
        selectedIsolation,
        setSelectedIsolation,
        selectedProfile,
        setSelectedProfile,
        dryRun,
        setDryRun,
        allowPaidCalls,
        setAllowPaidCalls,
        capabilities,
        capabilitiesLoading,
        profiles,
        isolationStatus,
        isolationProviders,
        exportText,
        setExportText,
        quotaProviderFilter,
        setQuotaProviderFilter,
        quotaResetting,
        quotaResetConfirmOpen,
        setQuotaResetConfirmOpen,
        quotaResetPhrase,
        setQuotaResetPhrase,
        liveProviderConfirmPhrase,
        setLiveProviderConfirmPhrase,
        providerActionLaunching,
        providerActionResult,
        providerTestResults,
        providerModels,
        testingProviders,
        expandedProviders,
        loadConfig,
        buildSafeExport,
        handleSave,
        testAllProviders,
        toggleProviderExpanded,
        runtimeOptionsWithCaps,
        diagnostics,
        quotaCounters,
        providerQuotaOptions,
        currentProfile,
        costPolicySummary,
        providerActionAvailable,
        providerTelemetryUnavailable,
        providerTelemetryError,
        providerTelemetryEmpty,
        quotaResetAvailable,
        quotaResetConfirmation,
        quotaResetRequiredPhrase,
        quotaResetConfirmed,
        selectedRuntimeCapability,
        runtimeRemediationPlan,
        exportTargetValidation,
        exportTargetCopyText,
        liveProviderGate,
        providerActionProvider,
        providerActionModel,
        liveProviderActionDisabled,
        handleProviderAction,
        handleResetQuota,
        handleSaveKeyRef,
    };
}
