/**
 * MCP Workbench Tab
 *
 * Standalone tab for MCP workbench status: server creatability, trust level,
 * registered tools and resources, and diagnostic info.
 * Previously rendered as a sub-panel in CommandCentreTab.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, McpDecisionEntry, McpWorkbenchStatus, McpToolInvokeResult } from '../../common/arc-protocol';
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

    // B2P-04b: in-IDE MCP tool invocation (loopback, risk-gated via the backend).
    const [invokeTool, setInvokeTool] = React.useState('');
    const [invokeArgs, setInvokeArgs] = React.useState('{}');
    const [invoking, setInvoking] = React.useState(false);
    const [invokeResult, setInvokeResult] = React.useState<McpToolInvokeResult | null>(null);
    const [invokeError, setInvokeError] = React.useState<string | null>(null);
    // Generation guard: a Cancel (or a superseding invoke) bumps the counter so a stale/cancelled
    // in-flight result is discarded. The backend call is additionally bounded by a 30s timeout.
    const invokeGen = React.useRef(0);

    const runInvoke = React.useCallback(async () => {
        const tool = invokeTool.trim();
        if (!tool) {
            return;
        }
        let parsedArgs: Record<string, unknown>;
        try {
            parsedArgs = invokeArgs.trim() ? JSON.parse(invokeArgs) : {};
        } catch {
            setInvokeResult(null);
            setInvokeError('Arguments must be valid JSON.');
            return;
        }
        // Invoking a tool executes it (risk-gated): confirm first.
        // eslint-disable-next-line no-alert
        if (!window.confirm(`Invoke MCP tool "${tool}" through the risk gate?`)) {
            return;
        }
        const gen = ++invokeGen.current;
        setInvoking(true);
        setInvokeError(null);
        setInvokeResult(null);
        try {
            const result = await arcService.invokeMcpTool(tool, parsedArgs);
            if (invokeGen.current === gen) {
                setInvokeResult(result);
            }
        } catch (e) {
            if (invokeGen.current === gen) {
                setInvokeError(e instanceof Error ? e.message : String(e));
            }
        } finally {
            if (invokeGen.current === gen) {
                setInvoking(false);
            }
        }
    }, [arcService, invokeTool, invokeArgs]);

    const cancelInvoke = React.useCallback(() => {
        // Supersede the in-flight invocation: its result will be discarded on resolve.
        invokeGen.current++;
        setInvoking(false);
        setInvokeError('Invocation cancelled.');
    }, []);

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
                <h4>Invoke Tool</h4>
                <div className='arc-mcp-workbench__invoke'>
                    <label className='arc-mcp-workbench__label' htmlFor='mcp-invoke-tool'>Tool</label>
                    <select
                        id='mcp-invoke-tool'
                        value={invokeTool}
                        onChange={e => setInvokeTool(e.target.value)}
                    >
                        <option value=''>Select a tool…</option>
                        {status.tools.map((t, i) => (
                            <option key={i} value={t}>{t}</option>
                        ))}
                    </select>
                    <label className='arc-mcp-workbench__label' htmlFor='mcp-invoke-args'>Arguments (JSON)</label>
                    <textarea
                        id='mcp-invoke-args'
                        className='arc-mcp-workbench__args'
                        value={invokeArgs}
                        onChange={e => setInvokeArgs(e.target.value)}
                        rows={3}
                        spellCheck={false}
                    />
                    <button
                        className='arc-mcp-workbench__invoke-btn'
                        disabled={!invokeTool || invoking}
                        aria-label={`Invoke MCP tool ${invokeTool || ''}`}
                        onClick={runInvoke}
                    >
                        {invoking ? 'Invoking…' : 'Invoke (risk-gated)'}
                    </button>
                    {invoking && (
                        <button
                            className='arc-mcp-workbench__invoke-cancel'
                            aria-label='Cancel MCP tool invocation'
                            onClick={cancelInvoke}
                        >
                            Cancel
                        </button>
                    )}
                    {invokeError && (
                        <div className='arc-mcp-workbench__invoke-error' role='alert'>Error: {invokeError}</div>
                    )}
                    {invokeResult && (
                        <div
                            className={`arc-mcp-workbench__invoke-result arc-mcp-workbench__invoke-result--${invokeResult.ok ? 'ok' : 'denied'}`}
                            role='status'
                        >
                            <div>
                                <strong>{invokeResult.ok ? 'OK' : 'Denied / failed'}</strong>
                                {invokeResult.riskLevel && (
                                    <span className='arc-mcp-workbench__badge'> risk:{invokeResult.riskLevel}</span>
                                )}
                            </div>
                            {invokeResult.error && <div>{invokeResult.error}</div>}
                            {invokeResult.ok && (
                                <pre className='arc-mcp-workbench__invoke-data'>{JSON.stringify(invokeResult.data, null, 2)}</pre>
                            )}
                        </div>
                    )}
                </div>
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
