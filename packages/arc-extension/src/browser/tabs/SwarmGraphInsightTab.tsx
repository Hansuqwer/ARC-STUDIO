/**
 * SwarmGraph Insight Tab
 *
 * Honest trace-backed topology, consensus, and cost panels.
 */

import * as React from '@theia/core/shared/react';
import type { ArcService, TraceFile } from '../../common/arc-protocol';
import {
    buildSwarmGraphInsight,
    type SwarmGraphConsensusInsight,
    type SwarmGraphCostInsight,
    type SwarmGraphInsightStatus,
    type SwarmGraphTopologyInsight,
} from './swarmgraph-insight-model';

export interface SwarmGraphInsightTabProps {
    arcService: ArcService;
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

function formatTime(value?: string): string {
    if (!value) {
        return 'not provided';
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function stateCopy(status: SwarmGraphInsightStatus): string {
    if (status === 'present') {
        return 'real trace events present';
    }
    if (status === 'degraded') {
        return 'SwarmGraph run detected; required insight events missing or incomplete';
    }
    return 'no SwarmGraph insight events found';
}

const Panel: React.FC<React.PropsWithChildren<{ title: string; status: SwarmGraphInsightStatus }>> = ({ title, status, children }) => (
    <section className={`arc-studio-swarmgraph__panel arc-studio-swarmgraph__panel--${status}`}>
        <div className='arc-studio-swarmgraph__panel-header'>
            <h3>{title}</h3>
            <span className={`arc-studio-swarmgraph__badge arc-studio-swarmgraph__badge--${status}`}>{status}</span>
        </div>
        <p className='arc-studio-swarmgraph__note'>{stateCopy(status)}</p>
        {children}
    </section>
);

const TopologyPanel: React.FC<{ topology: SwarmGraphTopologyInsight }> = ({ topology }) => (
    <Panel title='Topology' status={topology.status}>
        {topology.status === 'present' ? (
            <div className='arc-studio-swarmgraph__topology'>
                <div>
                    <h4>Nodes</h4>
                    {topology.nodes.length === 0 ? <p>None reported.</p> : topology.nodes.map(node => (
                        <div className='arc-studio-swarmgraph__item' key={node.id}>
                            <strong>{node.label ?? node.id}</strong>
                            <span>{node.role ?? 'role not reported'}</span>
                        </div>
                    ))}
                </div>
                <div>
                    <h4>Edges</h4>
                    {topology.edges.length === 0 ? <p>None reported.</p> : topology.edges.map((edge, index) => (
                        <div className='arc-studio-swarmgraph__item' key={`${edge.source}-${edge.target}-${index}`}>
                            <strong>{edge.source} -&gt; {edge.target}</strong>
                            <span>{edge.label ?? 'relationship not reported'}</span>
                        </div>
                    ))}
                </div>
            </div>
        ) : (
                <p className='arc-studio-swarmgraph__empty'>No SwarmGraph topology events found. Waiting for real topology trace events.</p>
        )}
    </Panel>
);

const ConsensusPanel: React.FC<{ consensus: SwarmGraphConsensusInsight }> = ({ consensus }) => (
    <Panel title='Consensus' status={consensus.status}>
        {consensus.status === 'present' ? (
            <dl className='arc-studio-swarmgraph__details'>
                <dt>decision</dt><dd>{consensus.decision ?? 'not reported'}</dd>
                <dt>strategy</dt><dd>{consensus.strategy ?? 'not reported'}</dd>
                <dt>voters</dt><dd>{consensus.voters.length ? consensus.voters.join(', ') : 'not reported'}</dd>
                <dt>vote records</dt><dd>{consensus.votes.length}</dd>
            </dl>
        ) : (
                <p className='arc-studio-swarmgraph__empty'>No SwarmGraph consensus events found. Runtime metadata is intentionally not shown as real consensus.</p>
        )}
    </Panel>
);

const CostPanel: React.FC<{ cost: SwarmGraphCostInsight }> = ({ cost }) => (
    <Panel title='Cost' status={cost.status}>
        {cost.status === 'present' ? (
            <dl className='arc-studio-swarmgraph__details'>
                <dt>total cost</dt><dd>{cost.totalCost ?? 'not reported'}</dd>
                <dt>tokens</dt><dd>{cost.totalTokens ?? 'not reported'}</dd>
                <dt>currency</dt><dd>{cost.currency ?? 'not reported'}</dd>
                <dt>line items</dt><dd>{cost.items.length}</dd>
            </dl>
        ) : (
                <p className='arc-studio-swarmgraph__empty'>No SwarmGraph cost events found. Waiting for real cost trace events.</p>
        )}
    </Panel>
);

export const SwarmGraphInsightTab: React.FC<SwarmGraphInsightTabProps> = ({ arcService }) => {
    const [traces, setTraces] = React.useState<TraceFile[]>([]);
    const [selectedTraceId, setSelectedTraceId] = React.useState('');
    const [loadingTraces, setLoadingTraces] = React.useState(false);
    const [loadingTrace, setLoadingTrace] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [insight, setInsight] = React.useState(buildSwarmGraphInsight(null));

    const loadTraces = React.useCallback(async () => {
        setLoadingTraces(true);
        setError(null);
        try {
            const nextTraces = await arcService.getTraces();
            setTraces(nextTraces);
            setSelectedTraceId(current => current || nextTraces[0]?.id || '');
        } catch (loadError) {
            setError(errorMessage(loadError));
        } finally {
            setLoadingTraces(false);
        }
    }, [arcService]);

    React.useEffect(() => {
        loadTraces();
    }, [loadTraces]);

    React.useEffect(() => {
        if (!selectedTraceId) {
            setInsight(buildSwarmGraphInsight(null));
            return;
        }
        let cancelled = false;
        setLoadingTrace(true);
        setError(null);
        arcService.readTrace(selectedTraceId)
            .then(trace => {
                if (!cancelled) {
                    setInsight(buildSwarmGraphInsight(trace));
                }
            })
            .catch(readError => {
                if (!cancelled) {
                    setError(errorMessage(readError));
                    setInsight(buildSwarmGraphInsight(null));
                }
            })
            .finally(() => {
                if (!cancelled) {
                    setLoadingTrace(false);
                }
            });
        return () => {
            cancelled = true;
        };
    }, [arcService, selectedTraceId]);

    return (
        <div className='arc-studio-swarmgraph' role='region' aria-label='SwarmGraph insight panel'>
            <div className='arc-studio-swarmgraph__header'>
                <div>
                    <h2>SwarmGraph Insight</h2>
                    <p>Trace-backed only. Runtime metadata is not promoted to insight.</p>
                </div>
                <button className='arc-studio-swarmgraph__button' onClick={loadTraces} disabled={loadingTraces}>
                    {loadingTraces ? 'Loading...' : 'Refresh'}
                </button>
            </div>
            <div className='arc-studio-swarmgraph__controls'>
                <label htmlFor='arc-swarmgraph-trace'>Trace</label>
                <select id='arc-swarmgraph-trace' className='arc-studio-swarmgraph__select' value={selectedTraceId} onChange={event => setSelectedTraceId(event.currentTarget.value)} disabled={loadingTraces || traces.length === 0}>
                    {traces.length === 0 ? <option value=''>No traces found</option> : traces.map(trace => (
                        <option value={trace.id} key={trace.id}>{trace.id} - {trace.status} - {formatTime(trace.timestamp)}</option>
                    ))}
                </select>
            </div>
            {error && <div className='arc-studio-swarmgraph__error' role='alert'>{error}</div>}
            {loadingTrace && <div className='arc-studio-swarmgraph__loading'>Loading trace...</div>}
            {!loadingTraces && !loadingTrace && traces.length === 0 && <div className='arc-studio-swarmgraph__empty'>No traces available.</div>}
            {insight.reasons.length > 0 && <div className='arc-studio-swarmgraph__reasons'>{insight.reasons.map(reason => <div key={reason}>{reason}</div>)}</div>}
            <div className='arc-studio-swarmgraph__grid'>
                {/* Insight derives from trace event.type via buildSwarmGraphInsight; metadata is informational only. */}
                <TopologyPanel topology={insight.topology} />
                <ConsensusPanel consensus={insight.consensus} />
                <CostPanel cost={insight.cost} />
            </div>
        </div>
    );
};
