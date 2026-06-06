import * as React from 'react';
import { BaseWidget, Message } from '@theia/core/lib/browser';
import { injectable } from '@theia/core/shared/inversify';

interface AgentEntry {
    name: string;
    skills: string[];
}

interface ContextDrawerState {
    agents: AgentEntry[];
    loading: boolean;
    error: string | null;
}

@injectable()
export class ArcContextDrawer extends BaseWidget {
    static readonly ID = 'arc-context-drawer';
    static readonly LABEL = 'ARC Context';

    private state: ContextDrawerState = { agents: [], loading: false, error: null };

    constructor() {
        super();
        this.id = ArcContextDrawer.ID;
        this.title.label = ArcContextDrawer.LABEL;
        this.title.caption = ArcContextDrawer.LABEL;
        this.title.closable = true;
        this.addClass('arc-context-drawer');
    }

    protected onAfterAttach(msg: Message): void {
        super.onAfterAttach(msg);
        this.loadAgents();
    }

    private async loadAgents(): Promise<void> {
        this.state = { ...this.state, loading: true, error: null };
        this.update();
        try {
            // Stub: In production, this calls arc agents-md discover --json via ArcService.
            // Returning empty list until CLI proxy is wired.
            this.state = { agents: [], loading: false, error: null };
        } catch (e) {
            this.state = { agents: [], loading: false, error: String(e) };
        }
        this.update();
    }

    render(): React.ReactNode {
        const { agents, loading, error } = this.state;
        if (loading) {
            return <div className="arc-context-drawer__loading">Loading…</div>;
        }
        if (error) {
            return <div className="arc-context-drawer__error" role="alert">{error}</div>;
        }
        if (agents.length === 0) {
            return (
                <div className="arc-context-drawer__empty" aria-label="ARC Context — no agents found">
                    No AGENTS.md discovered in workspace.
                </div>
            );
        }
        return (
            <div className="arc-context-drawer" role="list" aria-label="ARC Context — agent list">
                {agents.map(agent => (
                    <div key={agent.name} className="arc-context-drawer__agent" role="listitem">
                        <strong>{agent.name}</strong>
                        {agent.skills.length > 0 && (
                            <ul aria-label={`Skills for ${agent.name}`}>
                                {agent.skills.map(skill => <li key={skill}>{skill}</li>)}
                            </ul>
                        )}
                    </div>
                ))}
            </div>
        );
    }
}
