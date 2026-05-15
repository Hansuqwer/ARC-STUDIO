/**
 * ARC Adapters Widget — Runtime Readiness Cards + Doctor Actions
 *
 * Ported from theia-extensions/arc-adapters.
 * Displays runtime adapter capability reports and provider status.
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, RuntimeCapabilityReport, RuntimeCapabilitiesResponse, ProviderStatus, DoctorAction } from '../common/arc-protocol';

interface AdaptersWidgetState {
    loading: boolean;
    capabilities: RuntimeCapabilityReport[];
    providerStatus?: ProviderStatus;
    workspacePath: string;
    runtimeError?: string;
    confirmAction?: DoctorAction;
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
                        This runtime requires paid/provider calls.
                    </div>
                )}
            </div>
        );
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
