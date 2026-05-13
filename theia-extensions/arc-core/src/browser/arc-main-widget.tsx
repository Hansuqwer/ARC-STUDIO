/**
 * ARC Main Widget — the primary ARC Studio panel
 *
 * Renders in the left Activity Bar panel with a workflow-first layout:
 * Quick Actions, Runtime Readiness, and Recent Runs.
 * Source: https://theia-ide.org/docs/widgets/
 * Source: https://theia-ide.org/docs/widgets/#react-based-widget
 */

import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { MessageService } from '@theia/core/lib/common/message-service';
import { CommandService } from '@theia/core/lib/common/command';
import { ArcFrontendService } from './arc-frontend-service';
import { RuntimeInfo, WorkflowInfo, SchemaInfo, WorkspaceInfo, RunRecord, RuntimeCapabilityReport } from '../common/arc-protocol';

@injectable()
export class ArcMainWidget extends ReactWidget {
  static readonly ID = 'arc:main-widget';
  static readonly LABEL = 'ARC';

  @inject(MessageService)
  protected readonly messageService: MessageService;

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  @inject(CommandService)
  protected readonly commandService: CommandService;

  // State
  protected loading = false;
  protected error: string | null = null;
  protected workspaceInfo: WorkspaceInfo | null = null;
  protected runtimes: RuntimeInfo[] = [];
  protected workflows: WorkflowInfo[] = [];
  protected schemas: SchemaInfo[] = [];
  protected daemonStatus: { running: boolean; version: string } | null = null;
  protected recentRuns: RunRecord[] = [];
  protected capabilities: RuntimeCapabilityReport[] = [];
  protected expandedRuntime: string | null = null;

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
      const [statusResult, runtimesResult, capabilitiesResult, runsResult] = await Promise.all([
        this.arcService.getDaemonStatus(),
        this.arcService.listRuntimes(),
        this.arcService.listRuntimeCapabilities().catch(() => undefined),
        this.arcService.listRuns().catch(() => undefined),
      ]);

      this.daemonStatus = statusResult.data;
      this.runtimes = runtimesResult.data ?? [];
      this.capabilities = capabilitiesResult?.data?.runtimes ?? [];
      this.recentRuns = (runsResult?.data ?? []).slice(0, 5);

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
    if (this.loading && !this.daemonStatus) {
      return (
        <div style={styles.panel}>
          {this.renderHeader()}
          <div style={styles.loading}>
            <div style={styles.spinner}>⟳</div>
            <span>Loading ARC data...</span>
          </div>
        </div>
      );
    }

