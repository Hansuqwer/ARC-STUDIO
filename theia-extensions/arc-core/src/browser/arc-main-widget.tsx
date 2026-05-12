/**
 * ARC Main Widget — the primary ARC Studio panel
 *
 * Renders in the left Activity Bar panel.
 * Source: https://theia-ide.org/docs/widgets/
 * Source: https://theia-ide.org/docs/widgets/#react-based-widget
 */

import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { MessageService } from '@theia/core/lib/common/message-service';
import { ArcFrontendService } from './arc-frontend-service';
import { RuntimeInfo, WorkflowInfo, SchemaInfo, WorkspaceInfo } from '../common/arc-protocol';

@injectable()
export class ArcMainWidget extends ReactWidget {
  static readonly ID = 'arc:main-widget';
  static readonly LABEL = 'ARC';

  @inject(MessageService)
  protected readonly messageService: MessageService;

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  // State
  protected loading = false;
  protected error: string | null = null;
  protected workspaceInfo: WorkspaceInfo | null = null;
  protected runtimes: RuntimeInfo[] = [];
  protected workflows: WorkflowInfo[] = [];
  protected schemas: SchemaInfo[] = [];
  protected daemonStatus: { running: boolean; version: string } | null = null;
  protected activeTab: 'overview' | 'runtimes' | 'workflows' | 'schemas' | 'runs' = 'overview';

  @postConstruct()
  protected init(): void {
    this.id = ArcMainWidget.ID;
    this.title.label = ArcMainWidget.LABEL;
    this.title.caption = 'ARC — Agent Runtime Cockpit';
    this.title.iconClass = 'arc-icon codicon codicon-circuit-board';
    this.title.closable = true;
    this.node.classList.add('arc-main-widget');

    // Load initial data
    this.loadAll();
  }

  protected async loadAll(): Promise<void> {
    this.loading = true;
    this.update();

    try {
      const [statusResult, runtimesResult] = await Promise.all([
        this.arcService.getDaemonStatus(),
        this.arcService.listRuntimes(),
      ]);

      this.daemonStatus = statusResult.data;
      this.runtimes = runtimesResult.data ?? [];

      if (this.runtimes.length > 0) {
        const [workflowsResult, schemasResult] = await Promise.all([
          this.arcService.listWorkflows(),
          this.arcService.listSchemas(),
        ]);
        this.workflows = workflowsResult.data ?? [];
        this.schemas = schemasResult.data ?? [];
      }

      this.error = null;
    } catch (e) {
      this.error = `Failed to load ARC data: ${e}`;
    } finally {
      this.loading = false;
      this.update();
    }
  }

  protected render(): React.ReactNode {
    return (
      <div className="arc-panel" style={styles.panel}>
        {this.renderHeader()}
        {this.renderTabs()}
        {this.renderContent()}
      </div>
    );
  }

  protected renderHeader(): React.ReactNode {
    return (
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <span style={styles.headerIcon}>⬡</span>
          <span style={styles.headerText}>ARC Studio</span>
        </div>
        <div style={styles.headerActions}>
          <button
            style={styles.iconBtn}
            onClick={() => this.loadAll()}
            title="Refresh"
          >
            ↻
          </button>
        </div>
        {this.daemonStatus && (
          <div style={{
            ...styles.daemonBadge,
            backgroundColor: this.daemonStatus.running ? '#2d5a2d' : '#5a2d2d',
          }}>
            {this.daemonStatus.running ? '● daemon online' : '○ daemon offline'}
          </div>
        )}
      </div>
    );
  }

  protected renderTabs(): React.ReactNode {
    const tabs: Array<{ id: typeof this.activeTab; label: string; count?: number }> = [
      { id: 'overview', label: 'Overview' },
      { id: 'runtimes', label: 'Runtimes', count: this.runtimes.length },
      { id: 'workflows', label: 'Workflows', count: this.workflows.length },
      { id: 'schemas', label: 'Schemas', count: this.schemas.length },
      { id: 'runs', label: 'Runs' },
    ];

    return (
      <div style={styles.tabs}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            style={{
              ...styles.tab,
              ...(this.activeTab === tab.id ? styles.tabActive : {}),
            }}
            onClick={() => { this.activeTab = tab.id; this.update(); }}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span style={styles.tabCount}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>
    );
  }

