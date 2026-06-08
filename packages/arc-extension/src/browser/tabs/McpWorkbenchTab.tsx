/**
 * MCP Workbench Tab
 *
 * Standalone tab for MCP workbench status: server creatability, trust level,
 * registered tools and resources, and diagnostic info.
 * Previously rendered as a sub-panel in CommandCentreTab.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, McpDecisionEntry, McpWorkbenchStatus } from '../../common/arc-protocol';
import { useAsyncState } from '../hooks/useAsyncState';
import { riskBadgeVariant } from './mcp-risk';

const DECISION_LIMIT = 20;

export interface McpWorkbenchTabProps {
    arcService: ArcService;
}

export const McpWorkbenchTab: React.FC<McpWorkbenchTabProps> = ({ arcService }) => {
    const { data: status, loading, error, reload: load } = useAsyncState<McpWorkbenchStatus>(
        () => arcService.getMcpWorkbenchStatus(),
        [arcService],
        { errorMessage: 'Failed to load MCP workbench status' },
    );

    const [decisions, setDecisions] = React.useState<McpDecisionEntry[]>([]);
    const [decisionsLoading, setDecisionsLoading] = React.useState(false);

    const loadDecisions = React.useCallback(async () => {
        setDecisionsLoading(true);
        try {
            const result = await arcService.getMcpDecisions({ limit: DECISION_LIMIT });
            setDecisions(result.decisions);
        } finally {
            setDecisionsLoading(false);
        }
    }, [arcService]);

    React.useEffect(() => {
        // status loads via useAsyncState (immediate); only decisions need an explicit kick here.
        loadDecisions();
    }, [loadDecisions]);

    if (loading) {
        return (
            <div className='arc-mcp-workbench' role='region' aria-label='MCP Workbench'>
                <h3>MCP Workbench</h3>
                <p className='arc-mcp-workbench__loading'>Loading MCP workbench status...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className='arc-mcp-workbench' role='region' aria-label='MCP Workbench'>
                <h3>MCP Workbench</h3>
                <div className='arc-mcp-workbench__error' role='alert'>Error: {error}</div>
                <button className='arc-mcp-workbench__refresh' onClick={load}>Retry</button>
            </div>
        );
    }

    if (!status) {
        return (
            <div className='arc-mcp-workbench' role='region' aria-label='MCP Workbench'>
                <h3>MCP Workbench</h3>
                <p className='arc-mcp-workbench__empty'>MCP workbench status unavailable.</p>
                <button className='arc-mcp-workbench__refresh' onClick={load}>Refresh</button>
            </div>
        );
    }

    const serverStatus = status.serverCreatable ? 'Creatable' : 'Blocked';

    return (
        <div className='arc-mcp-workbench' role='region' aria-label='MCP Workbench'>
            <div className='arc-mcp-workbench__header'>
                <h3>MCP Workbench</h3>
                <button className='arc-mcp-workbench__refresh' onClick={load}>Refresh</button>
            </div>

            <section className='arc-mcp-workbench__section'>
                <h4>Server Status</h4>
                <div className='arc-mcp-workbench__field'>
                    <span className='arc-mcp-workbench__label'>Status:</span>
                    <span className={`arc-mcp-workbench__badge ${status.serverCreatable ? 'arc-mcp-workbench__badge--ok' : 'arc-mcp-workbench__badge--blocked'}`}>
                        {serverStatus}
                    </span>
                </div>
                {status.serverBlocker && (
                    <div className='arc-mcp-workbench__field'>
                        <span className='arc-mcp-workbench__label'>Blocker:</span>
                        <span>{status.serverBlocker}</span>
                    </div>
                )}
            </section>

            <section className='arc-mcp-workbench__section'>
                <h4>Trust Level</h4>
                <div className='arc-mcp-workbench__field'>
                    <span className='arc-mcp-workbench__label'>Level:</span>
                    <span>{status.trust.level}</span>
                </div>
                {status.trust.reason && (
                    <div className='arc-mcp-workbench__field'>
                        <span className='arc-mcp-workbench__label'>Reason:</span>
                        <span>{status.trust.reason}</span>
                    </div>
                )}
                {status.trust.warning && (
                    <div className='arc-mcp-workbench__field'>
                        <span className='arc-mcp-workbench__label'>Warning:</span>
                        <span className='arc-mcp-workbench__warning'>{status.trust.warning}</span>
                    </div>
                )}
            </section>

            <section className='arc-mcp-workbench__section'>
                <h4>Tools ({status.tools.length})</h4>
                {status.tools.length === 0 && (
                    <p className='arc-mcp-workbench__empty'>No tools registered.</p>
                )}
                {status.tools.length > 0 && (
                    <ul className='arc-mcp-workbench__list'>
                        {status.tools.map((tool, i) => (
                            <li key={i} className='arc-mcp-workbench__list-item'>{tool}</li>
                        ))}
                    </ul>
                )}
            </section>

            <section className='arc-mcp-workbench__section'>
                <h4>Resources ({status.resources.length})</h4>
                {status.resources.length === 0 && (
                    <p className='arc-mcp-workbench__empty'>No resources registered.</p>
                )}
                {status.resources.length > 0 && (
                    <ul className='arc-mcp-workbench__list'>
                        {status.resources.map((resource, i) => (
                            <li key={i} className='arc-mcp-workbench__list-item'>{resource}</li>
                        ))}
                    </ul>
                )}
            </section>

            <section className='arc-mcp-workbench__section'>
                <h4>Diagnostic Info</h4>
                <pre className='arc-mcp-workbench__diagnostic'>{status.diagnostic}</pre>
            </section>

            <section className='arc-mcp-workbench__section'>
                <div className='arc-mcp-workbench__header'>
                    <h4>Recent MCP Decisions ({decisions.length})</h4>
                    <button className='arc-mcp-workbench__refresh' onClick={loadDecisions} disabled={decisionsLoading}>
                        {decisionsLoading ? '...' : 'Refresh'}
                    </button>
                </div>
                {decisions.length === 0 && !decisionsLoading && (
                    <p className='arc-mcp-workbench__empty'>No recent MCP outbound call decisions.</p>
                )}
                {decisions.length > 0 && (
                    <ul className='arc-mcp-workbench__list'>
                        {decisions.map((d, i) => (
                            <li key={i} className={`arc-mcp-workbench__decision arc-mcp-workbench__decision--${d.decision}`}>
                                <span className='arc-mcp-workbench__decision-badge'>{d.decision.toUpperCase()}</span>
                                <span className='arc-mcp-workbench__decision-tool'>{d.serverId}/{d.toolName}</span>
                                <span
                                    className={`arc-mcp-workbench__badge arc-mcp-workbench__badge--${riskBadgeVariant(d.riskScore)}`}
                                    aria-label={`risk level ${d.riskScore}`}
                                >
                                    risk:{d.riskScore}
                                </span>
                                <span className='arc-mcp-workbench__decision-reason'>{d.reason}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </div>
    );
};
