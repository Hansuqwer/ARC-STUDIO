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
import { ArcService, ConfigStatus, SafeConfigUpdate, SafeProviderKeyStatus } from '../../common/arc-protocol';

export interface ConfigTabProps {
    arcService?: ArcService;
    onSave?: (update: SafeConfigUpdate) => void;
}

const RUNTIME_OPTIONS = [
    { value: 'swarmgraph', label: 'SwarmGraph', badge: 'SG', description: 'bundled, ready' },
    { value: 'langgraph', label: 'LangGraph', badge: 'LG', description: 'requires export target' },
    { value: 'crewai', label: 'CrewAI', badge: 'CR', description: 'not installed' },
    { value: 'openai-agents', label: 'OpenAI Agents', badge: 'OA', description: 'partial SDK' },
    { value: 'ag2', label: 'AG2', badge: 'A2', description: 'detection/export only' },
];

const MODE_OPTIONS = [
    { value: 'plan' as const, label: 'Plan', description: 'read-only' },
    { value: 'build' as const, label: 'Build', description: 'edit' },
    { value: 'auto' as const, label: 'Auto', description: 'policy-driven' },
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
        } catch {
            setConfig(null);
        } finally {
            setLoading(false);
        }
    }, [arcService]);

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
            </div>

            {saveMessage && (
                <div className='arc-studio-config__message' style={{ padding: '6px 16px', fontSize: '12px', color: 'var(--theia-descriptionForeground)', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                    {saveMessage}
                </div>
            )}

            <div className='arc-studio-config__section' style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widgetBorder)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--theia-descriptionForeground)', textTransform: 'uppercase' }}>Runtime</h4>
                <div className='arc-studio-config__radio-group' style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {RUNTIME_OPTIONS.map(opt => (
                        <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                            <input
                                type='radio'
                                name='runtime'
                                value={opt.value}
                                checked={selectedRuntime === opt.value}
                                onChange={() => setSelectedRuntime(opt.value)}
                            />
                            <span style={{
                                display: 'inline-block',
                                padding: '1px 6px',
                                borderRadius: '3px',
                                fontSize: '10px',
                                fontFamily: 'monospace',
                                backgroundColor: 'var(--theia-badge-background)',
                                color: 'var(--theia-badge-foreground)',
                                minWidth: '20px',
                                textAlign: 'center',
                            }}>{opt.badge}</span>
                            <span>{opt.label}</span>
                            <span style={{ fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>{opt.description}</span>
                        </label>
                    ))}
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
