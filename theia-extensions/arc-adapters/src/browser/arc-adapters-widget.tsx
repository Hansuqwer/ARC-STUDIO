/** ARC Adapters Status Widget — Runtime Readiness Cards + Doctor Actions */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { PreferenceService } from '@theia/core/lib/common/preferences';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { ProviderStatus, RuntimeCapabilityReport, DoctorAction } from 'arc-core/lib/common/arc-protocol';

@injectable()
export class ArcAdaptersWidget extends ReactWidget {
  static readonly ID = 'arc:adapters-status';
  static readonly LABEL = 'ARC Adapters';

  @inject(ArcFrontendService) protected readonly arcService: ArcFrontendService;
  @inject(PreferenceService) protected readonly preferences: PreferenceService;
  protected capabilities: RuntimeCapabilityReport[] = [];
  protected providerStatus?: ProviderStatus;
  protected workspaceStatus?: { frontendPath: string; backendPath: string; source: string };
  protected runtimeError?: string;
  protected confirmAction?: DoctorAction;
  protected loading = false;

  @postConstruct()
  protected init(): void {
    this.id = ArcAdaptersWidget.ID;
    this.title.label = ArcAdaptersWidget.LABEL;
    this.title.closable = true;
    this.load();
  }

  protected async load(): Promise<void> {
    this.loading = true; this.update();
    try {
      const provider = this.preferences.get<string>('arc.swarmgraph.provider', 'openai');
      const baseUrl = this.preferences.get<string>('arc.swarmgraph.baseUrl', '');
      const [capsResult, providerStatus] = await Promise.all([
        this.arcService.listRuntimeCapabilities().catch(error => {
          this.runtimeError = String(error);
          return undefined;
        }),
        this.arcService.getProviderStatus(provider, baseUrl).catch(() => undefined),
      ]);
      this.capabilities = capsResult?.data?.runtimes ?? [];
      this.runtimeError = capsResult?.error?.message ?? this.runtimeError;
      this.providerStatus = providerStatus?.data ?? undefined;
      this.workspaceStatus = (await this.arcService.getWorkspaceStatus().catch(() => undefined))?.data ?? undefined;
    }
    finally { this.loading = false; this.update(); }
  }

  protected render(): React.ReactNode {
    if (this.loading) return <div style={{ padding: 24 }}>Loading adapters…</div>;
    return (
      <div style={{ padding: 16, fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)', height: '100%', overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 15 }}>Runtime Readiness</h2>
          <button style={refreshBtnStyle} onClick={() => this.load()}>Refresh</button>
        </div>
        {this.renderWorkspaceDiagnostics()}
        {this.renderProviderSettings()}
        {this.capabilities.map(cap => this.renderCard(cap))}
        {this.capabilities.length === 0 && !this.runtimeError && (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--theia-descriptionForeground)' }}>
            No runtimes detected in workspace.
          </div>
        )}
        {this.renderConformanceTip()}
      </div>
    );
  }

  protected renderCard(cap: RuntimeCapabilityReport): React.ReactNode {
    const isReady = cap.can_run;
    const color = isReady ? '#4caf50' : '#ffb74d';
    const icon = isReady ? '✓' : '⚠';
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
            fontSize: 11,
            color,
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
            Evidence: {cap.detected_artifacts.join(' · ')}
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
          <div style={{ marginTop: 4, fontSize: 10, color: '#ffb74d' }}>
            This runtime requires paid/provider calls.
          </div>
        )}
      </div>
    );
  }

  protected runDoctorAction(action: DoctorAction): void {
    if (!action.safe_to_auto_run && action.command) {
      this.confirmAction = action;
      this.update();
      return;
    }
    if (action.command) {
      console.log(`ARC doctor: copying command: ${action.command}`);
      navigator.clipboard.writeText(action.command).catch(() => {});
    }
  }

  protected renderConfirmDialog(): React.ReactNode {
    if (!this.confirmAction) return null;
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
          <p style={{ margin: 0, fontSize: 13 }}>{this.confirmAction.description}</p>
          <pre style={{
            margin: '12px 0', padding: 10, backgroundColor: '#1e1e1e',
            borderRadius: 4, fontSize: 12, whiteSpace: 'pre-wrap',
          }}>{this.confirmAction.command}</pre>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button style={{ ...doctorBtnStyle, backgroundColor: '#c62828' }} onClick={() => {
              navigator.clipboard.writeText(this.confirmAction!.command).catch(() => {});
              this.confirmAction = undefined;
              this.update();
            }}>Copy & Close</button>
            <button style={doctorBtnStyle} onClick={() => {
              this.confirmAction = undefined;
              this.update();
            }}>Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  protected renderProviderSettings(): React.ReactNode {
    const status = this.providerStatus;
    const provider = status?.provider ?? this.preferences.get<string>('arc.swarmgraph.provider', 'openai');
    const apiKeyOk = Boolean(status?.apiKeyConfigured);
    return (
      <div style={{ marginBottom: 16, padding: 12, backgroundColor: 'var(--theia-editor-background)', border: '1px solid var(--theia-widget-border)', borderRadius: 6 }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: 13 }}>Provider Settings</h3>
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          <div>Provider: <strong>{provider}</strong></div>
          <div>Base URL override: <strong>{status?.baseUrlConfigured ? 'configured' : 'default'}</strong></div>
          <div>API key: <strong style={{ color: apiKeyOk ? '#4caf50' : '#ffb74d' }}>{apiKeyOk ? `configured via ${status?.apiKeySource}` : 'missing'}</strong></div>
          <p style={{ margin: '8px 0 0 0', color: 'var(--theia-descriptionForeground)' }}>{status?.message ?? 'Provider status unavailable.'}</p>
        </div>
      </div>
    );
  }

  protected renderWorkspaceDiagnostics(): React.ReactNode {
    return (
      <div style={{ marginBottom: 12, padding: 10, backgroundColor: 'var(--theia-editor-background)', border: '1px solid var(--theia-widget-border)', borderRadius: 6, fontSize: 11, lineHeight: 1.5 }}>
        <div>Workspace: <strong>{this.workspaceStatus?.backendPath || 'unresolved'}</strong></div>
        <div style={{ color: 'var(--theia-descriptionForeground)' }}>Source: {this.workspaceStatus?.source ?? 'unknown'}</div>
        {this.runtimeError && <div style={{ color: '#ffb74d' }}>Runtime API: {this.runtimeError}</div>}
      </div>
    );
  }

  protected renderConformanceTip(): React.ReactNode {
    return (
      <div style={{ marginTop: 16, padding: 10, backgroundColor: '#1a2d47', border: '1px solid #4fc3f7', borderRadius: 6, fontSize: 11, color: '#4fc3f7' }}>
        Run conformance tests: <code>uv run arc adapter test swarmgraph</code>
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
