/**
 * ARC Mobile Runtime Widget — read-only surface for arc mobile capabilities + doctor.
 * Simulator/mock only; no native-execution claims. R79 slice 110.6 (R-AUDIT17 Phase 148).
 */
import * as React from 'react';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, MobileStatus } from '../common/arc-protocol';

@injectable()
export class ArcMobileWidget extends ReactWidget {
    static readonly ID = 'arc:mobile-runtime';
    static readonly LABEL = 'ARC Mobile Runtime';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected state: { loading: boolean; status: MobileStatus | null; error?: string } = {
        loading: false, status: null,
    };

    @postConstruct()
    protected init(): void {
        this.id = ArcMobileWidget.ID;
        this.title.label = ArcMobileWidget.LABEL;
        this.title.closable = true;
        this.load();
    }

    protected async load(): Promise<void> {
        this.state = { loading: true, status: null };
        this.update();
        try {
            const status = await this.arcService.getMobileStatus();
            this.state = { loading: false, status };
        } catch (e) {
            this.state = { loading: false, status: null, error: String(e) };
        }
        this.update();
    }

    protected render(): React.ReactNode {
        const { loading, status, error } = this.state;
        if (loading) return <div className="arc-mobile-loading">Loading mobile runtime status…</div>;
        if (error || !status) return <div className="arc-mobile-error">⚠ {error ?? 'Unavailable'}</div>;
        return (
            <div className="arc-mobile-widget" role="main" aria-label="ARC Mobile Runtime Status">
                <div className="arc-mobile-doctor" style={{ marginBottom: 8 }}>
                    <strong>Doctor:</strong>{' '}
                    <span style={{ color: status.doctor.ok ? 'var(--arc-color-success, #73c991)' : 'var(--arc-color-error, #f14c4c)' }}>
                        {status.doctor.ok ? '✓' : '✗'} {status.doctor.message}
                    </span>
                    <span style={{ marginLeft: 8, opacity: 0.6, fontSize: 'var(--arc-font-size-sm, 11px)' }}>
                        [simulator/mock only]
                    </span>
                </div>
                <div className="arc-mobile-caps">
                    <strong>Capabilities ({status.capabilities.length})</strong>
                    {status.capabilities.length === 0
                        ? <div style={{ opacity: 0.6, marginTop: 4 }}>No capabilities found. Run <code>arc mobile capabilities</code> in a workspace with arc-mobile-capabilities.json.</div>
                        : (
                            <table role="list" aria-label="Mobile capabilities" style={{ width: '100%', borderCollapse: 'collapse', marginTop: 4 }}>
                                <thead>
                                    <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--arc-color-border, #454545)' }}>
                                        <th>ID</th><th>Name</th><th>Category</th><th>Platforms</th><th>Approval</th><th>Simulator</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {status.capabilities.map(c => (
                                        <tr key={c.id} role="listitem">
                                            <td><code>{c.id}</code></td>
                                            <td>{c.name}</td>
                                            <td>{c.category}</td>
                                            <td>{c.platforms.join(', ')}</td>
                                            <td>{c.approval_mode}</td>
                                            <td>{c.simulator_supported ? '✓' : '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )
                    }
                </div>
                <div style={{ marginTop: 8, opacity: 0.5, fontSize: 'var(--arc-font-size-sm, 11px)' }}>
                    Read-only view. Use <code>arc mobile</code> CLI for validate/simulate/trace.
                </div>
            </div>
        );
    }
}
