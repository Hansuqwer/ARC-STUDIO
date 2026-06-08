import * as React from 'react';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ArcService, AgentsMdEntry } from '../common/arc-protocol';

interface ContextDrawerState {
    entries: AgentsMdEntry[];
    loading: boolean;
    error: string | null;
}

@injectable()
export class ArcContextDrawer extends ReactWidget {
    static readonly ID = 'arc-context-drawer';
    static readonly LABEL = 'ARC Context';

    @inject(ArcService) private readonly arcService!: ArcService;

    private state: ContextDrawerState = { entries: [], loading: true, error: null };

    @postConstruct()
    protected init(): void {
        this.id = ArcContextDrawer.ID;
        this.title.label = ArcContextDrawer.LABEL;
        this.title.caption = ArcContextDrawer.LABEL;
        this.title.closable = true;
        this.addClass('arc-context-drawer');
        this.loadEntries();
    }

    private async loadEntries(): Promise<void> {
        this.state = { ...this.state, loading: true, error: null };
        this.update();
        try {
            // R-AUDIT16: real producer — `arc agents-md discover --json` via the backend bridge.
            const entries = await this.arcService.discoverAgentsMd();
            this.state = { entries, loading: false, error: null };
        } catch (e) {
            this.state = { entries: [], loading: false, error: String(e) };
        }
        this.update();
    }

    protected render(): React.ReactNode {
        const { entries, loading, error } = this.state;
        if (loading) {
            return <div className="arc-context-drawer__loading">Loading…</div>;
        }
        if (error) {
            return <div className="arc-context-drawer__error" role="alert">{error}</div>;
        }
        if (entries.length === 0) {
            return (
                <div className="arc-context-drawer__empty" aria-label="ARC Context — no AGENTS.md found">
                    No AGENTS.md discovered in workspace.
                </div>
            );
        }
        return (
            <div className="arc-context-drawer" role="list" aria-label="ARC Context — discovered AGENTS.md files">
                {entries.map(entry => (
                    <div key={entry.path} className="arc-context-drawer__agent" role="listitem">
                        <strong>{entry.path}</strong>
                        <ul aria-label={`Metadata for ${entry.path}`}>
                            {entry.isOverride && <li>override</li>}
                            {entry.overCap && <li>over size cap</li>}
                            {entry.likelyLlmGenerated && <li>likely LLM-generated</li>}
                            <li>{entry.sizeBytes} bytes</li>
                        </ul>
                    </div>
                ))}
            </div>
        );
    }
}
