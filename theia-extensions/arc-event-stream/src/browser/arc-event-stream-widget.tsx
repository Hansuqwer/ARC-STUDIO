/**
 * ARC Event Stream Widget
 *
 * Universal AG-UI event renderer for all runtime adapters.
 * Displays agent lifecycle events (agent start/end, tool calls, handoffs, state snapshots).
 * 
 * Source: packages/arc-ag-ui (canonical AG-UI mapping layer)
 * Spec: docs/AG_UI_MAPPING.md
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';
import { RunRecord, RunEvent } from 'arc-core/lib/common/arc-protocol';

// AG-UI Event Type Icons (33 canonical types from packages/arc-ag-ui/src/event-types.ts)
const EVENT_ICONS: Record<string, string> = {
  // Run lifecycle
  RUN_STARTED: '▶️',
  RUN_FINISHED: '✅',
  RUN_ERROR: '❌',
  
  // Step lifecycle
  STEP_STARTED: '🔵',
  STEP_FINISHED: '⚪',
  
  // Text messages
  TEXT_MESSAGE_START: '💬',
  TEXT_MESSAGE_CONTENT: '📝',
  TEXT_MESSAGE_END: '✓',
  TEXT_MESSAGE_CHUNK: '📄',
  
  // Tool calls
  TOOL_CALL_START: '🔧',
  TOOL_CALL_ARGS: '📋',
  TOOL_CALL_END: '✓',
  TOOL_CALL_CHUNK: '⚙️',
  TOOL_CALL_RESULT: '📦',
  
  // State
  STATE_SNAPSHOT: '📸',
  STATE_DELTA: '🔄',
  
  // Messages
  MESSAGES_SNAPSHOT: '💾',
  
  // Activity
  ACTIVITY_SNAPSHOT: '📊',
  ACTIVITY_DELTA: '📈',
  
  // Reasoning
  REASONING_START: '🧠',
  REASONING_MESSAGE_START: '💭',
  REASONING_MESSAGE_CONTENT: '💡',
  REASONING_MESSAGE_END: '✓',
  REASONING_MESSAGE_CHUNK: '🤔',
  REASONING_END: '✓',
  REASONING_ENCRYPTED_VALUE: '🔒',
  
  // Fallback
  RAW: '📄',
  CUSTOM: '🔖',
  
  // Legacy (for backward compatibility)
  AGENT_START: '🤖',
  AGENT_END: '✓',
  TOOL_START: '🔧',
  TOOL_END: '✓',
  HANDOFF: '🔀',
  NODE_STARTED: '◉',
  NODE_COMPLETED: '●',
  NODE_FAILED: '⚠️',
  MESSAGE: '💬',
};

// Event type colors
const EVENT_COLORS: Record<string, string> = {
  RUN_STARTED: '#4CAF50',
  RUN_FINISHED: '#4CAF50',
  RUN_ERROR: '#F44336',
  STEP_STARTED: '#2196F3',
  STEP_FINISHED: '#9E9E9E',
  TOOL_CALL_START: '#FF9800',
  TOOL_CALL_RESULT: '#FF9800',
  TEXT_MESSAGE_CONTENT: '#9C27B0',
  STATE_SNAPSHOT: '#00BCD4',
  HANDOFF: '#E91E63',
  RAW: '#757575',
  CUSTOM: '#607D8B',
};

interface EventStreamState {
  runs: RunRecord[];
  selectedRun: RunRecord | null;
  events: RunEvent[];
  selectedEvent: RunEvent | null;
  loading: boolean;
  filter: string;
  autoScroll: boolean;
}

@injectable()
export class ArcEventStreamWidget extends ReactWidget {
  static readonly ID = 'arc:event-stream';
  static readonly LABEL = 'ARC Event Stream';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  protected state: EventStreamState = {
    runs: [],
    selectedRun: null,
    events: [],
    selectedEvent: null,
    loading: false,
    filter: '',
    autoScroll: true,
  };

  @postConstruct()
  protected init(): void {
    this.id = ArcEventStreamWidget.ID;
    this.title.label = ArcEventStreamWidget.LABEL;
    this.title.closable = true;
    this.title.caption = 'ARC Event Stream - Universal AG-UI Event Renderer';
    this.loadRuns();
  }

  protected async loadRuns(): Promise<void> {
    this.state.loading = true;
    this.update();
    try {
      const result = await this.arcService.listRuns();
      this.state.runs = result.data ?? [];
      if (this.state.runs.length > 0 && !this.state.selectedRun) {
        await this.selectRun(this.state.runs[0]);
      }
    } catch (error) {
      console.error('Failed to load runs:', error);
    } finally {
      this.state.loading = false;
      this.update();
    }
  }

  protected async selectRun(run: RunRecord): Promise<void> {
    this.state.selectedRun = run;
    this.state.events = run.events ?? [];
    this.state.selectedEvent = null;
    this.update();
    
    // Auto-scroll to bottom if enabled
    if (this.state.autoScroll) {
      setTimeout(() => this.scrollToBottom(), 100);
    }
  }

  protected selectEvent(event: RunEvent): void {
    this.state.selectedEvent = this.state.selectedEvent?.sequence === event.sequence ? null : event;
    this.update();
  }

  protected setFilter(filter: string): void {
    this.state.filter = filter;
    this.update();
  }

  protected toggleAutoScroll(): void {
    this.state.autoScroll = !this.state.autoScroll;
    this.update();
  }

  protected scrollToBottom(): void {
    const eventList = this.node.querySelector('.event-list');
    if (eventList) {
      eventList.scrollTop = eventList.scrollHeight;
    }
  }

  protected getFilteredEvents(): RunEvent[] {
    if (!this.state.filter) {
      return this.state.events;
    }
    const filterLower = this.state.filter.toLowerCase();
    return this.state.events.filter(event =>
      event.type.toLowerCase().includes(filterLower) ||
      JSON.stringify(event.data).toLowerCase().includes(filterLower)
    );
  }

  protected render(): React.ReactNode {
    if (this.state.loading) {
      return <div style={styles.loading}>Loading runs…</div>;
    }

    const filteredEvents = this.getFilteredEvents();

    return (
      <div style={styles.container}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerTitle}>
            <span style={styles.headerIcon}>📡</span>
            <span>Event Stream</span>
            {this.state.selectedRun && (
              <span style={styles.headerSubtitle}>
                {this.state.selectedRun.runtime} · {this.state.selectedRun.id}
              </span>
            )}
          </div>
          <div style={styles.headerActions}>
            <input
              type="text"
              placeholder="Filter events..."
              value={this.state.filter}
              onChange={e => this.setFilter(e.target.value)}
              style={styles.filterInput}
            />
            <button
              onClick={() => this.toggleAutoScroll()}
              style={{
                ...styles.button,
                backgroundColor: this.state.autoScroll ? 'var(--theia-button-background)' : 'transparent',
              }}
              title={this.state.autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {this.state.autoScroll ? '📌' : '📍'}
            </button>
            <button onClick={() => this.loadRuns()} style={styles.button} title="Refresh">
              ↻
            </button>
          </div>
        </div>

        <div style={styles.content}>
          {/* Run List Sidebar */}
          <div style={styles.sidebar}>
            <div style={styles.sidebarHeader}>
              Runs ({this.state.runs.length})
            </div>
            <div style={styles.runList}>
              {this.state.runs.map(run => (
                <div
                  key={run.id}
                  onClick={() => this.selectRun(run)}
                  style={{
                    ...styles.runItem,
                    backgroundColor: this.state.selectedRun?.id === run.id
                      ? 'var(--theia-list-activeSelectionBackground)'
                      : 'transparent',
                  }}
                >
                  <div style={styles.runItemHeader}>
                    <span style={styles.runStatus}>{this.getRunStatusIcon(run.status)}</span>
                    <span style={styles.runRuntime}>{run.runtime}</span>
                  </div>
                  <div style={styles.runId}>{run.id}</div>
                  <div style={styles.runMeta}>
                    {run.events?.length ?? 0} events
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Event List */}
          <div style={styles.eventPanel}>
            {this.state.selectedRun ? (
              <React.Fragment>
                <div style={styles.eventListHeader}>
                  <span>
                    {filteredEvents.length} events
                    {this.state.filter && ` (filtered from ${this.state.events.length})`}
                  </span>
                </div>
                <div className="event-list" style={styles.eventList}>
                  {filteredEvents.map((event, idx) => (
                    <div
                      key={`${event.sequence}-${idx}`}
                      onClick={() => this.selectEvent(event)}
                      style={{
                        ...styles.eventItem,
                        backgroundColor: this.state.selectedEvent?.sequence === event.sequence
                          ? 'var(--theia-list-activeSelectionBackground)'
                          : idx % 2 === 0
                          ? 'var(--theia-list-hoverBackground)'
                          : 'transparent',
                      }}
                    >
                      <div style={styles.eventHeader}>
                        <span style={styles.eventSequence}>#{event.sequence}</span>
                        <span style={styles.eventIcon}>{EVENT_ICONS[event.type] || '📄'}</span>
                        <span
                          style={{
                            ...styles.eventType,
                            color: EVENT_COLORS[event.type] || 'var(--theia-foreground)',
                          }}
                        >
                          {event.type}
                        </span>
                        <span style={styles.eventTimestamp}>
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      {this.renderEventPreview(event)}
                    </div>
                  ))}
                </div>
              </React.Fragment>
            ) : (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>📡</div>
                <div>Select a run to view events</div>
              </div>
            )}
          </div>

          {/* Event Detail Drawer */}
          {this.state.selectedEvent && (
            <div style={styles.detailDrawer}>
              <div style={styles.detailHeader}>
                <span style={styles.detailTitle}>Event Detail</span>
                <button
                  onClick={() => this.selectEvent(this.state.selectedEvent!)}
                  style={styles.closeButton}
                >
                  ✕
                </button>
              </div>
              <div style={styles.detailContent}>
                {this.renderEventDetail(this.state.selectedEvent)}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  protected getRunStatusIcon(status: string): string {
    switch (status) {
      case 'completed': return '✅';
      case 'failed': return '❌';
      case 'running': return '▶️';
      case 'pending': return '⏳';
      case 'cancelled': return '⏹️';
      default: return '❓';
    }
  }

  protected renderEventPreview(event: RunEvent): React.ReactNode {
    const data = event.data;
    
    // Extract meaningful preview based on event type
    let preview = '';
    
    if (data.message) {
      preview = String(data.message).substring(0, 100);
    } else if (data.delta) {
      preview = String(data.delta).substring(0, 100);
    } else if (data.content) {
      preview = String(data.content).substring(0, 100);
    } else if (data.toolCallName || data.tool_name) {
      preview = `Tool: ${data.toolCallName || data.tool_name}`;
    } else if (data.stepName || data.agent_name) {
      preview = `Step: ${data.stepName || data.agent_name}`;
    } else if (data.error) {
      preview = `Error: ${String(data.error).substring(0, 100)}`;
    }
    
    if (preview) {
      return <div style={styles.eventPreview}>{preview}</div>;
    }
    
    return null;
  }

  protected renderEventDetail(event: RunEvent): React.ReactNode {
    return (
      <div style={styles.detailJson}>
        <div style={styles.detailSection}>
          <div style={styles.detailLabel}>Type</div>
          <div style={styles.detailValue}>{event.type}</div>
        </div>
        <div style={styles.detailSection}>
          <div style={styles.detailLabel}>Sequence</div>
          <div style={styles.detailValue}>#{event.sequence}</div>
        </div>
        <div style={styles.detailSection}>
          <div style={styles.detailLabel}>Timestamp</div>
          <div style={styles.detailValue}>{new Date(event.timestamp).toISOString()}</div>
        </div>
        <div style={styles.detailSection}>
          <div style={styles.detailLabel}>Run ID</div>
          <div style={styles.detailValue}>{event.run_id}</div>
        </div>
        <div style={styles.detailSection}>
          <div style={styles.detailLabel}>Data</div>
          <pre style={styles.detailPre}>
            {JSON.stringify(event.data, null, 2)}
          </pre>
        </div>
      </div>
    );
  }
}

// Styles
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    fontFamily: 'var(--theia-ui-font-family)',
    color: 'var(--theia-foreground)',
    backgroundColor: 'var(--theia-editor-background)',
  },
  loading: {
    padding: '24px',
    textAlign: 'center' as const,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid var(--theia-widget-border)',
    backgroundColor: 'var(--theia-sideBar-background)',
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    fontWeight: 600,
  },
  headerIcon: {
    fontSize: '18px',
  },
  headerSubtitle: {
    fontSize: '12px',
    color: 'var(--theia-descriptionForeground)',
    marginLeft: '8px',
  },
  headerActions: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  filterInput: {
    padding: '4px 8px',
    fontSize: '12px',
    border: '1px solid var(--theia-input-border)',
    backgroundColor: 'var(--theia-input-background)',
    color: 'var(--theia-input-foreground)',
    borderRadius: '3px',
    outline: 'none',
  },
  button: {
    padding: '4px 8px',
    fontSize: '14px',
    border: '1px solid var(--theia-button-border)',
    backgroundColor: 'transparent',
    color: 'var(--theia-button-foreground)',
    cursor: 'pointer',
    borderRadius: '3px',
  },
  content: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  sidebar: {
    width: '250px',
    borderRight: '1px solid var(--theia-widget-border)',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--theia-sideBar-background)',
  },
  sidebarHeader: {
    padding: '8px 12px',
    fontSize: '12px',
    fontWeight: 600,
    borderBottom: '1px solid var(--theia-widget-border)',
  },
  runList: {
    flex: 1,
    overflow: 'auto',
  },
  runItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    borderBottom: '1px solid var(--theia-widget-border)',
    fontSize: '12px',
  },
  runItemHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '4px',
  },
  runStatus: {
    fontSize: '14px',
  },
  runRuntime: {
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    fontSize: '11px',
  },
  runId: {
    fontSize: '11px',
    color: 'var(--theia-descriptionForeground)',
    marginBottom: '4px',
    fontFamily: 'monospace',
  },
  runMeta: {
    fontSize: '11px',
    color: 'var(--theia-descriptionForeground)',
  },
  eventPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  eventListHeader: {
    padding: '8px 12px',
    fontSize: '12px',
    fontWeight: 600,
    borderBottom: '1px solid var(--theia-widget-border)',
    backgroundColor: 'var(--theia-sideBar-background)',
  },
  eventList: {
    flex: 1,
    overflow: 'auto',
  },
  eventItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    borderBottom: '1px solid var(--theia-widget-border)',
    fontSize: '12px',
  },
  eventHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '4px',
  },
  eventSequence: {
    fontSize: '11px',
    color: 'var(--theia-descriptionForeground)',
    fontFamily: 'monospace',
    minWidth: '30px',
  },
  eventIcon: {
    fontSize: '14px',
  },
  eventType: {
    fontWeight: 600,
    fontSize: '11px',
    fontFamily: 'monospace',
  },
  eventTimestamp: {
    marginLeft: 'auto',
    fontSize: '11px',
    color: 'var(--theia-descriptionForeground)',
    fontFamily: 'monospace',
  },
  eventPreview: {
    fontSize: '11px',
    color: 'var(--theia-descriptionForeground)',
    marginTop: '4px',
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--theia-descriptionForeground)',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  detailDrawer: {
    width: '400px',
    borderLeft: '1px solid var(--theia-widget-border)',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--theia-sideBar-background)',
  },
  detailHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    borderBottom: '1px solid var(--theia-widget-border)',
  },
  detailTitle: {
    fontSize: '12px',
    fontWeight: 600,
  },
  closeButton: {
    padding: '2px 6px',
    fontSize: '14px',
    border: 'none',
    backgroundColor: 'transparent',
    color: 'var(--theia-foreground)',
    cursor: 'pointer',
  },
  detailContent: {
    flex: 1,
    overflow: 'auto',
    padding: '12px',
  },
  detailJson: {
    fontSize: '11px',
  },
  detailSection: {
    marginBottom: '16px',
  },
  detailLabel: {
    fontSize: '10px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    color: 'var(--theia-descriptionForeground)',
    marginBottom: '4px',
  },
  detailValue: {
    fontFamily: 'monospace',
    fontSize: '11px',
  },
  detailPre: {
    fontFamily: 'monospace',
    fontSize: '11px',
    backgroundColor: 'var(--theia-editor-background)',
    padding: '8px',
    borderRadius: '3px',
    overflow: 'auto',
    maxHeight: '400px',
  },
};
