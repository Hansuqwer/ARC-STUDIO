import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcFrontendService } from 'arc-core/lib/browser/arc-frontend-service';

interface HealthState {
  loading: boolean;
  running: boolean;
  version: string;
  activeRuns: number;
  checkedAt?: string;
  error?: string;
}

@injectable()
export class ArcHealthWidget extends ReactWidget {
  static readonly ID = 'arc:health-monitor';
  static readonly LABEL = 'ARC Health Monitor';

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  protected readonly pollMs = 5000;
  protected pollTimer: ReturnType<typeof setInterval> | undefined;
  protected state: HealthState = {
    loading: true,
    running: false,
    version: 'unknown',
    activeRuns: 0,
  };

  @postConstruct()
  protected init(): void {
    this.id = ArcHealthWidget.ID;
    this.title.label = ArcHealthWidget.LABEL;
    this.title.closable = true;
    this.title.caption = 'ARC local daemon health';
    this.refreshHealth();
    this.pollTimer = setInterval(() => this.refreshHealth(), this.pollMs);
  }

  dispose(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }
    super.dispose();
  }

  protected async refreshHealth(): Promise<void> {
    try {
      const [status, runs] = await Promise.all([
        this.arcService.getDaemonStatus(),
        this.arcService.listRuns().catch(() => undefined),
      ]);
      const activeRuns = runs?.data?.filter(run => run.status === 'running' || run.status === 'pending').length ?? 0;
      this.state = {
        loading: false,
        running: Boolean(status.data?.running),
        version: status.data?.version ?? 'unknown',
        activeRuns,
        checkedAt: new Date().toISOString(),
        error: status.ok ? undefined : status.error?.message ?? 'Daemon health unavailable',
      };
    } catch (error) {
      this.state = {
        ...this.state,
        loading: false,
        running: false,
        checkedAt: new Date().toISOString(),
        error: String(error),
      };
    }
    this.update();
  }

  protected render(): React.ReactNode {
    const status = this.state.running ? 'reachable' : 'degraded';
    return (
      <div style={styles.container} data-testid="arc-health-monitor">
        <h2 style={styles.title}>ARC Health Monitor</h2>
        <div style={styles.card}>
          <div style={styles.row}>
            <span>Daemon</span>
            <strong style={{ color: this.state.running ? '#4caf50' : '#ffb74d' }}>{status}</strong>
          </div>
          <div style={styles.row}>
            <span>Endpoint</span>
            <code>127.0.0.1:7777 /health</code>
          </div>
          <div style={styles.row}>
            <span>Version</span>
            <strong>{this.state.loading ? 'checking...' : this.state.version}</strong>
          </div>
          <div style={styles.row}>
            <span>Active Runs</span>
            <strong>{this.state.activeRuns}</strong>
          </div>
          <div style={styles.row}>
            <span>Poll Interval</span>
            <strong>{this.pollMs / 1000}s</strong>
          </div>
          {this.state.checkedAt && <div style={styles.muted}>Last checked: {this.state.checkedAt}</div>}
          {this.state.error && <pre style={styles.error}>{this.state.error}</pre>}
        </div>
        <button style={styles.button} onClick={() => this.refreshHealth()}>Refresh Health</button>
      </div>
    );
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '20px',
    fontFamily: 'var(--theia-ui-font-family)',
    color: 'var(--theia-foreground)',
  },
  title: {
    marginTop: 0,
    fontSize: '18px',
  },
  card: {
    maxWidth: '560px',
    padding: '14px',
    border: '1px solid var(--theia-widget-border)',
    borderRadius: '6px',
    backgroundColor: 'var(--theia-editor-background)',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '12px',
    padding: '6px 0',
    borderBottom: '1px solid var(--theia-widget-border)',
  },
  muted: {
    marginTop: '10px',
    fontSize: '12px',
    color: 'var(--theia-descriptionForeground)',
  },
  error: {
    marginTop: '10px',
    color: '#ffb74d',
    whiteSpace: 'pre-wrap',
  },
  button: {
    marginTop: '12px',
    padding: '6px 10px',
    cursor: 'pointer',
  },
};
