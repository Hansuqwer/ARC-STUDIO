/**
 * ARC Audit Widget — audit chain viewer
 *
 * MOCK_REASON: Audit chain not yet implemented in Python backend
 * REAL_IMPLEMENTATION_PATH: python/src/agent_runtime_cockpit/storage/jsonl.py (audit log)
 * LOCAL_FIX_STEPS: Implement audit JSONL persistence and /api/audit endpoint
 * OWNER: Audit Viewer Agent
 * REMOVE_BEFORE: Beta
 */
import * as React from 'react';
import { injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';

const MOCK_AUDIT_ENTRIES = [
  { id: 'audit-001', timestamp: new Date(Date.now() - 10000).toISOString(), action: 'RUN_STARTED', actor: 'user', details: { run_id: 'run-mock-001', workflow: 'ResearchSwarm' }, verified: true },
  { id: 'audit-002', timestamp: new Date(Date.now() - 9000).toISOString(), action: 'NODE_EXECUTED', actor: 'system', details: { node: 'researcher', duration_ms: 1200 }, verified: true },
  { id: 'audit-003', timestamp: new Date(Date.now() - 7000).toISOString(), action: 'NODE_EXECUTED', actor: 'system', details: { node: 'writer', duration_ms: 800 }, verified: true },
  { id: 'audit-004', timestamp: new Date(Date.now() - 5000).toISOString(), action: 'RUN_COMPLETED', actor: 'system', details: { status: 'success' }, verified: true },
];

@injectable()
export class ArcAuditWidget extends ReactWidget {
  static readonly ID = 'arc:audit-viewer';
  static readonly LABEL = 'ARC Audit Viewer';

  @postConstruct()
  protected override init(): void {
    super.init();
    this.id = ArcAuditWidget.ID;
    this.title.label = ArcAuditWidget.LABEL;
    this.title.closable = true;
  }

  protected render(): React.ReactNode {
    return (
      <div style={{ padding: '16px', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)', height: '100%', overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '15px' }}>🔐 Audit Chain</h2>
          <span style={{ fontSize: '11px', padding: '2px 8px', backgroundColor: '#3d2500', color: '#ffb74d', borderRadius: '10px', border: '1px solid #ffb74d' }}>
            MOCK — fixture data
          </span>
        </div>
        <div style={{ marginBottom: '16px', padding: '8px 12px', backgroundColor: '#3d2500', border: '1px solid #ffb74d', borderRadius: '4px', fontSize: '12px', color: '#ffb74d' }}>
          ⚠ Audit chain uses fixture data. Real audit persistence requires ARC daemon with JSONL storage.
        </div>
        {MOCK_AUDIT_ENTRIES.map(entry => (
          <div key={entry.id} style={{ marginBottom: '8px', padding: '10px 14px', backgroundColor: 'var(--theia-editor-background)', border: `1px solid ${entry.verified ? '#4caf50' : '#ef5350'}`, borderRadius: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, fontSize: '12px' }}>{entry.action}</span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--theia-descriptionForeground)' }}>
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span style={{ fontSize: '10px', color: entry.verified ? '#4caf50' : '#ef5350' }}>
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
