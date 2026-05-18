/**
 * SwarmGraph Insight Tab
 *
 * Honest trace-backed topology, consensus, and cost panels.
 */

import * as React from '@theia/core/shared/react';
import type { ActiveTraceEventChunk, ArcService, TraceData, TraceEvent, TraceFile } from '../../common/arc-protocol';
import {
    buildLiveInsightStatus,
    buildSwarmGraphInsight,
    type SwarmGraphConsensusInsight,
    type SwarmGraphCostInsight,
    type SwarmGraphInsightStatus,
    type SwarmGraphRuntimeMetadata,
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
        return 'trace events present';
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

function isTraceEvent(value: ActiveTraceEventChunk['event']): value is TraceEvent {
    return Boolean(value && typeof value === 'object' && 'type' in value && 'timestamp' in value);
}

function buildActiveTrace(runId: string, events: TraceEvent[]): TraceData {
    return {
        id: runId,
        workflowId: runId,
        runtime: 'active',
        status: 'running',
        startedAt: events[0]?.timestamp ?? new Date(0).toISOString(),
        events,
        metadata: {},
    };
}

function safeMetadataSummary(metadata?: Record<string, unknown>): string {
    const keys = Object.keys(metadata || {}).filter(key => !/secret|token|password|api[_-]?key|credential/i.test(key));
    return keys.length ? keys.slice(0, 6).join(', ') : 'none';
}

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
                <p className='arc-studio-swarmgraph__empty'>{cost.reason ?? 'No SwarmGraph cost events found. Cost stays empty until measured cost trace events are present.'}</p>
        )}
    </Panel>
);

const RuntimeMetadataPanel: React.FC<{ metadata: SwarmGraphRuntimeMetadata }> = ({ metadata }) => {
    const rows = [
        ['runtime mode', metadata.runtimeMode],
        ['provider call', metadata.realProviderCall === undefined ? undefined : metadata.realProviderCall ? 'real provider call reported' : 'fake/offline/no provider call'],
        ['runtime gate', metadata.realRuntimeGated === undefined ? undefined : metadata.realRuntimeGated ? 'real runtime gated' : 'real runtime not gated'],
        ['real path absent', metadata.realPathAbsentReason],
    ].filter((row): row is [string, string] => typeof row[1] === 'string' && row[1].trim().length > 0);

    if (rows.length === 0) {
        return null;
    }

    return (
        <section className='arc-studio-swarmgraph__panel arc-studio-swarmgraph__panel--metadata'>
            <div className='arc-studio-swarmgraph__panel-header'>
                <h3>Runtime Metadata</h3>
                <span className='arc-studio-swarmgraph__badge arc-studio-swarmgraph__badge--metadata'>informational</span>
            </div>
            <p className='arc-studio-swarmgraph__note'>Shown as gating/provenance metadata only; not promoted to topology, consensus, or cost insight.</p>
            <dl className='arc-studio-swarmgraph__details'>
                {rows.map(([label, value]) => <React.Fragment key={label}><dt>{label}</dt><dd>{value}</dd></React.Fragment>)}
            </dl>
        </section>
    );
};

