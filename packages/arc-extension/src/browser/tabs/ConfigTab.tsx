/**
 * Config Tab — v0.1 minimal config UI.
 *
 * Displays runtime, mode, workspace trust state, and provider key status.
 * Secrets are shown only as source/status — never raw values.
 * Gracefully handles unavailable backend.
 */

import * as React from '@theia/core/shared/react';
import { useState, useEffect, useCallback } from '@theia/core/shared/react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import {
    ArcProfileInfo,
    ArcService,
    ConfigStatus,
    IsolationProviderInfo,
    IsolationStatus,
    ProviderCatalogEntry,
    SafeConfigUpdate,
    RuntimeCapabilityReport,
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

export interface ConfigTabProps {
    arcService?: ArcService;
    onSave?: (update: SafeConfigUpdate) => void;
}

const RUNTIME_DISPLAY: Record<string, { label: string; badge: string }> = {
    'swarmgraph': { label: 'SwarmGraph', badge: 'SG' },
    'langgraph': { label: 'LangGraph', badge: 'LG' },
    'crewai': { label: 'CrewAI', badge: 'CR' },
    'crewai+swarmgraph': { label: 'CrewAI + SwarmGraph', badge: 'CS' },
    'openai-agents': { label: 'OpenAI Agents', badge: 'OA' },
    'ag2': { label: 'AG2', badge: 'A2' },
};

const MODE_OPTIONS = [
    { value: 'plan' as const, label: 'Plan', description: 'read-only' },
    { value: 'build' as const, label: 'Build', description: 'edit' },
    { value: 'auto' as const, label: 'Auto', description: 'policy-driven' },
];

const FALLBACK_ISOLATION_OPTIONS: IsolationProviderInfo[] = [
    { id: 'none', name: 'None', available: true },
    { id: 'subprocess', name: 'Subprocess', available: true },
    { id: 'docker', name: 'Docker', available: false, reason: 'status unknown' },
];

const FALLBACK_PROFILE_OPTIONS: ArcProfileInfo[] = [
    { id: 'local-safe', name: 'local-safe', allowPaidCalls: false, dryRun: true },
    { id: 'local-paid', name: 'local-paid', allowPaidCalls: true, dryRun: false },
];

const PROVIDER_DISPLAY: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    azure: 'Azure OpenAI',
    bedrock: 'Bedrock',
    vertex: 'Vertex',
    ollama: 'Ollama',
};

type JsonObject = Record<string, unknown>;
type OptionalProviderTelemetryService = {
    getProviderDiagnostics?: () => Promise<unknown>;
    getProviderQuota?: (provider?: string) => Promise<unknown>;
    resetProviderQuota?: (provider?: string) => Promise<unknown>;
};

function asObject(value: unknown): JsonObject | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : null;
}

function providerSourceBadge(source: string): string {
    switch (source) {
        case 'keyring': return 'keyring';
        case 'env': return 'env';
        case 'file': return 'file';
        default: return 'unset';
    }
}

function providerSourceColor(source: string): string {
    switch (source) {
        case 'keyring': return '#66bb6a';
        case 'env': return '#4fc3f7';
        case 'file': return '#ffb74d';
        default: return '#999';
    }
}

