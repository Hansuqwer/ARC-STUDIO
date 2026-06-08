import * as React from 'react';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { ArcService, WorkspaceSearchHit } from '../common/arc-protocol';

type SearchStatus = 'idle' | 'loading' | 'done' | 'error';

interface SearchState {
    query: string;
    hits: WorkspaceSearchHit[];
    status: SearchStatus;
    error: string | null;
}

/** R-AUDIT18: IDE workspace-search panel — wired to the path-confined `arc workspace search`. */
@injectable()
export class ArcWorkspaceSearchWidget extends ReactWidget {
    static readonly ID = 'arc:workspace-search';
    static readonly LABEL = 'ARC Workspace Search';

    @inject(ArcService) private readonly arcService!: ArcService;

    private state: SearchState = { query: '', hits: [], status: 'idle', error: null };

    @postConstruct()
    protected init(): void {
        this.id = ArcWorkspaceSearchWidget.ID;
        this.title.label = ArcWorkspaceSearchWidget.LABEL;
        this.title.caption = ArcWorkspaceSearchWidget.LABEL;
        this.title.closable = true;
        this.addClass('arc-workspace-search');
        this.update();
    }

    private async runSearch(): Promise<void> {
        const query = this.state.query.trim();
        if (!query) {
            this.state = { ...this.state, hits: [], status: 'idle', error: null };
            this.update();
            return;
        }
        this.state = { ...this.state, status: 'loading', error: null };
        this.update();
        try {
            const hits = await this.arcService.searchWorkspace(query);
            this.state = { ...this.state, hits, status: 'done', error: null };
        } catch (e) {
            this.state = { ...this.state, hits: [], status: 'error', error: String(e) };
        }
        this.update();
    }

    protected render(): React.ReactNode {
        const { query, hits, status, error } = this.state;
        return (
            <div className="arc-workspace-search" role="region" aria-label="ARC Workspace Search">
                <form
                    className="arc-workspace-search__form"
                    onSubmit={e => {
                        e.preventDefault();
                        this.runSearch();
                    }}
                >
                    <input
                        type="search"
                        aria-label="Workspace search query"
                        placeholder="Search workspace text…"
                        value={query}
                        onChange={e => {
                            this.state = { ...this.state, query: e.target.value };
                        }}
                    />
                    <button type="submit" aria-label="Run workspace search">Search</button>
                </form>
                {status === 'loading' && <div className="arc-workspace-search__loading">Searching…</div>}
                {status === 'error' && (
                    <div className="arc-workspace-search__error" role="alert">{error}</div>
                )}
                {status === 'done' && hits.length === 0 && (
                    <div className="arc-workspace-search__empty" aria-label="No matches found">
                        No matches found.
                    </div>
                )}
                {hits.length > 0 && (
                    <ul className="arc-workspace-search__results" role="list" aria-label="Search results">
                        {hits.map((hit, i) => (
                            <li key={`${hit.file}:${hit.line}:${i}`} role="listitem">
                                <code>{hit.file}:{hit.line}</code>
                                <span className="arc-workspace-search__match">{hit.match}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        );
    }
}
