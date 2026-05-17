/**
 * ARC Adapters Widget — Runtime Readiness Cards + Doctor Actions
 *
 * Ported from theia-extensions/arc-adapters.
 * Displays runtime adapter capability reports and provider status.
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, RuntimeCapabilityReport, RuntimeCapabilitiesResponse, ProviderStatus, DoctorAction, CapabilityDiffResponse } from '../common/arc-protocol';
import { CapabilityDiffViewer } from './components/CapabilityDiffViewer';

interface AdaptersWidgetState {
    loading: boolean;
    capabilities: RuntimeCapabilityReport[];
    providerStatus?: ProviderStatus;
    workspacePath: string;
    runtimeError?: string;
    confirmAction?: DoctorAction;
    diffLoading: boolean;
    diffResponse: CapabilityDiffResponse | null;
    diffError?: string;
}

interface ReadinessAction {
    id: string;
    title: string;
    help: string;
    copyLabel: string;
    copyText?: string;
    confirmText?: string;
}

@injectable()
export class ArcAdaptersWidget extends ReactWidget {
    static readonly ID = 'arc:adapters-status';
    static readonly LABEL = 'ARC Adapters';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected state: AdaptersWidgetState = {
        loading: false,
        capabilities: [],
        workspacePath: '',
        runtimeError: undefined,
        confirmAction: undefined,
        diffLoading: false,
        diffResponse: null,
        diffError: undefined,
    };

    @postConstruct()
    protected init(): void {
        this.id = ArcAdaptersWidget.ID;
        this.title.label = ArcAdaptersWidget.LABEL;
        this.title.closable = true;
        this.load();
    }

    protected async load(): Promise<void> {
        this.updateState({ loading: true });
        try {
            const [capsResult, wsStatus] = await Promise.all([
                this.arcService.listRuntimeCapabilities().catch(error => {
                    this.updateState({ runtimeError: String(error) });
                    return undefined;
                }),
                this.arcService.getWorkspaceStatus().catch(() => undefined),
            ]);
            this.updateState({
                capabilities: capsResult?.runtimes ?? [],
                workspacePath: wsStatus?.frontendPath || '',
                loading: false,
            });
        } catch {
            this.updateState({ loading: false });
        }
    }

    protected updateState(updates: Partial<AdaptersWidgetState>): void {
        this.state = { ...this.state, ...updates };
        this.update();
    }

    protected render(): React.ReactNode {
        if (this.state.loading) return <div style={{ padding: 24 }}>Loading adapters...</div>;
        const runtimeIds = this.state.capabilities.map(c => c.runtime_id);
        return (
            <div style={{
                padding: 16, fontFamily: 'var(--theia-ui-font-family)',
                color: 'var(--theia-foreground)', height: '100%', overflow: 'auto',
            }}>
                <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 16,
                }}>
                    <h2 style={{ margin: 0, fontSize: 15 }}>Runtime Readiness</h2>
                    <button style={refreshBtnStyle} onClick={() => this.load()}>Refresh</button>
                </div>
                {this.renderWorkspaceInfo()}
                <CapabilityDiffViewer
                    diffResponse={this.state.diffResponse}
                    loading={this.state.diffLoading}
                    error={this.state.diffError}
                    onConfirm={() => this.handleDiffConfirm()}
                    onCancel={() => this.handleDiffCancel()}
                    onCompare={(from, to) => this.handleCompare(from, to)}
                    availableRuntimes={runtimeIds}
                />
                {this.state.capabilities.map(cap => this.renderCard(cap))}
                {this.state.capabilities.length === 0 && !this.state.runtimeError && (
                    <div style={{
                        padding: 20, textAlign: 'center',
                        color: 'var(--theia-descriptionForeground)',
                    }}>
                        No runtimes detected in workspace.
                    </div>
                )}
                {this.renderConfirmDialog()}
            </div>
        );
    }

    protected renderWorkspaceInfo(): React.ReactNode {
        return (
            <div style={{
                marginBottom: 12, padding: 10,
                backgroundColor: 'var(--theia-editor-background)',
                border: '1px solid var(--theia-widget-border)',
                borderRadius: 6, fontSize: 11, lineHeight: 1.5,
            }}>
                <div>Workspace: <strong>{this.state.workspacePath || 'unresolved'}</strong></div>
                {this.state.runtimeError && (
                    <div style={{ color: 'var(--theia-editorWarning-foreground)' }}>
                        Runtime API: {this.state.runtimeError}
                    </div>
                )}
            </div>
        );
    }

    protected renderCard(cap: RuntimeCapabilityReport): React.ReactNode {
        const isReady = cap.can_run;
        const color = isReady ? 'var(--theia-charts-green)' : 'var(--theia-editorWarning-foreground)';
        const icon = isReady ? '\u2713' : '\u26A0';
        return (
            <div key={cap.runtime_id} style={{
                marginBottom: 10, padding: '10px 14px',
                backgroundColor: 'var(--theia-editor-background)',
                border: `1px solid ${color}`,
                borderRadius: 6,
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>
                        {icon} {cap.runtime_id}
                    </span>
                    <span style={{
                        fontSize: 11, color,
                        padding: '2px 8px',
                        border: `1px solid ${color}`,
                        borderRadius: 10,
                    }}>
                        {cap.can_run ? 'ready' : cap.availability.replace(/_/g, ' ')}
                    </span>
                </div>
                {cap.reason && (
                    <div style={{ marginTop: 6, fontSize: 11, color: 'var(--theia-descriptionForeground)' }}>
                        {cap.reason}
                    </div>
                )}
                {cap.required_env.length > 0 && (
                    <div style={{ marginTop: 4, fontSize: 11, color: 'var(--theia-descriptionForeground)' }}>
                        Required env: <code>{cap.required_env.join(', ')}</code>
                    </div>
                )}
                {cap.detected_artifacts.length > 0 && (
                    <div style={{ marginTop: 4, fontSize: 11, color: 'var(--theia-descriptionForeground)' }}>
                        Evidence: {cap.detected_artifacts.join(' \u00B7 ')}
                    </div>
                )}
                {this.renderReadinessActions(cap)}
                {cap.doctor_actions.length > 0 && (
                    <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {cap.doctor_actions.map(action => (
                            <button
                                key={action.id}
                                style={doctorBtnStyle}
                                title={action.description}
                                onClick={() => this.runDoctorAction(action)}
                            >
                                {action.label}
                            </button>
                        ))}
                    </div>
                )}
                {cap.requires_paid_calls && (
                    <div style={{ marginTop: 4, fontSize: 10, color: 'var(--theia-editorWarning-foreground)' }}>
                        Provider gate: this runtime requires explicit paid/provider opt-in. Use env-var refs only; raw secret values are never shown.
                    </div>
                )}
            </div>
        );
    }

    protected renderReadinessActions(cap: RuntimeCapabilityReport): React.ReactNode {
        const actions = this.getReadinessActions(cap);
        if (actions.length === 0) return null;
        return (
            <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                {actions.map(action => (
                    <div key={action.id} style={readinessCardStyle}>
                        <div style={{ fontWeight: 600 }}>{action.title}</div>
                        <div style={{ marginTop: 2, color: 'var(--theia-descriptionForeground)' }}>
                            {action.help}
                        </div>
                        <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {action.copyText && (
                                <button
                                    style={doctorBtnStyle}
                                    title="Copy only; ARC never executes setup commands from this card."
                                    onClick={() => navigator.clipboard.writeText(action.copyText!).catch(() => {})}
                                >
                                    {action.copyLabel}
                                </button>
                            )}
                            {action.confirmText && (
                                <button
                                    style={doctorBtnStyle}
                                    title="Requires explicit confirmation before using provider-backed runtime."
                                    onClick={() => navigator.clipboard.writeText(action.confirmText!).catch(() => {})}
                                >
                                    Copy confirm flag
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    protected getReadinessActions(cap: RuntimeCapabilityReport): ReadinessAction[] {
        const actions: ReadinessAction[] = [];
        const runtimeId = cap.runtime_id.toLowerCase();
        if (!cap.can_run && cap.doctor_actions.length === 0) {
            actions.push({
                id: 'missing-dependencies',
                title: 'Missing dependencies',
                help: 'Install the adapter package/CLI, then refresh readiness. This card is copy-only and never runs commands.',
                copyLabel: 'Copy doctor command',
                copyText: `arc doctor runtime ${cap.runtime_id}`,
            });
        }
        if (runtimeId.includes('crewai')) {
            actions.push(this.exportTargetAction('crewai', 'CrewAI export target', 'CREWAI_EXPORT_PATH'));
        }
        if (runtimeId.includes('openai')) {
            actions.push(this.exportTargetAction('openai', 'OpenAI Agents export target', 'OPENAI_AGENTS_EXPORT_PATH'));
        }
        if (runtimeId.includes('llama')) {
            actions.push(this.exportTargetAction('llamaindex', 'LlamaIndex export target', 'LLAMAINDEX_EXPORT_PATH'));
        }
        if (cap.required_env.length > 0 || cap.requires_paid_calls) {
            actions.push({
                id: 'provider-gate-env-refs',
                title: 'Provider gate / env refs',
                help: `Set env-var references only: ${cap.required_env.join(', ') || 'provider-specific env refs'}. Do not paste secret values into ARC config.`,
                copyLabel: 'Copy env var names',
                copyText: cap.required_env.join('\n'),
                confirmText: 'ARC_CONFIRM_PROVIDER_CALLS=1',
            });
        }
        return actions;
    }

    protected exportTargetAction(id: string, title: string, envName: string): ReadinessAction {
        return {
            id: `${id}-export-target`,
            title,
            help: `Configure ${envName} as an env-var reference for generated export output. Raw values are not displayed.`,
            copyLabel: 'Copy export env name',
            copyText: envName,
        };
    }

    protected runDoctorAction(action: DoctorAction): void {
        if (!action.safe_to_auto_run && action.command) {
            this.updateState({ confirmAction: action });
            return;
        }
        if (action.command) {
            console.log(`ARC doctor: copying command: ${action.command}`);
            navigator.clipboard.writeText(action.command).catch(() => {});
        }
    }

    protected async handleCompare(from: string, to: string): Promise<void> {
        this.updateState({ diffLoading: true, diffError: undefined, diffResponse: null });
        try {
            const result = await this.arcService.getCapabilityDiff(from, to);
            this.updateState({ diffLoading: false, diffResponse: result });
        } catch (error) {
            this.updateState({
                diffLoading: false,
                diffError: error instanceof Error ? error.message : String(error),
            });
        }
    }

    protected handleDiffConfirm(): void {
        console.log('ARC adapters: runtime switch confirmed');
    }

    protected handleDiffCancel(): void {
        this.updateState({ diffResponse: null });
    }

    protected renderConfirmDialog(): React.ReactNode {
        if (!this.state.confirmAction) return null;
        return (
            <div style={{
                position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
            }}>
                <div style={{
                    backgroundColor: 'var(--theia-editor-background)',
                    border: '1px solid var(--theia-widget-border)',
                    borderRadius: 8, padding: 20, maxWidth: 480,
                }}>
                    <h3 style={{ margin: '0 0 8px 0' }}>Run Doctor Action?</h3>
                    <p style={{ margin: 0, fontSize: 13 }}>{this.state.confirmAction.description}</p>
                    <pre style={{
                        margin: '12px 0', padding: 10,
                        backgroundColor: 'var(--theia-textCodeBlock-background)',
                        borderRadius: 4, fontSize: 12, whiteSpace: 'pre-wrap',
                    }}>{this.state.confirmAction.command}</pre>
                    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                        <button style={{
                            ...doctorBtnStyle,
                            backgroundColor: 'var(--theia-errorForeground)',
                        }} onClick={() => {
                            navigator.clipboard.writeText(this.state.confirmAction!.command).catch(() => {});
                            this.updateState({ confirmAction: undefined });
                        }}>Copy & Close</button>
                        <button style={doctorBtnStyle} onClick={() => {
                            this.updateState({ confirmAction: undefined });
                        }}>Cancel</button>
                    </div>
                </div>
            </div>
        );
    }
}

const refreshBtnStyle: React.CSSProperties = {
    backgroundColor: 'var(--theia-secondaryButton-background)',
    color: 'var(--theia-secondaryButton-foreground)',
    border: 'none',
    borderRadius: 4,
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: 11,
};

const doctorBtnStyle: React.CSSProperties = {
    backgroundColor: 'var(--theia-button-background)',
    color: 'var(--theia-button-foreground)',
    border: 'none',
    borderRadius: 4,
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: 11,
};

const readinessCardStyle: React.CSSProperties = {
    padding: 8,
    border: '1px solid var(--theia-widget-border)',
    borderRadius: 4,
    fontSize: 11,
};
