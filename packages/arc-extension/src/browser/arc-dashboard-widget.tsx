import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService } from '../common/arc-protocol';

interface WorkspaceInfo {
    path: string;
    name: string;
    status: 'active' | 'idle' | 'error';
    recentRuns: number;
    totalCost: number;
    health: 'ok' | 'degraded' | 'unknown';
}

interface DashboardState {
    loading: boolean;
    workspaces: WorkspaceInfo[];
    activeWorkspace?: string;
    error?: string;
    lastUpdated?: string;
}

@injectable()
export class ArcDashboardWidget extends ReactWidget {
    static readonly ID = 'arc:dashboard';
    static readonly LABEL = 'ARC Dashboard';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected state: DashboardState = {
        loading: true,
        workspaces: [],
    };

    @postConstruct()
    protected init(): void {
        this.id = ArcDashboardWidget.ID;
        this.title.label = ArcDashboardWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'Multi-workspace control center';
        this.refreshDashboard();
    }

    protected async refreshDashboard(): Promise<void> {
        try {
            const config = await this.arcService.getConfigStatus();
            const workspacePath = config.workspace?.workspacePath || '.';
            const workspaces: WorkspaceInfo[] = [
                {
                    path: workspacePath,
                    name: workspacePath ? workspacePath.split('/').pop() || 'workspace' : 'workspace',
                    status: config.backendAvailable ? 'active' : 'idle',
                    recentRuns: 0,
                    totalCost: 0,
                    health: config.backendAvailable ? 'ok' : 'degraded',
                },
            ];

            this.state = {
                loading: false,
                workspaces,
                activeWorkspace: workspaces[0]?.path,
                lastUpdated: new Date().toISOString(),
            };
        } catch (error) {
            this.state = {
                loading: false,
                workspaces: [],
                error: error instanceof Error ? error.message : String(error),
            };
        }
        this.update();
    }

    protected switchWorkspace(path: string): void {
        this.state = {
            ...this.state,
            activeWorkspace: path,
        };
        this.update();
    }

