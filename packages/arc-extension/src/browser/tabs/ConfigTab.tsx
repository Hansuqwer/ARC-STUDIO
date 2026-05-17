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
            setSelectedProfile('local-safe');
            setDryRun(Boolean(status.runtime.dryRun));
            setAllowPaidCalls(Boolean(status.runtime.allowPaidCalls));
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
                    const current = loadedProfiles.find(profile => profile.id === selectedProfile) || loadedProfiles[0];
                    setSelectedProfile(current.id);
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
    }, [arcService, selectedProfile]);

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
            description = meta.label.toLowerCase().includes('swarm') ? 'bundled, ready' : availability;
        }
        return { value, ...meta, canRun, reason, availability, paid, description };
    });

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
                        Allow paid provider calls
                    </label>
                </div>
                <p className='arc-studio-config__run-policy-note' style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                    Dry-run saves force paid calls off; profile selection follows backend profile inventory but is not persisted by this safe config update; provider auth remains env-var references only.
                </p>
                {isolationStatus?.message && (
                    <p className='arc-studio-config__isolation-message' style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
                        Isolation status: {isolationStatus.message}
                    </p>
                )}
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