  protected renderContent(): React.ReactNode {
    if (this.loading) {
      return (
        <div style={styles.loading}>
          <div style={styles.spinner}>⟳</div>
          <span>Loading ARC data...</span>
        </div>
      );
    }

    if (this.error) {
      return (
        <div style={styles.error}>
          <div style={styles.errorIcon}>⚠</div>
          <div style={styles.errorText}>{this.error}</div>
          <button style={styles.retryBtn} onClick={() => this.loadAll()}>Retry</button>
        </div>
      );
    }

    switch (this.activeTab) {
      case 'overview': return this.renderOverview();
      case 'runtimes': return this.renderRuntimes();
      case 'workflows': return this.renderWorkflows();
      case 'schemas': return this.renderSchemas();
      case 'runs': return this.renderRuns();
      default: return null;
    }
  }

  protected renderOverview(): React.ReactNode {
    const mockWarnings = this.runtimes.some(r =>
      r.evidence.some(e => e.includes('[MOCK]'))
    );

    return (
      <div style={styles.content}>
        {mockWarnings && (
          <div style={styles.mockWarning}>
            ⚠ Using fixture data. Run <code>uv run arc serve</code> for live data.
          </div>
        )}

        <div style={styles.statsGrid}>
          <div style={styles.stat}>
            <div style={styles.statNumber}>{this.runtimes.length}</div>
            <div style={styles.statLabel}>Runtimes</div>
          </div>
          <div style={styles.stat}>
            <div style={styles.statNumber}>{this.workflows.length}</div>
            <div style={styles.statLabel}>Workflows</div>
          </div>
          <div style={styles.stat}>
            <div style={styles.statNumber}>{this.schemas.length}</div>
            <div style={styles.statLabel}>Schemas</div>
          </div>
        </div>

        {this.runtimes.length === 0 && (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>📂</div>
            <div style={styles.emptyText}>No runtimes detected</div>
            <div style={styles.emptyHint}>
              Open a workspace containing a SwarmGraph or LangGraph project
            </div>
          </div>
        )}
      </div>
    );
  }

