/** ARC Adapters Status Widget */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { PreferenceService } from '@theia/core/lib/common/preferences';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { ProviderStatus, RuntimeInfo } from 'arc-core/lib/common/arc-protocol';

@injectable()
export class ArcAdaptersWidget extends ReactWidget {
  static readonly ID = 'arc:adapters-status';
  static readonly LABEL = 'ARC Adapters';

  @inject(ArcFrontendService) protected readonly arcService: ArcFrontendService;
  @inject(PreferenceService) protected readonly preferences: PreferenceService;
  protected runtimes: RuntimeInfo[] = [];
  protected providerStatus?: ProviderStatus;
  protected workspaceStatus?: { frontendPath: string; backendPath: string; source: string };
  protected runtimeError?: string;
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
      const provider = this.preferences.get<string>('arc.swarmgraph.provider', '9router');
      const baseUrl = this.preferences.get<string>('arc.swarmgraph.baseUrl', '');
      const [runtimes, providerStatus] = await Promise.all([
        this.arcService.listRuntimes().catch(error => {
          this.runtimeError = String(error);
          return undefined;
        }),
        this.arcService.getProviderStatus(provider, baseUrl).catch(() => undefined),
      ]);
      this.runtimes = runtimes?.data ?? [];
      this.runtimeError = runtimes?.error?.message ?? this.runtimeError;
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
          <h2 style={{ margin: 0, fontSize: 15 }}>🔌 Registered Adapters</h2>
          <button style={refreshBtnStyle} onClick={() => this.load()}>Refresh</button>
        </div>
        {this.renderWorkspaceDiagnostics()}
        {this.renderProviderSettings()}
        {['swarmgraph', 'langgraph', 'crewai', 'openai-agents', 'ag2'].map(adapter => {
          const rt = this.runtimes.find(r => r.adapter === adapter);
          return (
            <div key={adapter} style={{ marginBottom: 8, padding: '10px 14px', backgroundColor: 'var(--theia-editor-background)', border: `1px solid ${rt ? '#4caf50' : 'var(--theia-widget-border)'}`, borderRadius: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{adapter}</span>
                <span style={{ fontSize: 11, color: rt ? '#4caf50' : 'var(--theia-descriptionForeground)', padding: '2px 8px', border: `1px solid ${rt ? '#4caf50' : 'var(--theia-widget-border)'}`, borderRadius: 10 }}>
                  {rt ? `detected (${rt.confidence})` : 'not detected'}
                </span>
              </div>
              {rt && (
                <div style={{ marginTop: 6, fontSize: 11, color: 'var(--theia-descriptionForeground)' }}>
                  {rt.evidence.join(' · ')}
                </div>
              )}
            </div>
          );
        })}
        <div style={{ marginTop: 16, padding: 10, backgroundColor: '#1a2d47', border: '1px solid #4fc3f7', borderRadius: 6, fontSize: 11, color: '#4fc3f7' }}>
          ℹ Run <code>uv run arc adapter test swarmgraph</code> to run conformance tests
        </div>
      </div>
    );
  }

  protected renderProviderSettings(): React.ReactNode {
    const status = this.providerStatus;
    const provider = status?.provider ?? this.preferences.get<string>('arc.swarmgraph.provider', '9router');
    const apiKeyOk = Boolean(status?.apiKeyConfigured);
    return (
      <div style={{ marginBottom: 16, padding: 12, backgroundColor: 'var(--theia-editor-background)', border: '1px solid var(--theia-widget-border)', borderRadius: 6 }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: 13 }}>SwarmGraph Provider Settings</h3>
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          <div>Provider: <strong>{provider}</strong> <span style={{ color: 'var(--theia-descriptionForeground)' }}>(preference: <code>arc.swarmgraph.provider</code>)</span></div>
          <div>Base URL override: <strong>{status?.baseUrlConfigured ? 'configured' : 'default'}</strong> <span style={{ color: 'var(--theia-descriptionForeground)' }}>(preference: <code>arc.swarmgraph.baseUrl</code>)</span></div>
          <div>API key: <strong style={{ color: apiKeyOk ? '#4caf50' : '#ffb74d' }}>{apiKeyOk ? `configured via ${status?.apiKeySource}` : 'missing'}</strong></div>
          <div>Runtime execution: <strong style={{ color: status?.runtimeAvailable ? '#4caf50' : '#ffb74d' }}>{status?.runtimeAvailable ? 'available' : 'not implemented'}</strong></div>
          <p style={{ margin: '8px 0 0 0', color: 'var(--theia-descriptionForeground)' }}>{status?.message ?? 'Provider status unavailable.'}</p>
          <div style={{ marginTop: 8, padding: 8, backgroundColor: '#2b1f00', border: '1px solid #ffb74d', borderRadius: 4, color: '#ffcc80' }}>
            API keys are not stored in the IDE yet. Set <code>AI_PROVIDER_GATEWAY_9ROUTER_API_KEY</code> in the backend environment. Optional: <code>AI_PROVIDER_GATEWAY_9ROUTER_BASE_URL</code>.
          </div>
        </div>
      </div>
    );
  }

  protected renderWorkspaceDiagnostics(): React.ReactNode {
    return (
      <div style={{ marginBottom: 12, padding: 10, backgroundColor: 'var(--theia-editor-background)', border: '1px solid var(--theia-widget-border)', borderRadius: 6, fontSize: 11, lineHeight: 1.5 }}>
        <div>Workspace: <strong>{this.workspaceStatus?.backendPath || 'unresolved'}</strong></div>
        <div style={{ color: 'var(--theia-descriptionForeground)' }}>Source: {this.workspaceStatus?.source ?? 'unknown'} · Frontend path: {this.workspaceStatus?.frontendPath || '(empty)'}</div>
        {this.runtimeError && <div style={{ color: '#ffb74d' }}>Runtime API: {this.runtimeError}</div>}
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
