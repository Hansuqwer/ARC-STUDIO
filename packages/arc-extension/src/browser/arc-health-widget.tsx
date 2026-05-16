import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService } from '../common/arc-protocol';

interface HealthState {
    loading: boolean;
    backendAvailable: boolean;
    backendMessage?: string;
    runtimeCount: number;
    readyRuntimeCount: number;
    checkedAt?: string;
    error?: string;
}

@injectable()
export class ArcHealthWidget extends ReactWidget {
    static readonly ID = 'arc:health-monitor';
    static readonly LABEL = 'ARC Health Monitor';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected readonly pollMs = 5000;
    protected pollTimer: ReturnType<typeof setInterval> | undefined;
    protected state: HealthState = {
        loading: true,
        backendAvailable: false,
        runtimeCount: 0,
        readyRuntimeCount: 0,
    };

    @postConstruct()
    protected init(): void {
        this.id = ArcHealthWidget.ID;
        this.title.label = ArcHealthWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'ARC backend health';
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
            const [config, capabilities] = await Promise.all([
                this.arcService.getConfigStatus(),
                this.arcService.listRuntimeCapabilities().catch(() => undefined),
            ]);
            const runtimes = capabilities?.runtimes ?? [];
            this.state = {
                loading: false,
                backendAvailable: config.backendAvailable,
                backendMessage: config.backendMessage,
                runtimeCount: runtimes.length,
                readyRuntimeCount: runtimes.filter(runtime => runtime.can_run).length,
                checkedAt: new Date().toISOString(),
                error: config.backendAvailable ? undefined : config.backendMessage || 'ARC backend unavailable',
            };
        } catch (error) {
            this.state = {
                ...this.state,
                loading: false,
                backendAvailable: false,
                checkedAt: new Date().toISOString(),
                error: error instanceof Error ? error.message : String(error),
            };
        }
        this.update();
    }

    protected render(): React.ReactNode {
        const status = this.state.backendAvailable ? 'reachable' : 'degraded';
        return (
            <div style={styles.container} data-testid="arc-health-monitor">
                <h2 style={styles.title}>ARC Health Monitor</h2>
                <div style={styles.card}>
                    <div style={styles.row}>
                        <span>Backend</span>
                        <strong style={{ color: this.state.backendAvailable ? 'var(--theia-charts-green)' : 'var(--theia-editorWarning-foreground)' }}>{status}</strong>
                    </div>
                    <div style={styles.row}>
                        <span>Ready Runtimes</span>
                        <strong>{this.state.readyRuntimeCount} / {this.state.runtimeCount}</strong>
                    </div>
                    <div style={styles.row}>
                        <span>Poll Interval</span>
                        <strong>{this.pollMs / 1000}s</strong>
                    </div>
                    {this.state.backendMessage && <div style={styles.muted}>Backend: {this.state.backendMessage}</div>}
                    {this.state.checkedAt && <div style={styles.muted}>Last checked: {this.state.checkedAt}</div>}
                    {this.state.error && <pre style={styles.error}>{this.state.error}</pre>}
                </div>
                <button style={styles.button} onClick={() => this.refreshHealth()} aria-label="Refresh health status">Refresh Health</button>
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
        color: 'var(--theia-editorWarning-foreground)',
        whiteSpace: 'pre-wrap',
    },
    button: {
        marginTop: '12px',
        padding: '6px 10px',
        cursor: 'pointer',
    },
};
