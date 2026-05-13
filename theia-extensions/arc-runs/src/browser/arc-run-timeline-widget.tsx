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
import { RunRecord, RunEvent, RuntimeCapabilityReport, RuntimeId } from 'arc-core/lib/common/arc-protocol';

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
  protected sseSource?: EventSource;
  protected liveEvents: RunEvent[] = [];
  protected prompt = 'ARC local SwarmGraph smoke run: return one short status sentence.';
  protected workspaceStatus?: { frontendPath: string; backendPath: string; source: string };
  protected lastError?: string;
  protected runStatusMessage?: string;
  protected eventFilter = '';
  protected selectedEvent: RunEvent | null = null;
  protected runtimeCapabilities: RuntimeCapabilityReport[] = [];
  protected selectedRuntime: RuntimeId = 'auto';
  protected runtimeError?: string;

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
      const [workspaceStatus, capabilities] = await Promise.all([
        this.arcService.getWorkspaceStatus().catch(() => undefined),
        this.arcService.listRuntimeCapabilities().catch(error => {
          this.runtimeError = String(error);
          return undefined;
        }),
      ]);
      this.workspaceStatus = workspaceStatus?.data ?? undefined;
      this.runtimeCapabilities = capabilities?.data?.runtimes ?? [];
      this.runtimeError = capabilities?.error?.message ?? this.runtimeError;
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
              <div style={{ fontSize: '10px', color: this.statusColor(run.status), fontWeight: 600 }}>{run.status}</div>
              <div style={{ fontSize: '10px', opacity: 0.7 }}>{run.workflow_id}</div>
              <div style={{ fontSize: '10px', opacity: 0.6 }}>
                {new Date(run.started_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
          {this.runs.length === 0 && (
            <div style={{ padding: '12px', fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
              No runs yet for this workspace.
            </div>
          )}
        </div>

        {/* Timeline */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
          {this.selectedRun ? this.renderTimeline(this.selectedRun) : (
            <div style={{ textAlign: 'center', paddingTop: '48px', color: 'var(--theia-descriptionForeground)' }}>
              <p>No run selected. Start a local stub-backed SwarmGraph run or refresh history.</p>
              {this.renderRunControls()}
            </div>
          )}
        </div>
      </div>
    );
  }

  protected renderTimeline(run: RunRecord): React.ReactNode {
    const events = this.filteredEvents(this.liveEvents.length > 0 ? this.liveEvents : run.events);
    const duration = run.ended_at
      ? new Date(run.ended_at).getTime() - new Date(run.started_at).getTime()
      : null;

    return (
      <div>
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ margin: '0 0 4px 0', fontSize: '15px' }}>
            {this.statusIcon(run.status)} Run: {run.id}
          </h2>
          <button style={secondaryBtnStyle} onClick={() => this.copyText('Run ID', run.id)}>Copy Run ID</button>
          <button style={secondaryBtnStyle} onClick={() => this.replayRun(run)}>Replay Events</button>
          <button style={secondaryBtnStyle} onClick={() => this.clearReplay()}>Show Stored Trace</button>
          <button style={secondaryBtnStyle} disabled={this.streaming} onClick={() => this.connectSseStream(run.id)}>Connect SSE Stream</button>
          <button style={secondaryBtnStyle} onClick={() => this.exportRunJson(run)}>Export Run JSON</button>
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
          {this.renderRunMetadata(run)}
          {this.renderRunControls()}
          {this.renderTraceControls(run, events)}
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
        {this.renderSelectedEvent()}
      </div>
    );
  }

  protected renderTraceControls(run: RunRecord, events: RunEvent[]): React.ReactNode {
    const types = Array.from(new Set(run.events.map(event => event.type))).sort();
    return (
      <div style={{ ...metadataBoxStyle, marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <strong>Trace Viewer:</strong>
        <span>{events.length}/{run.events.length} events</span>
        <select
          style={selectStyle}
          value={this.eventFilter}
          onChange={event => { this.eventFilter = event.currentTarget.value; this.update(); }}
        >
          <option value="">All events</option>
          {types.map(type => <option key={type} value={type}>{type}</option>)}
        </select>
            <button style={secondaryBtnStyle} onClick={() => this.copyText('Trace JSON', JSON.stringify(this.redactValue(run.events), null, 2))}>Copy Trace JSON</button>
      </div>
    );
  }

  protected renderSelectedEvent(): React.ReactNode {
    if (!this.selectedEvent) {
      return null;
    }
    return (
      <div style={{ ...metadataBoxStyle, marginTop: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
          <strong>Selected Event: {this.selectedEvent.type}</strong>
          <button style={secondaryBtnStyle} onClick={() => { this.selectedEvent = null; this.update(); }}>Close</button>
        </div>
        <pre style={outputBoxStyle}>{JSON.stringify(this.redactValue(this.selectedEvent), null, 2)}</pre>
      </div>
    );
  }

  protected renderRunMetadata(run: RunRecord): React.ReactNode {
    const metadata = run.metadata ?? {};
    const tracePath = typeof metadata['trace_path'] === 'string' ? metadata['trace_path'] : '';
    const summary = [
      ['Backend', metadata['backend']],
      ['Provider', metadata['provider']],
      ['Swarm ID', metadata['swarm_id']],
      ['Command', metadata['_external_command']],
    ].filter((entry): entry is [string, string] => typeof entry[1] === 'string' && entry[1].length > 0);
    const finalOutput = this.eventValue(run, 'RUN_COMPLETED', 'final_output') ?? this.eventValue(run, 'MESSAGE', 'output') ?? this.eventValue(run, 'MESSAGE', 'message');
    const errorOutput = this.eventValue(run, 'RUN_FAILED', 'error') ?? this.eventValue(run, 'RUN_FAILED', 'stderr');

    if (summary.length === 0 && !finalOutput && !errorOutput) {
      return null;
    }

    return (
      <div style={{ marginTop: '10px', display: 'grid', gap: '8px' }}>
        {summary.length > 0 && (
          <div style={metadataBoxStyle}>
            {summary.map(([label, value]) => (
              <div key={label}><strong>{label}:</strong> {value}</div>
            ))}
          </div>
        )}
        {tracePath && (
          <div style={metadataBoxStyle}>
            <div><strong>Trace:</strong></div>
            <code style={traceCodeStyle}>{tracePath}</code>
            <button style={secondaryBtnStyle} onClick={() => this.copyText('Trace path', tracePath)}>Copy Trace Path</button>
          </div>
        )}
        {finalOutput && (
          <div style={{ display: 'grid', gap: '6px' }}>
            <pre style={outputBoxStyle}>{finalOutput}</pre>
            <button style={secondaryBtnStyle} onClick={() => this.copyText('Final output', finalOutput)}>Copy Final Output</button>
          </div>
        )}
        {errorOutput && <pre style={{ ...outputBoxStyle, borderColor: '#ef5350', color: '#ef9a9a' }}>{errorOutput}</pre>}
      </div>
    );
  }

  protected renderRunControls(): React.ReactNode {
    return (
      <div style={{ marginTop: '12px', display: 'grid', gap: '8px', maxWidth: 640 }}>
        <div style={{ fontSize: '11px', color: 'var(--theia-descriptionForeground)' }}>
          Workspace: <strong>{this.workspaceStatus?.backendPath || 'unresolved'}</strong> · Source: {this.workspaceStatus?.source ?? 'unknown'}
        </div>
        <textarea
          style={promptInputStyle}
          rows={3}
          value={this.prompt}
          onChange={event => { this.prompt = event.currentTarget.value; this.update(); }}
          placeholder="Prompt for local SwarmGraph stub run"
        />
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ fontSize: '11px' }}>
            Runtime:{' '}
            <select
              aria-label="Runtime"
              data-testid="arc-runtime-picker"
              style={selectStyle}
              value={this.selectedRuntime}
              onChange={event => { this.selectedRuntime = event.currentTarget.value as RuntimeId; this.update(); }}
            >
              <option value="auto">Auto</option>
              {this.runtimeCapabilities.map(runtime => (
                <option key={runtime.runtime_id} value={runtime.runtime_id} disabled={!runtime.can_run}>
                  {this.runtimeLabel(runtime)}
                </option>
              ))}
            </select>
          </label>
          <button style={primaryBtnStyle} onClick={() => this.startRuntimeRun()}>Start Run</button>
          <button style={secondaryBtnStyle} onClick={() => this.refreshWorkspace()}>Refresh Workspace</button>
        </div>
        {this.runtimeError && <div style={{ fontSize: '11px', color: '#ffb74d' }}>Runtime capabilities: {this.runtimeError}</div>}
        {this.runStatusMessage && <div style={statusMessageStyle}>{this.runStatusMessage}</div>}
        {this.lastError && <pre style={{ ...outputBoxStyle, borderColor: '#ef5350', color: '#ef9a9a' }}>{this.lastError}</pre>}
      </div>
    );
  }

  protected eventValue(run: RunRecord, type: string, key: string): string | undefined {
    for (let i = run.events.length - 1; i >= 0; i--) {
      const event = run.events[i];
      const value = event.type === type ? event.data[key] : undefined;
      if (typeof value === 'string' && value.length > 0) {
        return value;
      }
    }
    return undefined;
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
        }} onClick={() => { this.selectedEvent = event; this.update(); }}>
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
              {JSON.stringify(this.redactValue(event.data), null, 2)}
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

  protected runtimeLabel(runtime: RuntimeCapabilityReport): string {
    const status = runtime.can_run ? 'run' : runtime.availability.replace(/_/g, ' ');
    const paid = runtime.requires_paid_calls ? ', paid' : '';
    return `${runtime.runtime_id} (${status}${paid})`;
  }

  protected async startRuntimeRun(): Promise<void> {
    this.loading = true;
    this.lastError = undefined;
    this.runStatusMessage = `Starting ${this.selectedRuntime} run...`;
    this.update();
    try {
      const paid = this.runtimeCapabilities.find(
        r => r.runtime_id === this.selectedRuntime
      )?.requires_paid_calls === true;
      const result = await this.arcService.startRun('wf-swarmgraph-001', {
        prompt: this.prompt,
        workspacePath: this.workspaceStatus?.frontendPath,
      }, this.selectedRuntime, paid ? true : undefined);
      if (result.data) {
        this.runs = [result.data, ...this.runs];
        this.selectedRun = result.data;
        this.runStatusMessage = result.data.status === 'completed'
          ? 'Run completed.'
          : `Run ${result.data.status}.`;
      } else if (result.error) {
        this.lastError = result.error.message;
        this.runStatusMessage = 'Run failed.';
      }
    } catch (error) {
      this.lastError = String(error);
      this.runStatusMessage = 'Run failed.';
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected async refreshWorkspace(): Promise<void> {
    this.workspaceStatus = (await this.arcService.getWorkspaceStatus().catch(() => undefined))?.data ?? undefined;
    await this.loadRuns();
  }

  protected filteredEvents(events: RunEvent[]): RunEvent[] {
    return this.eventFilter ? events.filter(event => event.type === this.eventFilter) : events;
  }

  protected clearReplay(): void {
    this.liveEvents = [];
    this.selectedEvent = null;
    this.runStatusMessage = 'Showing stored trace.';
    this.update();
  }

  protected exportRunJson(run: RunRecord): void {
    const json = JSON.stringify(this.redactValue(run), null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${run.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
    this.runStatusMessage = 'Run JSON exported.';
    this.update();
  }

  protected async replayRun(run: RunRecord): Promise<void> {
    this.liveEvents = [];
    this.runStatusMessage = `Replaying ${run.events.length} events...`;
    this.update();
    for (const event of run.events) {
      this.liveEvents = [...this.liveEvents, event];
      this.update();
      await new Promise(resolve => setTimeout(resolve, 120));
    }
    this.runStatusMessage = 'Replay complete.';
    this.update();
  }

  protected connectSseStream(runId: string): void {
    if (this.sseSource) {
      this.sseSource.close();
    }
    const host = window.location.hostname || '127.0.0.1';
    const url = `http://${host}:7777/api/runs/${encodeURIComponent(runId)}/events`;
    this.liveEvents = [];
    this.streaming = true;
    this.runStatusMessage = 'Connecting to local SSE stream...';
    const source = new EventSource(url);
    this.sseSource = source;
    source.onmessage = message => {
      const event = JSON.parse(message.data) as RunEvent;
      if (event.type === 'STREAM_END') {
        source.close();
        this.sseSource = undefined;
        this.streaming = false;
        this.runStatusMessage = 'SSE stream complete.';
      } else {
        this.liveEvents = [...this.liveEvents, event];
        this.runStatusMessage = `Streaming ${this.liveEvents.length} events...`;
      }
      this.update();
    };
    source.onerror = () => {
      source.close();
      this.sseSource = undefined;
      this.streaming = false;
      this.lastError = `SSE stream unavailable at ${url}. Start \`uv run arc serve\`.`;
      this.update();
    };
    this.update();
  }

  protected redactValue(value: unknown): unknown {
    if (typeof value === 'string') {
      return value
        .replace(/sk-[A-Za-z0-9_-]{8,}/g, 'sk-REDACTED')
        .replace(/(api[_-]?key\s*[=:]\s*)[^\s]+/ig, '$1REDACTED')
        .replace(/(authorization:\s*bearer\s+)[^\s]+/ig, '$1REDACTED');
    }
    if (Array.isArray(value)) {
      return value.map(item => this.redactValue(item));
    }
    if (value && typeof value === 'object') {
      return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key,
        /(key|token|password|secret|credential|auth)/i.test(key) ? '[REDACTED]' : this.redactValue(item),
      ]));
    }
    return value;
  }

  protected async copyText(label: string, value: string): Promise<void> {
    try {
      await navigator.clipboard?.writeText(value);
      this.lastError = undefined;
      this.runStatusMessage = `${label} copied.`;
    } catch (error) {
      this.lastError = `Copy failed: ${error}`;
    }
    this.update();
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

const secondaryBtnStyle: React.CSSProperties = {
  backgroundColor: 'var(--theia-secondaryButton-background)',
  color: 'var(--theia-secondaryButton-foreground)',
  border: 'none',
  borderRadius: '4px',
  padding: '6px 12px',
  cursor: 'pointer',
};

const promptInputStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  color: 'var(--theia-input-foreground)',
  backgroundColor: 'var(--theia-input-background)',
  border: '1px solid var(--theia-input-border)',
  borderRadius: '4px',
  padding: '6px 8px',
  resize: 'vertical',
};

const metadataBoxStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: '4px',
  backgroundColor: 'var(--theia-editor-background)',
  fontSize: '11px',
};

const outputBoxStyle: React.CSSProperties = {
  margin: 0,
  padding: '8px 10px',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: '4px',
  backgroundColor: 'var(--theia-editor-background)',
  color: 'var(--theia-foreground)',
  fontSize: '11px',
  whiteSpace: 'pre-wrap',
};

const traceCodeStyle: React.CSSProperties = {
  display: 'block',
  margin: '6px 0',
  padding: '6px 8px',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: '4px',
  wordBreak: 'break-all',
};

const selectStyle: React.CSSProperties = {
  color: 'var(--theia-dropdown-foreground)',
  backgroundColor: 'var(--theia-dropdown-background)',
  border: '1px solid var(--theia-dropdown-border)',
  borderRadius: '4px',
  padding: '4px 6px',
};

const statusMessageStyle: React.CSSProperties = {
  padding: '6px 8px',
  border: '1px solid var(--theia-widget-border)',
  borderRadius: '4px',
  backgroundColor: 'var(--theia-editor-background)',
  fontSize: '11px',
};
