import * as React from 'react';
import { injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';

/**
 * ARC IR Simulation Panel.
 *
 * Reads a locally-uploaded IR JSON file, POSTs it to the ARC daemon's
 * /v1/runs/inspect endpoint (or displays offline when unavailable),
 * and renders the SimulationReport inline.
 *
 * Local-first: no data is sent outside 127.0.0.1.
 */

type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

interface SimSummary {
    total_nodes: number;
    reachable_nodes: number;
    opaque_nodes: number;
    side_effect_count: number;
    gate_count: number;
    hitl_gate_count: number;
    paid_call_count: number;
    warning_count: number;
}

interface SimReport {
    graph_id: string;
    graph_hash?: string;
    determinism_hash?: string;
    format?: string;
    summary: SimSummary;
    policy?: { can_run: boolean; risk_level: RiskLevel; issue_count: number };
    warnings?: Array<{ code: string; message: string }>;
}

interface WidgetState {
    loading: boolean;
    report: SimReport | null;
    error: string | null;
    fileName: string | null;
}

const RISK_COLOR: Record<RiskLevel, string> = {
    low: '#27ae60',
    medium: '#f39c12',
    high: '#e67e22',
    critical: '#e74c3c',
};

@injectable()
export class ArcSimulationWidget extends ReactWidget {
    static readonly ID = 'arc:simulation-panel';
    static readonly LABEL = 'ARC Simulation Panel';

    protected state: WidgetState = { loading: false, report: null, error: null, fileName: null };

    @postConstruct()
    protected init(): void {
        this.id = ArcSimulationWidget.ID;
        this.title.label = ArcSimulationWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'SwarmGraph IR Simulation — dry-run preview';
        this.title.iconClass = 'codicon codicon-beaker';
    }

    /** Call the ARC daemon's inspect endpoint with the loaded IR JSON. */
    protected async simulateIr(irJson: unknown): Promise<SimReport> {
        const base = 'http://127.0.0.1:7777';
        const resp = await fetch(`${base}/v1/ir/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(irJson),
            signal: AbortSignal.timeout(10_000),
        });
        if (!resp.ok) {
            throw new Error(`ARC daemon returned ${resp.status}`);
        }
        const envelope = await resp.json();
        if (!envelope.ok) {
            throw new Error(envelope.error?.message ?? 'Simulation failed');
        }
        return envelope.data as SimReport;
    }

    protected handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
        const file = e.target.files?.[0];
        if (!file) return;
        this.state = { loading: true, report: null, error: null, fileName: file.name };
        this.update();
        try {
            const text = await file.text();
            const irJson = JSON.parse(text);
            const report = await this.simulateIr(irJson);
            this.state = { loading: false, report, error: null, fileName: file.name };
        } catch (err) {
            this.state = {
                loading: false,
                report: null,
                fileName: file.name,
                error: err instanceof Error ? err.message : String(err),
            };
        }
        this.update();
    };

    protected render(): React.ReactNode {
        const { loading, report, error, fileName } = this.state;
        return (
            <div style={{ padding: '16px', fontFamily: 'var(--theia-ui-font-family)', fontSize: '13px' }}>
                <h3 style={{ marginTop: 0 }}>IR Simulation Panel</h3>
                <p style={{ color: 'var(--theia-ui-font-color2)', marginBottom: '12px' }}>
                    Upload a SwarmGraph IR JSON file to preview what the workflow would do — no execution.
                </p>

                <label style={{ display: 'block', marginBottom: '12px' }}>
                    <input
                        type="file"
                        accept=".json"
                        onChange={this.handleFileChange}
                        style={{ display: 'none' }}
                        id="arc-sim-file-input"
                    />
                    <button
                        style={btnStyle}
                        onClick={() => document.getElementById('arc-sim-file-input')?.click()}
                    >
                        📂 Load IR JSON
                    </button>
                    {fileName && <span style={{ marginLeft: '8px', color: 'var(--theia-ui-font-color2)' }}>{fileName}</span>}
                </label>

                {loading && <p>⏳ Simulating…</p>}

                {error && (
                    <div style={errorStyle}>
                        ⚠️ {error}
                        {error.includes('127.0.0.1') && (
                            <div style={{ marginTop: '6px', fontSize: '12px' }}>
                                Start the ARC daemon: <code>arc serve</code>
                            </div>
                        )}
                    </div>
                )}

                {report && <SimulationReportView report={report} />}
            </div>
        );
    }
}

const btnStyle: React.CSSProperties = {
    padding: '6px 12px',
    cursor: 'pointer',
    borderRadius: '4px',
    border: '1px solid var(--theia-input-border)',
    background: 'var(--theia-button-secondaryBackground)',
    color: 'var(--theia-button-secondaryForeground)',
};

const errorStyle: React.CSSProperties = {
    padding: '10px',
    background: 'rgba(231, 76, 60, 0.12)',
    border: '1px solid #e74c3c',
    borderRadius: '4px',
    marginBottom: '12px',
};

function SimulationReportView({ report }: { report: SimReport }): React.ReactNode {
    const s = report.summary;
    const risk = report.policy?.risk_level ?? 'low';
    const canRun = report.policy?.can_run ?? true;

    return (
        <div>
            <h4 style={{ marginBottom: '8px' }}>
                {canRun ? '✅' : '🚫'} {report.graph_id}
                <span style={{
                    marginLeft: '10px', fontSize: '11px', fontWeight: 'normal',
                    color: RISK_COLOR[risk] ?? '#888',
                }}>
                    risk: {risk}
                </span>
            </h4>

            {report.determinism_hash && (
                <div style={{ fontSize: '11px', color: 'var(--theia-ui-font-color2)', marginBottom: '10px' }}>
                    hash: <code>{report.determinism_hash}</code>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
                {([
                    ['Nodes', `${s.reachable_nodes}/${s.total_nodes}`],
                    ['Side effects', s.side_effect_count],
                    ['Gates', s.gate_count],
                    ['HITL gates', s.hitl_gate_count],
                    ['Paid calls', s.paid_call_count],
                    ['Warnings', s.warning_count],
                ] as [string, string | number][]).map(([label, val]) => (
                    <div key={label} style={statCard}>
                        <div style={{ fontSize: '11px', color: 'var(--theia-ui-font-color2)' }}>{label}</div>
                        <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{val}</div>
                    </div>
                ))}
            </div>

            {report.warnings && report.warnings.length > 0 && (
                <details style={{ marginTop: '8px' }}>
                    <summary style={{ cursor: 'pointer', color: '#f39c12' }}>
                        ⚠️ {report.warnings.length} warning{report.warnings.length !== 1 ? 's' : ''}
                    </summary>
                    <ul style={{ marginTop: '6px', paddingLeft: '20px' }}>
                        {report.warnings.map((w, i) => (
                            <li key={i} style={{ marginBottom: '4px' }}>
                                <code style={{ fontSize: '11px' }}>{w.code}</code>: {w.message}
                            </li>
                        ))}
                    </ul>
                </details>
            )}
        </div>
    );
}

const statCard: React.CSSProperties = {
    padding: '8px',
    borderRadius: '4px',
    background: 'var(--theia-input-background)',
    border: '1px solid var(--theia-input-border)',
    textAlign: 'center' as const,
};