    protected render(): React.ReactNode {
        if (this.state.loading) {
            return (
                <div style={styles.container} data-testid="arc-dashboard-loading" role="status" aria-label="Loading workspaces">
                    <h2 style={styles.title}>ARC Dashboard</h2>
                    <div style={styles.loading}>Loading workspaces...</div>
                </div>
            );
        }

        if (this.state.error) {
            return (
                <div style={styles.container} data-testid="arc-dashboard-error" role="alert" aria-label="Dashboard error">
                    <h2 style={styles.title}>ARC Dashboard</h2>
                    <div style={styles.error}>Error: {this.state.error}</div>
                    <button style={styles.button} onClick={() => this.refreshDashboard()} aria-label="Retry loading dashboard">Retry</button>
                </div>
            );
        }

        if (this.state.workspaces.length === 0) {
            return (
                <div style={styles.container} data-testid="arc-dashboard-empty" role="status" aria-label="No workspaces found">
                    <h2 style={styles.title}>ARC Dashboard</h2>
                    <div style={styles.empty}>No workspaces found. Open a workspace to get started.</div>
                </div>
            );
        }

        return (
            <div style={styles.container} data-testid="arc-dashboard">
                <h2 style={styles.title}>ARC Dashboard</h2>
                <div style={styles.summary} role="group" aria-label="Workspace summary">
                    <div style={styles.summaryCard} aria-label={`Workspaces: ${this.state.workspaces.length}`}>
                        <div style={styles.summaryLabel}>Workspaces</div>
                        <div style={styles.summaryValue}>{this.state.workspaces.length}</div>
                    </div>
                    <div style={styles.summaryCard} aria-label={`Active workspaces: ${this.state.workspaces.filter(w => w.status === 'active').length}`}>
                        <div style={styles.summaryLabel}>Active</div>
                        <div style={styles.summaryValue}>
                            {this.state.workspaces.filter(w => w.status === 'active').length}
                        </div>
                    </div>
                    <div style={styles.summaryCard} aria-label={`Total cost in dollars`}>
                        <div style={styles.summaryLabel}>Total Cost</div>
                        <div style={styles.summaryValue}>
                            ${this.state.workspaces.reduce((sum, w) => sum + w.totalCost, 0).toFixed(2)}
                        </div>
                    </div>
                </div>
                <div style={styles.workspaceList}>
                    {this.state.workspaces.map(workspace => (
                        <div
                            key={workspace.path}
                            style={{
                                ...styles.workspaceCard,
                                borderColor: workspace.path === this.state.activeWorkspace
                                    ? 'var(--theia-focusBorder)'
                                    : 'var(--theia-widget-border)',
                            }}
                            onClick={() => this.switchWorkspace(workspace.path)}
                            role="button"
                            tabIndex={0}
                            aria-label={`Switch to workspace ${workspace.name}`}
                        >
                            <div style={styles.workspaceHeader}>
                                <strong>{workspace.name}</strong>
                                <span style={{
                                    ...styles.statusBadge,
                                    backgroundColor: workspace.status === 'active'
                                        ? 'var(--theia-charts-green)'
                                        : workspace.status === 'error'
                                            ? 'var(--theia-editorWarning-foreground)'
                                            : 'var(--theia-descriptionForeground)',
                                }}>
                                    {workspace.status}
                                </span>
                            </div>
                            <div style={styles.workspacePath}>{workspace.path}</div>
                            <div style={styles.workspaceStats}>
                                <span>Runs: {workspace.recentRuns}</span>
                                <span>Cost: ${workspace.totalCost.toFixed(2)}</span>
                                <span>Health: {workspace.health}</span>
                            </div>
                        </div>
                    ))}
                </div>
                {this.state.lastUpdated && (
                    <div style={styles.muted}>Last updated: {this.state.lastUpdated}</div>
                )}
                <button style={styles.button} onClick={() => this.refreshDashboard()} aria-label="Refresh dashboard">Refresh</button>
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
    loading: {
        padding: '20px',
        textAlign: 'center',
        color: 'var(--theia-descriptionForeground)',
    },
    error: {
        padding: '20px',
        color: 'var(--theia-editorWarning-foreground)',
    },
    empty: {
        padding: '20px',
        textAlign: 'center',
        color: 'var(--theia-descriptionForeground)',
    },
    summary: {
        display: 'flex',
        gap: '16px',
        marginBottom: '20px',
    },
    summaryCard: {
        flex: 1,
        padding: '16px',
        border: '1px solid var(--theia-widget-border)',
        borderRadius: '6px',
        backgroundColor: 'var(--theia-editor-background)',
        textAlign: 'center',
    },
    summaryLabel: {
        fontSize: '12px',
        color: 'var(--theia-descriptionForeground)',
        marginBottom: '8px',
    },
    summaryValue: {
        fontSize: '24px',
        fontWeight: 'bold',
    },
    workspaceList: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
    },
    workspaceCard: {
        padding: '14px',
        border: '2px solid var(--theia-widget-border)',
        borderRadius: '6px',
        backgroundColor: 'var(--theia-editor-background)',
        cursor: 'pointer',
    },
    workspaceHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '8px',
    },
    statusBadge: {
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '11px',
        color: 'white',
        textTransform: 'uppercase',
    },
    workspacePath: {
        fontSize: '12px',
        color: 'var(--theia-descriptionForeground)',
        marginBottom: '8px',
    },
    workspaceStats: {
        display: 'flex',
        gap: '16px',
        fontSize: '13px',
    },
    muted: {
        marginTop: '16px',
        fontSize: '12px',
        color: 'var(--theia-descriptionForeground)',
    },
    button: {
        marginTop: '12px',
        padding: '6px 10px',
        cursor: 'pointer',
    },
};