export const ConfigTab: React.FC<ConfigTabProps> = ({ arcService, onSave }) => {
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
    })({
        dryRun,
        allowPaidCalls,
        providerCall: false,
        diagnostics,
        costPolicySummary,
        provider: quotaProviderFilter === 'all' ? diagnostics.routingDefault : quotaProviderFilter,
    });

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

    if (loading) {
        return (
            <div className='arc-studio-config' role='region' aria-label='Config panel'>
                <div className='arc-studio-config__loading' style={{ padding: '16px', color: 'var(--theia-descriptionForeground)', textAlign: 'center' }}>
                    Loading configuration...
                </div>
            </div>
        );
    }

    if (!config || !config.backendAvailable) {
        return (
            <div className='arc-studio-config' role='region' aria-label='Config panel'>
                <div className='arc-studio-config__unavailable' style={{ padding: '16px' }}>
                    <h3>Config</h3>
                    <p style={{ color: 'var(--theia-errorForeground)', fontSize: '13px' }}>
                        Backend unavailable. {config?.backendMessage || 'Start the ARC daemon to manage configuration.'}
                    </p>
                    <button
                        className='arc-studio-config__retry'
                        onClick={loadConfig}
                        style={{ marginTop: '8px', padding: '4px 12px' }}
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className='arc-studio-config' role='region' aria-label='Config panel'>
            <div className='arc-studio-config__header' style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>Config</h3>
                <button
                    className='arc-studio-config__save'
                    onClick={handleSave}
                    disabled={saving}
                    aria-label='Save configuration'
                    style={{ padding: '4px 12px', fontSize: '12px' }}
                >
                    {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                    className='arc-studio-config__export-safe'
                    onClick={() => setExportText(buildSafeExport())}
                    aria-label='Export safe configuration snapshot'
                    style={{ padding: '4px 12px', fontSize: '12px', marginLeft: '8px' }}
                >
                    Export safe snapshot
                </button>
            </div>

            {saveMessage && (
                <div className='arc-studio-config__message' style={{ padding: '6px 16px', fontSize: '12px', color: 'var(--theia-descriptionForeground)', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                    {saveMessage}
                </div>
            )}

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Runtime</h4>
                <div className='arc-studio-config__radio-group' style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {runtimeOptionsWithCaps.map(opt => {
                        const disabled = !opt.canRun;
                        return (
                            <label key={opt.value} style={{
                                display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px',
                                cursor: disabled ? 'not-allowed' : 'pointer',
                                opacity: disabled ? 0.55 : 1,
                            }}
                            title={disabled ? opt.description : ''}
                            >
                                <input
                                    type='radio'
                                    name='runtime'
                                    value={opt.value}
                                    checked={selectedRuntime === opt.value}
                                    onChange={() => !disabled && setSelectedRuntime(opt.value)}
                                    disabled={disabled}
                                />
                                <span style={{
                                    display: 'inline-block',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    fontSize: '10px',
                                    fontFamily: 'monospace',
                                    backgroundColor: disabled ? 'var(--theia-badge-background)' : 'var(--theia-badge-background)',
                                    color: disabled ? 'var(--theia-descriptionForeground)' : 'var(--theia-badge-foreground)',
                                    minWidth: '20px',
                                    textAlign: 'center',
                                }}>{opt.badge}</span>
                                <span>{opt.label}</span>
                                <span style={{
                                    fontSize: '11px',
                                    color: disabled ? 'var(--theia-editorWarning-foreground)' : 'var(--theia-descriptionForeground)',
                                }}>
                                    {disabled ? `⛔ ${opt.description}` : opt.description}
                                </span>
                            </label>
                        );
                    })}
                </div>
            </div>

            <div className='arc-studio-config__section arc-studio-config__runtime-setup-wizard' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Runtime Setup Wizard</h4>
                <p style={{ margin: '0 0 6px', fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
                    {runtimeRemediationPlan.summary}
                </p>
                <p style={{ margin: '0 0 6px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    No raw secrets are captured or displayed. Env var names only; values stay in your shell/keychain.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px', fontSize: '11px' }}>
                    <span style={{ fontFamily: 'monospace' }}>runtime: {selectedRuntime}</span>
                    <span style={{ fontFamily: 'monospace' }}>status: {runtimeRemediationPlan.status}</span>
                    <span style={{ fontFamily: 'monospace' }}>setup: {selectedRuntimeCapability?.can_run ? 'detected' : 'needs setup'}</span>
                    {capabilitiesLoading && <span>refreshing...</span>}
                </div>
                {selectedRuntimeCapability && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px', marginBottom: '8px', fontSize: '11px' }}>
                        <div>
                            <strong>Required env names</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {selectedRuntimeCapability.required_env.length > 0 ? selectedRuntimeCapability.required_env.join(', ') : 'none'}
                            </div>
                        </div>
                        <div>
                            <strong>Detected artifacts</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {runtimeRemediationPlan.artifacts.length > 0 ? runtimeRemediationPlan.artifacts.join(', ') : 'none'}
                            </div>
                        </div>
                        <div>
                            <strong>Doctor actions</strong>
                            <div style={{ marginTop: '4px', fontFamily: 'monospace', color: 'var(--theia-descriptionForeground)' }}>
                                {selectedRuntimeCapability.doctor_actions.length > 0 ? `${selectedRuntimeCapability.doctor_actions.length} available` : 'none'}
                            </div>
                        </div>
                    </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {exportTargetValidation.envName && (
                        <div className='arc-studio-config__export-target-guidance' style={{ padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', backgroundColor: 'var(--theia-editor-background)', fontSize: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'flex-start' }}>
                                <div>
                                    <strong>Export target env-ref</strong>
                                    <span className='arc-studio-config__export-target-status' style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--theia-descriptionForeground)', fontFamily: 'monospace' }}>
                                        {exportTargetValidation.status}
                                    </span>
                                </div>
                                <button
                                    className='arc-studio-config__export-target-copy'
                                    onClick={() => navigator.clipboard?.writeText(exportTargetCopyText)}
                                    style={{ fontSize: '11px' }}
                                >
                                    Copy env-ref
                                </button>
                            </div>
                            <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                                {exportTargetValidation.message} Configure the shell/env only; ARC does not save export target values.
                            </p>
                            <div className='arc-studio-config__export-target-env' style={{ marginTop: '4px', fontSize: '11px' }}>
                                Env ref: <span style={{ fontFamily: 'monospace' }}>{exportTargetValidation.envName}</span>
                            </div>
                            <code className='arc-studio-config__export-target-module' style={{ display: 'block', marginTop: '4px', padding: '4px 6px', fontSize: '11px', whiteSpace: 'pre-wrap', backgroundColor: 'var(--theia-input-background)' }}>
                                {exportTargetCopyText}
                            </code>
                            <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                                {exportTargetValidation.remediation}
                            </p>
                        </div>
                    )}
                    {runtimeRemediationPlan.steps.length > 0 ? runtimeRemediationPlan.steps.map(step => {
                        const copyText = step.copyText || step.command || '';
                        const canCopy = Boolean(step.copyText || step.command);
                        return (
                            <div key={step.id} className='arc-studio-config__runtime-remediation-step' style={{ padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', backgroundColor: 'var(--theia-editor-background)', fontSize: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'flex-start' }}>
                                    <div>
                                        <strong>{step.title}</strong>
                                        <span style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--theia-descriptionForeground)', fontFamily: 'monospace' }}>{step.kind}</span>
                                    </div>
                                    {canCopy && (
                                        <button
                                            className='arc-studio-config__runtime-remediation-copy'
                                            onClick={() => navigator.clipboard?.writeText(copyText)}
                                            style={{ fontSize: '11px' }}
                                        >
                                            Copy
                                        </button>
                                    )}
                                </div>
                                <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>{step.description}</p>
                                {step.envVars && step.envVars.length > 0 && (
                                    <div style={{ marginTop: '4px', fontSize: '11px' }}>
                                        Env refs: <span style={{ fontFamily: 'monospace' }}>{step.envVars.join(', ')}</span>
                                    </div>
                                )}
                                {step.command && (
                                    <code className='arc-studio-config__runtime-remediation-command' style={{ display: 'block', marginTop: '4px', padding: '4px 6px', fontSize: '11px', whiteSpace: 'pre-wrap', backgroundColor: 'var(--theia-input-background)' }}>
                                        {step.command}
                                    </code>
                                )}
                            </div>
                        );
                    }) : (
                        <div className='arc-studio-config__runtime-remediation-step' style={{ fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
                            No remediation steps available. Refresh runtime capabilities after installing dependencies.
                        </div>
                    )}
                </div>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Mode</h4>
                <div className='arc-studio-config__radio-group' style={{ display: 'flex', gap: '8px' }}>
                    {MODE_OPTIONS.map(opt => (
                        <label key={opt.value} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '13px',
                            cursor: 'pointer',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            backgroundColor: selectedMode === opt.value ? 'var(--theia-list-activeSelectionBackground)' : 'transparent',
                            color: selectedMode === opt.value ? 'var(--theia-list-activeSelectionForeground)' : 'var(--theia-foreground)',
                        }}>
                            <input
                                type='radio'
                                name='mode'
                                value={opt.value}
                                checked={selectedMode === opt.value}
                                onChange={() => setSelectedMode(opt.value)}
                            />
                            <span>{opt.label}</span>
                            <span style={{ fontSize: '11px', opacity: 0.7 }}>({opt.description})</span>
                        </label>
                    ))}
                </div>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Workspace Trust</h4>
                <p className={config.workspace.trusted ? 'arc-studio-config__trusted' : 'arc-studio-config__untrusted'} style={{
                    margin: 0,
                    fontSize: '13px',
                    color: config.workspace.trusted ? 'var(--theia-terminal-ansiGreen)' : 'var(--theia-errorForeground)',
                }}>
                    {config.workspace.trusted ? '✓' : '✗'} Workspace {config.workspace.trusted ? 'trusted' : 'not trusted'}
                </p>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)', fontFamily: 'monospace' }}>
                    {config.workspace.workspacePath}
                </p>
                <p style={{ margin: '2px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Trust level: {config.workspace.trustLevel}
                </p>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Run Policy</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', fontSize: '12px' }}>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        Isolation
                        <select
                            className='arc-studio-config__isolation-select'
                            value={selectedIsolation}
                            onChange={e => setSelectedIsolation(e.currentTarget.value)}
                        >
                            {isolationProviders.map(provider => (
                                <option key={provider.id} value={provider.id} disabled={!provider.available}>
                                    {provider.name || provider.id}{provider.available ? '' : ` — ${provider.reason || 'unavailable'}`}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        Profile
                        <select
                            className='arc-studio-config__profile-select'
                            value={selectedProfile}
                            onChange={e => setSelectedProfile(e.currentTarget.value)}
                        >
                            {profiles.map(profile => (
                                <option key={profile.id} value={profile.id}>
                                    {profile.name || profile.id}{profile.dryRun ? ' — dry-run' : ''}{profile.allowPaidCalls ? ' — paid allowed' : ''}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className='arc-studio-config__dry-run-toggle' style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <input
                            type='checkbox'
                            checked={dryRun}
                            onChange={e => {
                                const next = e.currentTarget.checked;
                                setDryRun(next);
                                if (next) setAllowPaidCalls(false);
                            }}
                        />
                        Dry run (providerCall:false)
                    </label>
                    <label className='arc-studio-config__paid-calls-toggle' style={{ display: 'flex', alignItems: 'center', gap: '6px', opacity: dryRun ? 0.6 : 1 }}>
                        <input
                            type='checkbox'
                            checked={!dryRun && allowPaidCalls}
                            disabled={dryRun}
                            onChange={e => setAllowPaidCalls(e.currentTarget.checked)}
                        />
                        Request backend paid-call opt-in (no provider call here)
                    </label>
                </div>
                <p className='arc-studio-config__run-policy-note' style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    YAML-backed safe config save persists runtime, mode, isolation, dry-run, paid-call opt-in, and selected profile. Dry-run saves force paid calls off; provider auth remains env-var references only.
                </p>
                <p className='arc-studio-config__safe-fields-summary' style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Safe fields only: defaultRuntime={selectedRuntime}, mode={selectedMode}, isolation={selectedIsolation}, selectedProfile={selectedProfile}; no raw secrets or provider calls.
                </p>
                <p className='arc-studio-config__cost-policy-summary' style={{ margin: '4px 0 0', fontSize: '11px', color: dryRun || !allowPaidCalls ? 'var(--theia-descriptionForeground)' : 'var(--theia-editorWarning-foreground)' }}>
                    Local cost preview: {costPolicySummary.label}. Dry-run blocks paid calls; current profile dryRun={String(Boolean(currentProfile?.dryRun))}, allowPaidCalls={String(Boolean(currentProfile?.allowPaidCalls))}; effective allowPaidCalls={String(costPolicySummary.paidCallsAllowed)}. Backend enforces opt-in gates; this UI does not enable provider execution.
                </p>
                {isolationStatus?.message && (
                    <p className='arc-studio-config__isolation-message' style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Isolation status: {isolationStatus.message}
                    </p>
                )}
            </div>

            <div className='arc-studio-config__section arc-studio-config__provider-cost' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                    <h4 style={{ margin: 0, fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Provider Diagnostics & Local Quota Preview</h4>
                    <button
                        className='arc-studio-config__provider-refresh'
                        onClick={loadConfig}
                        disabled={loading}
                    >
                        Refresh provider status
                    </button>
                </div>
                <p className='arc-studio-config__paid-call-warning' style={{ margin: '8px 0', fontSize: '11px', color: 'var(--theia-editorWarning-foreground)' }}>
                    Paid/live provider calls require explicit backend-enforced opt-in gates. Offline/local panel only; provider execution is not implemented here. dry-run/offline stays providerCall:false. Quota/cost display and reset use local counters only; display is event-backed/local-counter only.
                </p>
                <p className='arc-studio-config__provider-telemetry-state' style={{ margin: '0 0 8px', fontSize: '11px', color: providerTelemetryError ? 'var(--theia-editorWarning-foreground)' : 'var(--theia-descriptionForeground)' }}>
                    Provider telemetry state: {providerTelemetryUnavailable ? 'unavailable/degraded - backend method not wired; no provider call attempted' : providerTelemetryError ? 'error/degraded - local telemetry read failed; provider execution still disabled' : loading ? 'loading local telemetry...' : 'loaded from local ARC telemetry only'}.
                </p>
                <div className='arc-studio-config__live-provider-gate' style={{ margin: '8px 0', padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', fontSize: '11px', backgroundColor: 'var(--theia-editor-background)' }}>
                    <strong>Local provider backend-gated preview: {liveProviderGate.label || liveProviderGate.state || liveProviderGate.status || (dryRun || !allowPaidCalls ? 'blocked/gated' : 'preview-only')}</strong>
                    <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                        No network by default: providerCall:false. This panel never calls provider API, provider proxy, live API, or billing endpoints, and never enables real provider execution.
                    </p>
                    <p style={{ margin: '4px 0 0', color: 'var(--theia-descriptionForeground)' }}>
                        {liveProviderGate.message || 'State derives from dry-run, paid-call opt-in, diagnostics, and local cost policy only.'} Enforcement: {liveProviderGate.enforcement || 'backend-enforced opt-in; UI remains preview/offline and never enables provider execution.'}
                    </p>
                </div>
                <div className='arc-studio-config__provider-diagnostics' style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', fontSize: '12px' }}>
                    <span>Backend live-test flag (no calls here): <span style={{ fontFamily: 'monospace' }}>{diagnostics.liveTestsEnabled ? 'configured for gated backend use' : 'disabled/gated'}</span></span>
                    <span>Routing default: <span style={{ fontFamily: 'monospace' }}>{diagnostics.routingDefault || 'unset'}</span></span>
                    <span>Configured providers: <span style={{ fontFamily: 'monospace' }}>{diagnostics.configuredProvidersCount}</span></span>
                    <span>Configured accounts: <span style={{ fontFamily: 'monospace' }}>{diagnostics.configuredAccountsCount}</span></span>
                </div>
                <p className='arc-studio-config__provider-paths-note' style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Path legend: dry-run/offline = local preview only; local quota reset = ARC storage counters only; future live provider paths = separate backend-gated flow, not launched from this panel.
                </p>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px', fontSize: '12px', maxWidth: '260px' }}>
                    Quota provider filter
                    <select
                        className='arc-studio-config__quota-provider-filter'
                        value={quotaProviderFilter}
                        onChange={e => setQuotaProviderFilter(e.currentTarget.value)}
                    >
                        <option value='all'>All providers</option>
                        {providerQuotaOptions.map(p => (
                            <option key={p.id} value={p.id}>{p.displayName || p.display_name || p.id}</option>
                        ))}
                    </select>
                </label>
                <div className='arc-studio-config__provider-quota' style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '11px' }}>
                    {quotaCounters.length > 0 ? quotaCounters.map(row => (
                        <span key={row.key} className='arc-studio-config__quota-row' style={{ display: 'inline-flex', gap: '6px', padding: '2px 6px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '3px', fontFamily: 'monospace' }}>
                            <span className='arc-studio-config__quota-bucket'>{row.bucket}</span>
                            <span className='arc-studio-config__quota-scope'>{row.scope}</span>
                            <span>{row.id}</span>
                            <strong>{row.count}</strong>
                        </span>
                    )) : <span className='arc-studio-config__quota-empty' style={{ color: 'var(--theia-descriptionForeground)' }}>{providerTelemetryEmpty ? 'No local quota counters recorded yet. Run dry-run/offline flows to produce event-backed counters.' : 'Quota counters unavailable/degraded; no provider calls attempted.'}</span>}
                </div>
                {!quotaResetAvailable && (
                    <p className='arc-studio-config__quota-reset-disabled' style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Local quota reset disabled until local counters exist and the reset method is available.
                    </p>
                )}
                {quotaResetAvailable && (
                    <div className='arc-studio-config__quota-reset-confirm' style={{ marginTop: '8px', padding: '8px', border: '1px solid var(--theia-widgetBorder)', borderRadius: '4px', fontSize: '12px' }}>
                        <button
                            className='arc-studio-config__quota-reset-open'
                            onClick={() => setQuotaResetConfirmOpen(true)}
                            disabled={quotaResetting}
                        >
                            Local quota-counter reset
                        </button>
                        {quotaResetConfirmOpen && (
                            <div className='arc-studio-config__quota-reset-modal' role='dialog' aria-label='Confirm local quota-counter reset' style={{ marginTop: '8px' }}>
                                <p style={{ margin: '0 0 6px', color: 'var(--theia-editorWarning-foreground)' }}>
                                    Local quota-counter reset only. No provider network, no live API, no billing action.
                                </p>
                                <p style={{ margin: '0 0 6px', color: 'var(--theia-descriptionForeground)' }}>
                                    Type exact phrase <code>{quotaResetRequiredPhrase}</code> to enable reset. {quotaResetConfirmation.warning || quotaResetConfirmation.description || ''}
                                </p>
                                <input
                                    className='arc-studio-config__quota-reset-phrase'
                                    value={quotaResetPhrase}
                                    onChange={e => setQuotaResetPhrase(e.currentTarget.value)}
                                    placeholder={quotaResetRequiredPhrase}
                                    aria-label='Quota reset confirmation phrase'
                                />
                                <button
                                    className='arc-studio-config__quota-reset-local'
                                    onClick={handleResetQuota}
                                    disabled={quotaResetting || !quotaResetConfirmed}
                                    style={{ marginLeft: '8px', fontSize: '12px' }}
                                >
                                    {quotaResetting ? 'Resetting local quota counters...' : 'Confirm local reset'}
                                </button>
                                <button
                                    className='arc-studio-config__quota-reset-cancel'
                                    onClick={() => { setQuotaResetConfirmOpen(false); setQuotaResetPhrase(''); }}
                                    disabled={quotaResetting}
                                    style={{ marginLeft: '6px', fontSize: '12px' }}
                                >
                                    Cancel
                                </button>
                            </div>
                        )}
                    </div>
                )}
                <p className='arc-studio-config__quota-reset-note' style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Local quota-counter reset calls ARC CLI local storage only; no provider network calls, no live API calls, no billing action.
                </p>
            </div>

            {exportText && (
                <div className='arc-studio-config__section arc-studio-config__safe-export' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                    <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Safe Config Snapshot</h4>
                    <p style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Copy-safe JSON. Contains status/source metadata only; no raw credentials.
                    </p>
                    <pre className='arc-studio-config__safe-export-json' style={{ maxHeight: '220px', overflow: 'auto', fontSize: '11px' }}>{exportText}</pre>
                </div>
            )}

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Provider Key Reference</h4>
                <p style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Save an environment variable name only. ARC does not capture raw key material.
                </p>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', marginBottom: '8px' }}>
                    Provider
                    <select
                        className='arc-studio-config__provider-dropdown'
                        value={selectedProvider}
                        onChange={e => {
                            const next = e.currentTarget.value;
                            const entry = providerCatalog.find(p => p.id === next);
                            setSelectedProvider(next);
                            setProviderEnvVar(entry?.envKeyNames?.[0] || entry?.env_key_names?.[0] || '');
                        }}
                    >
                        {(providerCatalog.length ? providerCatalog : [{ id: 'openai', displayName: 'OpenAI', display_name: 'OpenAI' } as ProviderCatalogEntry]).map(p => (
                            <option key={p.id} value={p.id}>{p.displayName || p.display_name || p.id}</option>
                        ))}
                    </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', marginBottom: '8px' }}>
                    API key via env var
                    <input
                        className='arc-studio-config__provider-env-input'
                        value={providerEnvVar}
                        onChange={e => setProviderEnvVar(e.currentTarget.value)}
                        placeholder='OPENAI_API_KEY'
                    />
                </label>
                <button
                    className='arc-studio-config__save-key-ref'
                    onClick={handleSaveKeyRef}
                    disabled={saving || !providerEnvVar.trim()}
                >
                    Save key reference
                </button>
                <p className='arc-studio-config__web-auth-warning' style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--theia-editorWarning-foreground)' }}>
                    Web session auth is research-only. ARC does not capture browser cookies or passphrases. Use official API/OAuth where available.
                </p>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Providers</h4>
                <p style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Keys shown as source/status only — raw values are never displayed.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {config.providers.map(p => (
                        <div key={p.provider} className='arc-studio-config__provider' style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            backgroundColor: 'var(--theia-editor-background)',
                            fontSize: '12px',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontWeight: 500 }}>{PROVIDER_DISPLAY[p.provider] || p.displayName || p.provider}</span>
                                <span style={{
                                    display: 'inline-block',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    fontSize: '10px',
                                    fontFamily: 'monospace',
                                    color: providerSourceColor(p.source),
                                    border: `1px solid ${providerSourceColor(p.source)}40`,
                                }}>
                                    {p.configured ? '✓ ' : '✗ '}{providerSourceBadge(p.source)}
                                </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                                {p.defaultModel && <span>model: {p.defaultModel}</span>}
                                {p.envOverride && (
                                    <span className='arc-studio-config__env-override' style={{ fontFamily: 'monospace', opacity: 0.8 }}>
                                        env: {p.envOverride}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className='arc-studio-config__section' style={{ padding: '12px 16px' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Routing</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
                    <span>Mode: <span style={{ fontFamily: 'monospace' }}>{config.runtime.routingMode}</span></span>
                    <span>Dry run: <span style={{ fontFamily: 'monospace' }}>{config.runtime.dryRun ? 'yes' : 'no'}</span></span>
                    <span>Isolation: <span style={{ fontFamily: 'monospace' }}>{config.runtime.isolation}</span></span>
                    <span>Profile: <span style={{ fontFamily: 'monospace' }}>{selectedProfile}</span></span>
                    <span>Paid calls: <span style={{ fontFamily: 'monospace', color: config.runtime.allowPaidCalls ? 'var(--theia-terminal-ansiYellow)' : 'var(--theia-descriptionForeground)' }}>{config.runtime.allowPaidCalls ? 'allowed' : 'blocked'}</span></span>
                </div>
            </div>
        </div>
    );
};

@injectable()
export class ConfigTabWidget extends ReactWidget {
    static readonly ID = 'arc:config-tab';
    static readonly LABEL = 'ARC Config';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    @postConstruct()
    protected init(): void {
        this.id = ConfigTabWidget.ID;
        this.title.label = ConfigTabWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'ARC Studio Configuration';
        this.update();
    }

    protected render(): React.ReactNode {
        return <ConfigTab arcService={this.arcService} />;
    }
}