    return (
      <div className="arc-panel" style={styles.panel}>
        {this.renderHeader()}
        {this.error && this.renderError()}
        <div style={styles.content}>
          {this.renderQuickActions()}
          {this.renderRuntimeReadiness()}
          {this.renderRecentRuns()}
        </div>
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
            aria-label="Refresh ARC data"
          >
            ↻
          </button>
        </div>
        {this.daemonStatus && (
          <div style={{
            ...styles.daemonBadge,
            backgroundColor: this.daemonStatus.running ? 'var(--theia-charts-green)' : 'var(--theia-inputValidation-errorBackground)',
          }}>
            {this.daemonStatus.running ? '● daemon online' : '○ daemon offline'}
          </div>
        )}
      </div>
    );
  }

  protected renderError(): React.ReactNode {
    return (
      <div style={styles.error}>
        <div style={styles.errorIcon}>⚠</div>
        <div style={styles.errorText}>{this.error}</div>
        <button style={styles.retryBtn} onClick={() => this.loadAll()}>Retry</button>
      </div>
    );
  }

  // ─── Quick Actions ─────────────────────────────────────────────────────

  protected renderQuickActions(): React.ReactNode {
    return (
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Quick Actions</div>
        <div style={styles.quickActions}>
          <button
            style={styles.actionBtn}
            onClick={() => this.commandService.executeCommand('arc:open-chat')}
            title="Run an agent workflow"
            aria-label="Run Agent"
          >
            <span style={styles.actionIcon}>▶</span>
            <span>Run Agent</span>
          </button>
          <button
            style={styles.actionBtn}
            onClick={() => this.commandService.executeCommand('arc:open-arena')}
            title="Compare models side by side"
            aria-label="Compare Models"
          >
            <span style={styles.actionIcon}>⚔</span>
            <span>Compare Models</span>
          </button>
          <button
            style={styles.actionBtn}
            onClick={() => this.commandService.executeCommand('arc:open-run-timeline')}
            title="View run history and timeline"
            aria-label="Open Timeline"
          >
            <span style={styles.actionIcon}>📊</span>
            <span>Run Timeline</span>
          </button>
        </div>
      </div>
    );
  }

  // ─── Runtime Readiness ─────────────────────────────────────────────────

  protected renderRuntimeReadiness(): React.ReactNode {
    const allRuntimes = this.capabilities.length > 0 ? this.capabilities : this.runtimes.map(rt => ({
      runtime_id: rt.id as any,
      can_run: rt.confidence === 'high',
      availability: rt.confidence,
      reason: rt.evidence.join('; '),
      required_env: [],
      detected_artifacts: rt.evidence,
      doctor_actions: [],
      requires_paid_calls: false,
      requires_network: false,
      requires_secrets: false,
    }));

    return (
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          Runtime Readiness
          <span style={styles.sectionCount}>{allRuntimes.length}</span>
        </div>
        {allRuntimes.length === 0 && (
          <div style={styles.emptyHint}>
            No runtimes detected. Open a workspace with an agent project.
          </div>
        )}
        {allRuntimes.map(rt => this.renderRuntimeItem(rt))}
      </div>
    );
  }

  protected renderRuntimeItem(rt: RuntimeCapabilityReport | ({ runtime_id: string; can_run: boolean; availability: string; reason: string; required_env: string[]; detected_artifacts: string[]; doctor_actions: any[]; requires_paid_calls: boolean; requires_network: boolean; requires_secrets: boolean })): React.ReactNode {
    const isReady = rt.can_run;
    const isExpanded = this.expandedRuntime === rt.runtime_id;
    const color = isReady ? 'var(--theia-charts-green)' : 'var(--theia-editorWarning-foreground)';
    const icon = isReady ? '✓' : '⚠';

    return (
      <div key={rt.runtime_id} style={styles.runtimeItem}>
        <div
          style={styles.runtimeHeader}
          onClick={() => {
            this.expandedRuntime = isExpanded ? null : rt.runtime_id;
            this.update();
          }}
          role="button"
          tabIndex={0}
          aria-label={`${rt.runtime_id} - ${isReady ? 'ready' : 'not ready'}`}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { this.expandedRuntime = isExpanded ? null : rt.runtime_id; this.update(); }}}
        >
          <span style={{ color, fontWeight: 600, fontSize: 12 }}>
            {icon} {rt.runtime_id}
          </span>
          <span style={{ fontSize: 10, color: 'var(--theia-descriptionForeground)' }}>
            {isReady ? 'ready' : rt.availability.replace(/_/g, ' ')}
          </span>
        </div>
        {isExpanded && (
          <div style={styles.runtimeDetails}>
            {rt.reason && (
              <div style={styles.runtimeDetailText}>{rt.reason}</div>
            )}
            {rt.required_env.length > 0 && (
              <div style={styles.runtimeDetailText}>
                Required: <code>{rt.required_env.join(', ')}</code>
              </div>
            )}
            {'doctor_actions' in rt && rt.doctor_actions.length > 0 && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                {rt.doctor_actions.map((action: any) => (
                  <button key={action.id} style={styles.doctorBtn} title={action.description}>
                    {action.label}
                  </button>
                ))}
              </div>
            )}
            {rt.requires_paid_calls && (
              <div style={{ fontSize: 10, color: 'var(--theia-editorWarning-foreground)', marginTop: 2 }}>
                Requires paid/provider calls
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // ─── Recent Runs ───────────────────────────────────────────────────────

  protected renderRecentRuns(): React.ReactNode {
    return (
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          Recent Runs
          {this.recentRuns.length > 0 && (
            <span style={styles.sectionCount}>{this.recentRuns.length}</span>
          )}
        </div>
        {this.recentRuns.length === 0 ? (
          <div style={styles.emptyHint}>
            No runs yet. Click "Run Agent" to start.
          </div>
        ) : (
          this.recentRuns.map(run => (
            <div
              key={run.id}
              style={styles.runItem}
              onClick={() => this.commandService.executeCommand('arc:open-run-timeline')}
              role="button"
              tabIndex={0}
              aria-label={`Run ${run.id.substring(0, 12)} - ${run.status}`}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { this.commandService.executeCommand('arc:open-run-timeline'); }}}
            >
              <div style={styles.runItemHeader}>
                <span style={{ fontSize: 11, fontWeight: 500 }}>
                  {this.statusIcon(run.status)} {run.id.substring(0, 12)}
                </span>
                <span style={{ fontSize: 10, fontWeight: 600, color: this.statusColor(run.status) }}>
                  {run.status}
                </span>
              </div>
              <div style={styles.runItemMeta}>
                {run.workflow_id} · {new Date(run.started_at).toLocaleTimeString()}
              </div>
            </div>
          ))
        )}
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

  protected statusColor(status: string): string {
    const colors: Record<string, string> = {
      pending: 'var(--theia-editorWarning-foreground)',
      running: 'var(--theia-textLink-foreground)',
      completed: 'var(--theia-charts-green)',
      failed: 'var(--theia-errorForeground)',
      cancelled: 'var(--theia-descriptionForeground)',
    };
    return colors[status] ?? 'inherit';
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
  headerIcon: { fontSize: '18px', color: 'var(--theia-textLink-foreground)' },
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
    color: 'var(--theia-badge-foreground)',
    marginTop: '4px',
    display: 'inline-block',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px 12px',
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
    padding: '16px',
    gap: '8px',
  },
  errorIcon: { fontSize: '24px', color: 'var(--theia-errorForeground)' },
  errorText: {
    color: 'var(--theia-errorForeground)',
    fontSize: '12px',
    textAlign: 'center',
    maxWidth: '300px',
  },
  retryBtn: {
    padding: '6px 16px',
    backgroundColor: 'var(--theia-button-background)',
    color: 'var(--theia-button-foreground)',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  // ─── Sections ──────────────────────────────────────────────────────────
  section: {
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--theia-descriptionForeground)',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  sectionCount: {
    fontSize: '10px',
    backgroundColor: 'var(--theia-badge-background)',
    color: 'var(--theia-badge-foreground)',
    borderRadius: '8px',
    padding: '0 5px',
  },
  // ─── Quick Actions ────────────────────────────────────────────────────
  quickActions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 12px',
    backgroundColor: 'var(--theia-editor-background)',
    border: '1px solid var(--theia-widget-border)',
    borderRadius: '6px',
    cursor: 'pointer',
    color: 'var(--theia-foreground)',
    fontSize: '13px',
    fontWeight: 500,
    textAlign: 'left' as any,
    transition: 'border-color 0.15s, background-color 0.15s',
  },
  actionIcon: { fontSize: '16px' },
  // ─── Runtime Readiness ────────────────────────────────────────────────
  runtimeItem: {
    border: '1px solid var(--theia-widget-border)',
    borderRadius: '4px',
    marginBottom: '4px',
    backgroundColor: 'var(--theia-editor-background)',
  },
  runtimeHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 10px',
    cursor: 'pointer',
  },
  runtimeDetails: {
    padding: '4px 10px 8px',
    borderTop: '1px solid var(--theia-widget-border)',
    fontSize: '11px',
  },
  runtimeDetailText: {
    color: 'var(--theia-descriptionForeground)',
    marginTop: '2px',
  },
  doctorBtn: {
    backgroundColor: 'var(--theia-button-background)',
    color: 'var(--theia-button-foreground)',
    border: 'none',
    borderRadius: '4px',
    padding: '2px 8px',
    cursor: 'pointer',
    fontSize: '10px',
  },
  // ─── Recent Runs ─────────────────────────────────────────────────────
  runItem: {
    padding: '8px 10px',
    borderBottom: '1px solid var(--theia-widget-border)',
    cursor: 'pointer',
  },
  runItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  runItemMeta: {
    fontSize: '10px',
    color: 'var(--theia-descriptionForeground)',
    marginTop: '2px',
  },
  emptyHint: {
    fontSize: '11px',
    color: 'var(--theia-descriptionForeground)',
    textAlign: 'center' as any,
    padding: '12px 8px',
  },
};