  protected renderRuntimes(): React.ReactNode {
    return (
      <div style={styles.content}>
        {this.runtimes.map(rt => (
          <div key={rt.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.cardTitle}>{rt.name}</span>
              <span style={{
                ...styles.confidence,
                color: rt.confidence === 'high' ? '#4fc3f7' : rt.confidence === 'medium' ? '#ffb74d' : '#ef5350',
              }}>
                {rt.confidence}
              </span>
            </div>
            <div style={styles.cardMeta}>
              <span style={styles.badge}>{rt.adapter}</span>
            </div>
            <div style={styles.cardCapabilities}>
              {Object.entries(rt.capabilities).map(([cap, val]) => (
                <span key={cap} style={{ ...styles.cap, opacity: val ? 1 : 0.4 }}>
                  {val ? '✓' : '✗'} {cap.replace('can_', '').replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  protected renderWorkflows(): React.ReactNode {
    return (
      <div style={styles.content}>
        {this.workflows.map(wf => (
          <div key={wf.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.cardTitle}>{wf.name}</span>
              <span style={styles.badge}>{wf.runtime}</span>
            </div>
            <div style={styles.cardMeta}>
              <span style={styles.metaItem}>
                {wf.nodes.length} nodes · {wf.edges.length} edges
              </span>
            </div>
            {wf.source_file && (
              <div style={styles.cardMeta}>
                <code style={styles.codeSmall}>{wf.source_file}</code>
              </div>
            )}
          </div>
        ))}
        {this.workflows.length === 0 && (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>⎘</div>
            <div style={styles.emptyText}>No workflows found</div>
          </div>
        )}
      </div>
    );
  }

  protected renderSchemas(): React.ReactNode {
    return (
      <div style={styles.content}>
        {this.schemas.map(s => (
          <div key={s.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.cardTitle}>{s.name}</span>
              <span style={styles.badge}>{s.runtime}</span>
            </div>
            {s.source_file && (
              <div style={styles.cardMeta}>
                <code style={styles.codeSmall}>{s.source_file}</code>
              </div>
            )}
            <details style={styles.details}>
              <summary style={styles.detailsSummary}>View JSON Schema</summary>
              <pre style={styles.jsonPre}>
                {JSON.stringify(s.schema, null, 2)}
              </pre>
            </details>
          </div>
        ))}
      </div>
    );
  }

  protected renderRuns(): React.ReactNode {
    return (
      <div style={styles.content}>
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>▶</div>
          <div style={styles.emptyText}>No runs yet</div>
          <div style={styles.emptyHint}>
            Select a workflow and press "Run" to start
          </div>
        </div>
      </div>
    );
  }
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
    fontFamily: 'var(--theia-ui-font-family)',
    fontSize: 'var(--theia-ui-font-size1)',
    color: 'var(--theia-foreground)',
    backgroundColor: 'var(--theia-sideBar-background)',
  },
  header: {
    padding: '12px 16px 8px',
    borderBottom: '1px solid var(--theia-widget-border)',
    flexShrink: 0,
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '4px',
  },
  headerIcon: { fontSize: '18px', color: '#4fc3f7' },
  headerText: { fontWeight: 600, fontSize: '14px' },
  headerActions: { position: 'absolute', right: '12px', top: '12px' },
  iconBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--theia-foreground)',
    fontSize: '18px',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  daemonBadge: {
    fontSize: '10px',
    padding: '2px 8px',
    borderRadius: '10px',
    color: '#fff',
    marginTop: '4px',
    display: 'inline-block',
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--theia-widget-border)',
    overflowX: 'auto',
    flexShrink: 0,
  },
  tab: {
    padding: '8px 12px',
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    color: 'var(--theia-descriptionForeground)',
    fontSize: '12px',
    whiteSpace: 'nowrap',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  tabActive: {
    color: 'var(--theia-foreground)',
    borderBottomColor: '#4fc3f7',
  },
  tabCount: {
    backgroundColor: 'var(--theia-badge-background)',
    color: 'var(--theia-badge-foreground)',
    borderRadius: '8px',
    padding: '0 5px',
    fontSize: '10px',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: '12px',
    color: 'var(--theia-descriptionForeground)',
  },
  spinner: { fontSize: '32px', animation: 'spin 1s linear infinite' },
  error: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '24px',
    gap: '12px',
  },
  errorIcon: { fontSize: '32px', color: '#ef5350' },
  errorText: {
    color: '#ef5350',
    fontSize: '13px',
    textAlign: 'center',
    maxWidth: '300px',
  },
  retryBtn: {
    padding: '6px 16px',
    backgroundColor: '#4fc3f7',
    color: '#000',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  mockWarning: {
    backgroundColor: '#5a3d00',
    border: '1px solid #ffb74d',
    borderRadius: '4px',
    padding: '8px 12px',
    marginBottom: '12px',
    fontSize: '12px',
    color: '#ffb74d',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '8px',
    marginBottom: '16px',
  },
  stat: {
    backgroundColor: 'var(--theia-editor-background)',
    border: '1px solid var(--theia-widget-border)',
    borderRadius: '6px',
    padding: '12px',
    textAlign: 'center',
  },
  statNumber: { fontSize: '24px', fontWeight: 700, color: '#4fc3f7' },
  statLabel: { fontSize: '11px', color: 'var(--theia-descriptionForeground)', marginTop: '4px' },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '32px 16px',
    gap: '8px',
  },
  emptyIcon: { fontSize: '32px' },
  emptyText: { fontWeight: 600, color: 'var(--theia-foreground)' },
  emptyHint: { fontSize: '12px', color: 'var(--theia-descriptionForeground)', textAlign: 'center' },
  card: {
    backgroundColor: 'var(--theia-editor-background)',
    border: '1px solid var(--theia-widget-border)',
    borderRadius: '6px',
    padding: '12px',
    marginBottom: '8px',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  cardTitle: { fontWeight: 600, fontSize: '13px' },
  cardMeta: { marginBottom: '4px' },
  cardCapabilities: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginTop: '8px',
  },
  cap: { fontSize: '10px', color: 'var(--theia-descriptionForeground)' },
  confidence: { fontSize: '11px', fontWeight: 600 },
  badge: {
    backgroundColor: 'var(--theia-badge-background)',
    color: 'var(--theia-badge-foreground)',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '11px',
  },
  metaItem: { fontSize: '12px', color: 'var(--theia-descriptionForeground)' },
  codeSmall: {
    fontSize: '11px',
    backgroundColor: 'var(--theia-textCodeBlock-background)',
    padding: '1px 4px',
    borderRadius: '2px',
    color: 'var(--theia-descriptionForeground)',
  },
  details: { marginTop: '8px' },
  detailsSummary: {
    cursor: 'pointer',
    fontSize: '12px',
    color: 'var(--theia-textLink-foreground)',
  },
  jsonPre: {
    fontSize: '11px',
    backgroundColor: 'var(--theia-textCodeBlock-background)',
    padding: '8px',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '300px',
    color: 'var(--theia-foreground)',
    margin: '8px 0 0 0',
  },
};
