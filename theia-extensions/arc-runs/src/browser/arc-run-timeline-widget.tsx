/**
 * ARC Run Timeline Widget
 *
 * Displays a chronological timeline of run events (AG-UI compatible).
 * Source: https://docs.ag-ui.com/concepts/events
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { RunRecord, RunEvent } from 'arc-core/lib/common/arc-protocol';

const EVENT_ICONS: Record<string, string> = {
  RUN_STARTED: '▶',
  RUN_COMPLETED: '✓',
  RUN_FAILED: '✗',
  NODE_STARTED: '◉',
  NODE_COMPLETED: '●',
  NODE_FAILED: '⚠',
  MESSAGE: '💬',
  TOOL_CALL: '🔧',
  STATE_SNAPSHOT: '📸',
};

@injectable()
export class ArcRunTimelineWidget extends ReactWidget {
  static readonly ID = 'arc:run-timeline';
  static readonly LABEL = 'ARC Run Timeline';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  protected runs: RunRecord[] = [];
  protected selectedRun: RunRecord | null = null;
  protected loading = false;
  protected streaming = false;
  protected liveEvents: RunEvent[] = [];

  @postConstruct()
  protected init(): void {
    this.id = ArcRunTimelineWidget.ID;
    this.title.label = ArcRunTimelineWidget.LABEL;
    this.title.closable = true;
    this.title.caption = 'ARC Run Timeline';
    this.loadRuns();
  }

  protected async loadRuns(): Promise<void> {
    this.loading = true;
    this.update();
    try {
      const result = await this.arcService.listRuns();
      this.runs = result.data ?? [];
      this.selectedRun = this.runs[0] ?? null;
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected render(): React.ReactNode {
    if (this.loading) {
      return <div style={{ padding: 24, textAlign: 'center' }}>Loading runs…</div>;
    }

    return (
      <div style={{ display: 'flex', height: '100%', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)' }}>
        {/* Run List */}
        <div style={{ width: '200px', borderRight: '1px solid var(--theia-widget-border)', overflow: 'auto', flexShrink: 0 }}>
          <div style={{ padding: '8px 12px', fontWeight: 600, borderBottom: '1px solid var(--theia-widget-border)', fontSize: '12px', display: 'flex', justifyContent: 'space-between' }}>
            <span>Runs ({this.runs.length})</span>
            <button style={iconBtnStyle} onClick={() => this.loadRuns()} title="Refresh">↻</button>
          </div>
          {this.runs.map(run => (
            <div
              key={run.id}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                borderBottom: '1px solid var(--theia-widget-border)',
                backgroundColor: this.selectedRun?.id === run.id ? 'var(--theia-list-activeSelectionBackground)' : 'transparent',
              }}
              onClick={() => { this.selectedRun = run; this.update(); }}
            >
              <div style={{ fontSize: '11px', fontWeight: 500 }}>
                {this.statusIcon(run.status)} {run.id.substring(0, 12)}
              </div>
              <div style={{ fontSize: '10px', opacity: 0.7 }}>{run.workflow_id}</div>
              <div style={{ fontSize: '10px', opacity: 0.6 }}>
                {new Date(run.started_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>

        {/* Timeline */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
          {this.selectedRun ? this.renderTimeline(this.selectedRun) : (
            <div style={{ textAlign: 'center', paddingTop: '48px', color: 'var(--theia-descriptionForeground)' }}>
              <p>Select a run to view timeline</p>
              <button style={primaryBtnStyle} onClick={() => this.startSwarmGraphRun()}>Start SwarmGraph Run</button>
            </div>
          )}
        </div>
      </div>
    );
  }

  protected renderTimeline(run: RunRecord): React.ReactNode {
    const events = run.events;
    const duration = run.ended_at
      ? new Date(run.ended_at).getTime() - new Date(run.started_at).getTime()
      : null;

    return (
      <div>
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ margin: '0 0 4px 0', fontSize: '15px' }}>
            {this.statusIcon(run.status)} Run: {run.id}
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
            Workflow: <strong>{run.workflow_id}</strong> ·
            Runtime: <strong>{run.runtime}</strong> ·
            Status: <strong style={{ color: this.statusColor(run.status) }}>{run.status}</strong>
            {duration !== null && ` · Duration: ${duration}ms`}
          </div>
          {run.metadata?.['_mock'] && (
            <div style={{ marginTop: '8px', padding: '6px 10px', backgroundColor: '#3d2500', border: '1px solid #ffb74d', borderRadius: '4px', fontSize: '11px', color: '#ffb74d' }}>
              ⚠ [MOCK] Fixture run — connect ARC daemon for live runs
            </div>
          )}
        </div>

        {/* Timeline track */}
        <div style={{ position: 'relative', paddingLeft: '32px' }}>
          {/* Vertical line */}
          <div style={{
            position: 'absolute',
            left: '14px',
            top: '12px',
            bottom: '12px',
            width: '2px',
            backgroundColor: 'var(--theia-widget-border)',
          }} />

          {events.map((event, i) => this.renderEvent(event, i, run.started_at))}
        </div>
      </div>
    );
  }

  protected renderEvent(event: RunEvent, index: number, runStart: string): React.ReactNode {
    const icon = EVENT_ICONS[event.type] ?? '·';
    const elapsed = new Date(event.timestamp).getTime() - new Date(runStart).getTime();
    const isError = event.type.includes('FAILED');

    return (
      <div key={index} style={{ position: 'relative', marginBottom: '12px', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
        {/* Circle on the line */}
        <div style={{
          position: 'absolute',
          left: '-26px',
          width: '20px',
          height: '20px',
          borderRadius: '50%',
          backgroundColor: isError ? '#ef5350' : 'var(--theia-editor-background)',
          border: `2px solid ${isError ? '#ef5350' : '#4fc3f7'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          zIndex: 1,
        }}>
          {icon}
        </div>

        <div style={{
          flex: 1,
          backgroundColor: 'var(--theia-editor-background)',
          border: `1px solid ${isError ? '#ef5350' : 'var(--theia-widget-border)'}`,
          borderRadius: '6px',
          padding: '8px 12px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontWeight: 600, fontSize: '12px' }}>{event.type}</span>
            <span style={{ fontSize: '10px', color: 'var(--theia-descriptionForeground)' }}>
              +{elapsed}ms
            </span>
          </div>
          {Object.keys(event.data).length > 0 && (
            <pre style={{
              fontSize: '10px',
              margin: 0,
              color: 'var(--theia-descriptionForeground)',
              whiteSpace: 'pre-wrap',
            }}>
              {JSON.stringify(event.data, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  protected statusIcon(status: string): string {
    const icons: Record<string, string> = {
      pending: '⏸',
      running: '▶',
      completed: '✓',
      failed: '✗',
      cancelled: '⊘',
    };
    return icons[status] ?? '?';
  }

  protected async startSwarmGraphRun(): Promise<void> {
    this.loading = true;
    this.update();
    try {
      const result = await this.arcService.startRun('wf-swarmgraph-001');
      if (result.data) {
        this.runs = [result.data, ...this.runs];
        this.selectedRun = result.data;
      }
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected statusColor(status: string): string {
    const colors: Record<string, string> = {
      pending: '#ffb74d',
      running: '#4fc3f7',
      completed: '#4caf50',
      failed: '#ef5350',
      cancelled: '#9e9e9e',
    };
    return colors[status] ?? 'inherit';
  }
}

const iconBtnStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  color: 'var(--theia-foreground)',
  fontSize: '14px',
  padding: '0 2px',
};

const primaryBtnStyle: React.CSSProperties = {
  backgroundColor: 'var(--theia-button-background)',
  color: 'var(--theia-button-foreground)',
  border: 'none',
  borderRadius: '4px',
  padding: '6px 12px',
  cursor: 'pointer',
};
