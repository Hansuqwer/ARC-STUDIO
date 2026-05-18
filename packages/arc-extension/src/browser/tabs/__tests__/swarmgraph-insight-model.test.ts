import type { TraceData, TraceEvent } from '../../../common/arc-protocol';
import { buildLiveInsightStatus, buildSwarmGraphInsight } from '../swarmgraph-insight-model';

function event(type: string, data: Record<string, unknown>): TraceEvent {
    return {
        type: type as TraceEvent['type'],
        timestamp: '2026-01-01T00:00:00.000Z',
        runId: 'run-1',
        sequence: 0,
        data,
    };
}

function trace(overrides: Partial<TraceData>): TraceData {
    return {
        id: 'trace-1',
        workflowId: 'workflow-1',
        runtime: 'langgraph',
        status: 'completed',
        startedAt: '2026-01-01T00:00:00.000Z',
        events: [],
        metadata: {},
        ...overrides,
    };
}

describe('buildSwarmGraphInsight', () => {
    it('returns empty without SwarmGraph runtime or events', () => {
        const insight = buildSwarmGraphInsight(trace({ events: [event('MESSAGE', { text: 'hello' })] }));

        expect(insight.status).toBe('empty');
        expect(insight.topology.status).toBe('empty');
        expect(insight.consensus.status).toBe('empty');
        expect(insight.cost.status).toBe('empty');
    });

    it('returns degraded for SwarmGraph-ish traces with no explicit insight events', () => {
        const insight = buildSwarmGraphInsight(trace({
            runtime: 'crewai+swarmgraph',
            events: [event('NODE_COMPLETED', { runtime: 'swarmgraph', node: 'queen' })],
        }));

        expect(insight.status).toBe('degraded');
        expect(insight.topology.status).toBe('degraded');
        expect(insight.consensus.status).toBe('degraded');
        expect(insight.cost.status).toBe('degraded');
        expect(insight.cost.reason).toContain('measured SwarmGraph cost trace events');
    });

    it('extracts topology only from explicit topology trace events', () => {
        const insight = buildSwarmGraphInsight(trace({
            events: [event('SWARMGRAPH_TOPOLOGY', {
                nodes: [{ id: 'queen', role: 'coordinator' }, { name: 'worker-1', label: 'Worker 1' }],
                edges: [{ source: 'queen', target: 'worker-1', label: 'delegates' }],
            })],
        }));

        expect(insight.status).toBe('present');
        expect(insight.topology).toMatchObject({
            status: 'present',
            nodes: [
                { id: 'queen', role: 'coordinator' },
                { id: 'worker-1', label: 'Worker 1' },
            ],
            edges: [{ source: 'queen', target: 'worker-1', label: 'delegates' }],
        });
        expect(insight.consensus.status).toBe('empty');
        expect(insight.cost.status).toBe('empty');
    });

    it('extracts consensus only from explicit consensus trace events', () => {
        const insight = buildSwarmGraphInsight(trace({
            events: [event('SWARMGRAPH_CONSENSUS', {
                strategy: 'majority',
                decision: 'accept',
                votes: [{ voter: 'queen', value: 'accept' }, { agent: 'worker-1', value: 'reject' }],
            })],
        }));

        expect(insight.status).toBe('present');
        expect(insight.consensus.status).toBe('present');
        expect(insight.consensus.strategy).toBe('majority');
        expect(insight.consensus.decision).toBe('accept');
        expect(insight.consensus.voters).toEqual(['queen', 'worker-1']);
        expect(insight.topology.status).toBe('empty');
        expect(insight.cost.status).toBe('empty');
    });

    it('extracts cost only from explicit cost trace events', () => {
        const insight = buildSwarmGraphInsight(trace({
            events: [event('SWARMGRAPH_COST', {
                totalCost: 0.42,
                totalTokens: 1200,
                currency: 'USD',
                items: [{ node: 'queen', cost: 0.2 }],
            })],
        }));

        expect(insight.status).toBe('present');
        expect(insight.cost.status).toBe('present');
        expect(insight.cost.totalCost).toBe(0.42);
        expect(insight.cost.totalTokens).toBe(1200);
        expect(insight.cost.currency).toBe('USD');
        expect(insight.cost.items).toEqual([{ node: 'queen', cost: 0.2 }]);
    });

    it('keeps cost degraded when explicit cost event lacks measured fields', () => {
        const insight = buildSwarmGraphInsight(trace({
            runtime: 'crewai+swarmgraph',
            events: [event('SWARMGRAPH_COST', { provider: 'offline-fixture' })],
        }));

        expect(insight.status).toBe('degraded');
        expect(insight.cost.status).toBe('degraded');
        expect(insight.cost.totalCost).toBeUndefined();
        expect(insight.cost.totalTokens).toBeUndefined();
        expect(insight.cost.reason).toContain('did not include measured cost');
    });

    it('extracts insight from appended active stream events in a synthetic trace', () => {
        const insight = buildSwarmGraphInsight(trace({
            id: 'run-live-1',
            status: 'running',
            events: [
                event('SWARMGRAPH_TOPOLOGY', { nodes: [{ id: 'queen' }] }),
                event('SWARMGRAPH_CONSENSUS', { decision: 'accept', voters: ['queen'] }),
            ],
        }));

        expect(insight.status).toBe('present');
        expect(insight.topology.nodes).toEqual([{ id: 'queen', label: undefined, role: undefined }]);
        expect(insight.consensus.decision).toBe('accept');
        expect(insight.cost.status).toBe('empty');
    });

    it('ignores fake/offline consensus metadata', () => {
        const insight = buildSwarmGraphInsight(trace({
            runtime: 'crewai+swarmgraph',
            events: [event('NODE_COMPLETED', {
                step: 'fake offline complete',
                real_runtime_gated: true,
                real_path_absent_reason: 'provider opt-in missing',
            })],
            metadata: {
                runtime_mode: 'fake/offline',
                real_provider_call: false,
                consensus: { strategy: 'fake-majority', decision: 'accept' },
                cost: { totalCost: 999 },
                topology: { nodes: [{ id: 'fake' }] },
            },
        }));

        expect(insight.status).toBe('degraded');
        expect(insight.consensus.decision).toBeUndefined();
        expect(insight.cost.totalCost).toBeUndefined();
        expect(insight.topology.nodes).toEqual([]);
        expect(insight.runtimeMetadata).toEqual({
            runtimeMode: 'fake/offline',
            realProviderCall: false,
            realRuntimeGated: true,
            realPathAbsentReason: 'provider opt-in missing',
        });
    });

    it('extracts runtime metadata from event data without promoting it to insight', () => {
        const insight = buildSwarmGraphInsight(trace({
            runtime: 'crewai+swarmgraph',
            events: [event('NODE_COMPLETED', {
                runtime_mode: 'offline',
                real_provider_call: false,
                real_runtime_gated: true,
                real_path_absent_reason: 'fake fixture selected',
            })],
        }));

        expect(insight.status).toBe('degraded');
        expect(insight.topology.nodes).toEqual([]);
        expect(insight.consensus.decision).toBeUndefined();
        expect(insight.cost.totalCost).toBeUndefined();
        expect(insight.runtimeMetadata).toEqual({
            runtimeMode: 'offline',
            realProviderCall: false,
            realRuntimeGated: true,
            realPathAbsentReason: 'fake fixture selected',
        });
    });

    it('returns empty for missing trace', () => {
        expect(buildSwarmGraphInsight(null).status).toBe('empty');
        expect(buildSwarmGraphInsight(undefined).status).toBe('empty');
    });
});

describe('buildLiveInsightStatus', () => {
    it('reports disconnected when live has no base URL', () => {
        expect(buildLiveInsightStatus({ state: 'connecting', eventCount: 0 })).toMatchObject({
            baseUrlConfigured: false,
            text: 'live stream disconnected; no Python web/SSE base URL configured',
        });
    });

    it('does not claim connected until state is live and base URL is configured', () => {
        expect(buildLiveInsightStatus({ state: 'connecting', eventCount: 0, baseUrl: 'http://127.0.0.1:8000' }).text)
            .toBe('attempting live stream via configured Python web/SSE base URL');
        expect(buildLiveInsightStatus({ state: 'live', eventCount: 1, baseUrl: 'http://127.0.0.1:8000' }).text)
            .toBe('live stream connected to configured Python SSE endpoint; 1 active event appended in memory');
    });

    it('keeps idle copy explicit about Python SSE live requirement', () => {
        expect(buildLiveInsightStatus({ state: 'idle', eventCount: 0 }).text)
            .toBe('stored trace mode; live requires a configured Python web/SSE base URL');
    });
});
