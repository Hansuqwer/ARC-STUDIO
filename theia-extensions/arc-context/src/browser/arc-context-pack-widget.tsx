/**
 * ARC Context Pack Viewer Widget
 * Shows retrieved context evidence from local repo, Context7, Vercel Grep, GitHub, web search.
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { MessageService } from '@theia/core/lib/common/message-service';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { ContextPackEntry } from 'arc-core/lib/common/arc-protocol';

const SOURCE_ICONS: Record<string, string> = {
  local_repo: '📁',
  context7: '📚',
  vercel_grep: '🔍',
  github_search: '🐙',
  web_search: '🌐',
};

@injectable()
export class ArcContextPackWidget extends ReactWidget {
  static readonly ID = 'arc:context-pack-viewer';
  static readonly LABEL = 'ARC Context Pack';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  @inject(MessageService)
  protected readonly messageService: MessageService;

  protected entries: ContextPackEntry[] = [];
  protected task = 'inspect agent runtime';
  protected loading = false;
  protected generated = false;

  @postConstruct()
  protected override init(): void {
    super.init();
    this.id = ArcContextPackWidget.ID;
    this.title.label = ArcContextPackWidget.LABEL;
    this.title.closable = true;
  }

  protected async generate(): Promise<void> {
    this.loading = true;
    this.update();
    try {
      const result = await this.arcService.generateContextPack(this.task);
      this.entries = result.data ?? [];
      this.generated = true;
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected render(): React.ReactNode {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)' }}>
        {/* Toolbar */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--theia-widget-border)', flexShrink: 0 }}>
          <div style={{ fontWeight: 600, marginBottom: '8px' }}>🔍 Context Pack Generator</div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              style={{ flex: 1, padding: '6px 8px', backgroundColor: 'var(--theia-input-background)', color: 'var(--theia-input-foreground)', border: '1px solid var(--theia-input-border)', borderRadius: '4px', fontSize: '12px' }}
              value={this.task}
              placeholder="Enter task description..."
              onInput={e => { this.task = (e.target as HTMLInputElement).value; this.update(); }}
            />
            <button
              style={{ padding: '6px 14px', backgroundColor: '#4fc3f7', color: '#000', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}
              onClick={() => this.generate()}
              disabled={this.loading}
            >
              {this.loading ? '…' : 'Generate'}
            </button>
          </div>
        </div>

        {/* Results */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {!this.generated && !this.loading && (
            <div style={{ textAlign: 'center', paddingTop: '48px', color: 'var(--theia-descriptionForeground)' }}>
              Enter a task and click Generate to retrieve context
            </div>
          )}

          {this.generated && this.entries.length > 0 && (
            <div style={{ marginBottom: '8px', fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
              {this.entries.length} entries · sorted by relevance
            </div>
          )}

          {this.entries.map(entry => (
            <div key={entry.id} style={{ marginBottom: '8px', padding: '10px 14px', backgroundColor: 'var(--theia-editor-background)', border: '1px solid var(--theia-widget-border)', borderRadius: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontWeight: 600, fontSize: '12px' }}>
                  {SOURCE_ICONS[entry.source_type]} {entry.source}
                </span>
                <span style={{ fontSize: '10px', color: '#4fc3f7' }}>
                  {(entry.relevance_score * 100).toFixed(0)}% relevance
                </span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--theia-descriptionForeground)', marginBottom: '4px' }}>
                Source: <code>{entry.source_type}</code>
                {entry.url && <> · <a href={entry.url} style={{ color: 'var(--theia-textLink-foreground)' }}>{entry.url}</a></>}
              </div>
              <p style={{ fontSize: '12px', margin: 0, lineHeight: 1.5 }}>{entry.content}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }
}
