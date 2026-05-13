/** ARC Audit Widget — audit chain viewer. */
import * as React from 'react';
import { injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';

const AUDIT_ENTRIES: Array<{ id: string; timestamp: string; action: string; actor: string; details: Record<string, unknown>; verified: boolean }> = [];

@injectable()
export class ArcAuditWidget extends ReactWidget {
  static readonly ID = 'arc:audit-viewer';
  static readonly LABEL = 'ARC Audit Viewer';

  @postConstruct()
  protected init(): void {
    this.id = ArcAuditWidget.ID;
    this.title.label = ArcAuditWidget.LABEL;
    this.title.closable = true;
  }

  protected render(): React.ReactNode {
    return (
      <div style={{ padding: '16px', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)', height: '100%', overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '15px' }}>🔐 Audit Chain</h2>
          <span style={{ fontSize: '11px', padding: '2px 8px', backgroundColor: 'var(--theia-editorWarning-background)', color: 'var(--theia-editorWarning-foreground)', borderRadius: '10px', border: '1px solid var(--theia-editorWarning-foreground)' }}>
            Not implemented
          </span>
        </div>
        <div style={{ marginBottom: '16px', padding: '8px 12px', backgroundColor: 'var(--theia-editorWarning-background)', border: '1px solid var(--theia-editorWarning-foreground)', borderRadius: '4px', fontSize: '12px', color: 'var(--theia-editorWarning-foreground)' }}>
          Audit chain persistence is not implemented yet. No audit entries are shown until the ARC daemon exposes an audit endpoint.
        </div>
        {AUDIT_ENTRIES.length === 0 && (
          <div style={{ padding: '12px', color: 'var(--theia-descriptionForeground)', fontSize: '12px' }}>
            No audit entries available.
          </div>
        )}
        {AUDIT_ENTRIES.map(entry => (
          <div key={entry.id} style={{ marginBottom: '8px', padding: '10px 14px', backgroundColor: 'var(--theia-editor-background)', border: `1px solid ${entry.verified ? 'var(--theia-charts-green)' : 'var(--theia-errorForeground)'}`, borderRadius: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, fontSize: '12px' }}>{entry.action}</span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--theia-descriptionForeground)' }}>
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span style={{ fontSize: '10px', color: entry.verified ? 'var(--theia-charts-green)' : 'var(--theia-errorForeground)' }}>
                  {entry.verified ? '✓ verified' : '⚠ unverified'}
                </span>
              </div>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>Actor: {entry.actor}</div>
            <pre style={{ fontSize: '10px', margin: '4px 0 0 0', color: 'var(--theia-descriptionForeground)', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(entry.details, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    );
  }
}