export const SwarmGraphInsightTab: React.FC<SwarmGraphInsightTabProps> = ({ arcService }) => {
    const [traces, setTraces] = React.useState<TraceFile[]>([]);
    const [selectedTraceId, setSelectedTraceId] = React.useState('');
    const [loadingTraces, setLoadingTraces] = React.useState(false);
    const [loadingTrace, setLoadingTrace] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [insight, setInsight] = React.useState(buildSwarmGraphInsight(null));
    const [liveRunId, setLiveRunId] = React.useState('');
    const [liveBaseUrl, setLiveBaseUrl] = React.useState('');
    const [liveReason, setLiveReason] = React.useState<string | undefined>();
    const [liveState, setLiveState] = React.useState<'idle' | 'connecting' | 'live' | 'disconnected' | 'degraded' | 'error'>('idle');
    const [liveEvents, setLiveEvents] = React.useState<TraceEvent[]>([]);
    const streamCancelled = React.useRef(false);

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

    const connectLiveStream = React.useCallback(async () => {
        const runId = liveRunId.trim();
        const baseUrl = liveBaseUrl.trim();
        if (!runId) {
            setLiveState('degraded');
            setLiveReason('run ID is required for live stream probe');
            return;
        }
        if (!baseUrl) {
            setLiveState('disconnected');
            setLiveReason('no Python web/SSE base URL configured');
            setError(null);
            return;
        }
        streamCancelled.current = false;
        setLiveEvents([]);
        setLiveState('connecting');
        setLiveReason(undefined);
        setError(null);
        try {
            const stream = await arcService.streamActiveTrace({ runId, mode: 'live', baseUrl });
            for await (const chunk of stream) {
                if (streamCancelled.current) {
                    return;
                }
                if (chunk.status?.message) {
                    setLiveReason(chunk.status.message);
                }
                if (chunk.status?.state === 'connected') {
                    setLiveState('live');
                }
                if (isTraceEvent(chunk.event)) {
                    setLiveEvents(current => {
                        const next = [...current, chunk.event as TraceEvent];
                        setInsight(buildSwarmGraphInsight(buildActiveTrace(runId, next)));
                        return next;
                    });
                }
                if (chunk.done) {
                    setLiveState('disconnected');
                    if (chunk.status?.message) {
                        setLiveReason(chunk.status.message);
                    }
                    return;
                }
            }
            setLiveState('disconnected');
        } catch (streamError) {
            if (!streamCancelled.current) {
                setLiveState('error');
                const message = errorMessage(streamError);
                setLiveReason(message);
                setError(message);
            }
        }
    }, [arcService, liveBaseUrl, liveRunId]);

    const disconnectLiveStream = React.useCallback(() => {
        streamCancelled.current = true;
        setLiveState(current => current === 'live' || current === 'connecting' ? 'disconnected' : current);
    }, []);

    const liveStatus = buildLiveInsightStatus({ state: liveState, eventCount: liveEvents.length, baseUrl: liveBaseUrl, reason: liveReason });

    return (
        <div className='arc-studio-swarmgraph' role='region' aria-label='SwarmGraph insight panel'>
            <div className='arc-studio-swarmgraph__header'>
                <div>
                    <h2>SwarmGraph Insight</h2>
                    <p>Trace-backed only. Cost requires measured trace events; runtime metadata is not promoted to insight.</p>
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
            <div className='arc-studio-swarmgraph__live-controls'>
                <label htmlFor='arc-swarmgraph-live-run'>Optional active run ID</label>
                <input id='arc-swarmgraph-live-run' className='arc-studio-swarmgraph__input' value={liveRunId} onChange={event => setLiveRunId(event.currentTarget.value)} placeholder='run id for live/degraded stream probe' />
                <label htmlFor='arc-swarmgraph-live-base-url'>Python web/SSE base URL</label>
                <input id='arc-swarmgraph-live-base-url' className='arc-studio-swarmgraph__input' value={liveBaseUrl} onChange={event => setLiveBaseUrl(event.currentTarget.value)} placeholder='required for degraded live attempt, e.g. http://127.0.0.1:8000' />
                <button className='arc-studio-swarmgraph__button' onClick={connectLiveStream} disabled={liveState === 'connecting' || liveState === 'live'}>Connect live</button>
                <button className='arc-studio-swarmgraph__button' onClick={disconnectLiveStream} disabled={liveState !== 'connecting' && liveState !== 'live'}>Disconnect</button>
            </div>
            <div className='arc-studio-swarmgraph__trace-metadata'>
                Trace metadata keys: {safeMetadataSummary(insight.runtimeMetadata as unknown as Record<string, unknown>)}. Display is provenance-only; absent event data stays degraded.
            </div>
            <div className={`arc-studio-swarmgraph__live-status arc-studio-swarmgraph__live-status--${liveState}`}>
                Live insight: {liveStatus.text}. Base URL: {liveStatus.baseUrlConfigured ? 'configured' : 'not configured'}. Live mode is a limited Python SSE probe; disconnected/degraded states mean no active stream is reachable.
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
                <RuntimeMetadataPanel metadata={insight.runtimeMetadata} />
            </div>
        </div>
    );
};
