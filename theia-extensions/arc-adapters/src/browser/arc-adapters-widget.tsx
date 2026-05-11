/** ARC Adapters Status Widget */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { RuntimeInfo } from 'arc-core/lib/common/arc-protocol';

@injectable()
export class ArcAdaptersWidget extends ReactWidget {
  static readonly ID = 'arc:adapters-status';
  static readonly LABEL = 'ARC Adapters';

  @inject(ArcFrontendService) protected readonly arcService: ArcFrontendService;
  protected runtimes: RuntimeInfo[] = [];
  protected loading = false;

  @postConstruct()
  protected override init(): void {
    super.init();
    this.id = ArcAdaptersWidget.ID;
    this.title.label = ArcAdaptersWidget.LABEL;
    this.title.closable = true;
    this.load();
  }

  protected async load(): Promise<void> {
    this.loading = true; this.update();
    try { this.runtimes = (await this.arcService.listRuntimes()).data ?? []; }
    finally { this.loading = false; this.update(); }
  }

  protected render(): React.ReactNode {
    if (this.loading) return <div style={{ padding: 24 }}>Loading adapters…</div>;
    return (
      <div style={{ padding: 16, fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)', height: '100%', overflow: 'auto' }}>
        <h2 style={{ margin: '0 0 16px 0', fontSize: 15 }}>🔌 Registered Adapters</h2>
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
}
