import type { TraceData, TraceEvent } from '../../common/arc-protocol';

export type SwarmGraphInsightStatus = 'empty' | 'degraded' | 'present';

export interface SwarmGraphTopologyNode {
    id: string;
    label?: string;
    role?: string;
}

export interface SwarmGraphTopologyEdge {
    source: string;
    target: string;
    label?: string;
}

export interface SwarmGraphTopologyInsight {
    status: SwarmGraphInsightStatus;
    nodes: SwarmGraphTopologyNode[];
    edges: SwarmGraphTopologyEdge[];
}

export interface SwarmGraphConsensusInsight {
    status: SwarmGraphInsightStatus;
    decision?: string;
    strategy?: string;
    voters: string[];
    votes: Record<string, unknown>[];
}

export interface SwarmGraphCostInsight {
    status: SwarmGraphInsightStatus;
    provider?: string;
    model?: string;
    promptTokens?: number;
    completionTokens?: number;
    totalCost?: number;
    totalTokens?: number;
    currency?: string;
    source?: string;
    measured?: string;
    items: Record<string, unknown>[];
    reason?: string;
}

export interface SwarmGraphRuntimeMetadata {
    runtimeMode?: string;
    realProviderCall?: boolean;
    realRuntimeGated?: boolean;
    realPathAbsentReason?: string;
}

export interface SwarmGraphInsight {
    status: SwarmGraphInsightStatus;
    topology: SwarmGraphTopologyInsight;
    consensus: SwarmGraphConsensusInsight;
    cost: SwarmGraphCostInsight;
    runtimeMetadata: SwarmGraphRuntimeMetadata;
    reasons: string[];
}

export type LiveInsightUiState = 'idle' | 'connecting' | 'live' | 'disconnected' | 'degraded' | 'error';

export interface LiveInsightStatusInput {
    state: LiveInsightUiState;
    eventCount: number;
    baseUrl?: string;
    reason?: string;
}

export interface LiveInsightStatusView {
    state: LiveInsightUiState;
    baseUrlConfigured: boolean;
    text: string;
}

type UnknownRecord = Record<string, unknown>;

const EMPTY_TOPOLOGY: SwarmGraphTopologyInsight = { status: 'empty', nodes: [], edges: [] };
const EMPTY_CONSENSUS: SwarmGraphConsensusInsight = { status: 'empty', voters: [], votes: [] };
const EMPTY_COST: SwarmGraphCostInsight = { status: 'empty', items: [] };

export function buildLiveInsightStatus(input: LiveInsightStatusInput): LiveInsightStatusView {
    const baseUrlConfigured = Boolean(input.baseUrl?.trim());
    const count = input.eventCount;
    let text: string;
    if (!baseUrlConfigured && (input.state === 'connecting' || input.state === 'live')) {
        text = 'live stream disconnected; no Python web/SSE base URL configured';
    } else if (input.state === 'connecting') {
        text = 'attempting live stream via configured Python web/SSE base URL';
    } else if (input.state === 'live') {
        text = `live stream connected to configured Python SSE endpoint; ${count} active event${count === 1 ? '' : 's'} appended in memory`;
    } else if (input.state === 'disconnected') {
        text = count > 0
            ? `live stream disconnected; showing ${count} previously captured active event${count === 1 ? '' : 's'} from the prior live stream attempt`
            : 'live stream disconnected; no active events captured';
    } else if (input.state === 'degraded') {
        text = 'live stream unavailable/degraded; stored trace flow still works';
    } else if (input.state === 'error') {
        text = 'live stream error; stored trace flow still works';
    } else {
        text = 'stored trace mode; live requires a configured Python web/SSE base URL';
    }
    return { state: input.state, baseUrlConfigured, text: input.reason ? `${text}: ${input.reason}` : text };
}

function isRecord(value: unknown): value is UnknownRecord {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim() ? value : undefined;
}

function asNumber(value: unknown): number | undefined {
    return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function asRecords(value: unknown): UnknownRecord[] {
    return Array.isArray(value) ? value.filter(isRecord) : [];
}

function eventType(event: TraceEvent): string {
    return String(event.type);
}

function eventKind(event: TraceEvent): string | undefined {
    return asString(event.data?.kind) ?? asString(event.data?.event) ?? asString(event.data?.name);
}

function isSwarmGraphEvent(event: TraceEvent): boolean {
    const haystack = [eventType(event), eventKind(event), event.data?.runtime, event.data?.framework]
        .filter(value => typeof value === 'string')
        .join(' ')
        .toLowerCase();
    return haystack.includes('swarmgraph') || haystack.includes('swarm_graph');
}

function isInsightEvent(event: TraceEvent, name: 'topology' | 'consensus' | 'cost'): boolean {
    const markers = [eventType(event), eventKind(event)]
        .filter((value): value is string => Boolean(value))
        .map(value => value.toLowerCase());
    return markers.some(marker =>
        marker === `swarmgraph_${name}` ||
        marker === `swarm_graph_${name}` ||
        marker === `swarmgraph.${name}` ||
        marker === `swarm_graph.${name}`
    );
}

function extractTopology(events: TraceEvent[], degraded: boolean): SwarmGraphTopologyInsight {
    const source = events.find(event => isInsightEvent(event, 'topology'))?.data;
    if (!source) {
        return degraded ? { ...EMPTY_TOPOLOGY, status: 'degraded' } : EMPTY_TOPOLOGY;
    }

    const nodes = asRecords(source.nodes).map(node => ({
        id: asString(node.id) ?? asString(node.name) ?? '',
        label: asString(node.label) ?? asString(node.name),
        role: asString(node.role),
    })).filter(node => node.id);
    const edges = asRecords(source.edges).map(edge => ({
        source: asString(edge.source) ?? asString(edge.from) ?? '',
        target: asString(edge.target) ?? asString(edge.to) ?? '',
        label: asString(edge.label),
    })).filter(edge => edge.source && edge.target);

    return nodes.length || edges.length ? { status: 'present', nodes, edges } : { ...EMPTY_TOPOLOGY, status: 'degraded' };
}

function extractConsensus(events: TraceEvent[], degraded: boolean): SwarmGraphConsensusInsight {
    const source = events.find(event => isInsightEvent(event, 'consensus'))?.data;
    if (!source) {
        return degraded ? { ...EMPTY_CONSENSUS, status: 'degraded' } : EMPTY_CONSENSUS;
    }

    const votes = asRecords(source.votes);
    const voters = Array.isArray(source.voters)
        ? source.voters.map(asString).filter((value): value is string => Boolean(value))
        : votes.map(vote => asString(vote.voter) ?? asString(vote.agent)).filter((value): value is string => Boolean(value));
    const decision = asString(source.decision) ?? asString(source.result) ?? asString(source.winner);
    const strategy = asString(source.strategy) ?? asString(source.method);

    return decision || strategy || voters.length || votes.length
        ? { status: 'present', decision, strategy, voters, votes }
        : { ...EMPTY_CONSENSUS, status: 'degraded' };
}

function extractCost(events: TraceEvent[], degraded: boolean): SwarmGraphCostInsight {
    const eventData = events.find(event => isInsightEvent(event, 'cost'))?.data;
    if (!eventData) {
        return degraded
            ? { ...EMPTY_COST, status: 'degraded', reason: 'Cost requires explicit measured SwarmGraph cost trace events; runtime/provider metadata is not used.' }
            : EMPTY_COST;
    }

    const source = eventData as Record<string, unknown>;
    const items = asRecords(source.items ?? source.breakdown);
    const totalCost = asNumber(source.totalCost) ?? asNumber(source.cost) ?? asNumber(source.total_cost);
    const totalTokens = asNumber(source.totalTokens) ?? asNumber(source.tokens) ?? asNumber(source.total_tokens);
    const currency = asString(source.currency);
    const provider = asString(source.provider);
    const model = asString(source.model);
    const promptTokens = asNumber(source.promptTokens) ?? asNumber(source.prompt_tokens);
    const completionTokens = asNumber(source.completionTokens) ?? asNumber(source.completion_tokens);
    const sourceField = asString(source.source);
    const measured = asString(source.measured);

    const hasData = totalCost !== undefined || totalTokens !== undefined || currency || items.length
        || provider !== undefined || model !== undefined || promptTokens !== undefined || completionTokens !== undefined
        || sourceField !== undefined || measured !== undefined;

    if (!hasData) {
        return { ...EMPTY_COST, status: 'degraded', reason: 'Cost event was present but did not include measured cost, token, currency, or item data.' };
    }

    const result: SwarmGraphCostInsight = { status: 'present', items };
    if (totalCost !== undefined) result.totalCost = totalCost;
    if (totalTokens !== undefined) result.totalTokens = totalTokens;
    if (currency !== undefined) result.currency = currency;
    if (provider !== undefined) result.provider = provider;
    if (model !== undefined) result.model = model;
    if (promptTokens !== undefined) result.promptTokens = promptTokens;
    if (completionTokens !== undefined) result.completionTokens = completionTokens;
    if (sourceField !== undefined) result.source = sourceField;
    if (measured !== undefined) result.measured = measured;
    return result;
}

function asBoolean(value: unknown): boolean | undefined {
    return typeof value === 'boolean' ? value : undefined;
}

function extractRuntimeMetadata(trace?: TraceData | null): SwarmGraphRuntimeMetadata {
    const sources = [trace?.metadata, ...(trace?.events ?? []).map(event => event.data)].filter(isRecord);
    const metadata: SwarmGraphRuntimeMetadata = {};
    for (const source of sources) {
        metadata.runtimeMode ??= asString(source.runtime_mode) ?? asString(source.runtimeMode);
        metadata.realProviderCall ??= asBoolean(source.real_provider_call) ?? asBoolean(source.realProviderCall);
        metadata.realRuntimeGated ??= asBoolean(source.real_runtime_gated) ?? asBoolean(source.realRuntimeGated);
        metadata.realPathAbsentReason ??= asString(source.real_path_absent_reason) ?? asString(source.realPathAbsentReason);
    }
    return metadata;
}

export function buildSwarmGraphInsight(trace?: TraceData | null): SwarmGraphInsight {
    const events = trace?.events ?? [];
    const swarmGraphish = Boolean(trace?.runtime?.toLowerCase().includes('swarmgraph')) || events.some(isSwarmGraphEvent);
    const hasInsightEvents = events.some(event =>
        isInsightEvent(event, 'topology') || isInsightEvent(event, 'consensus') || isInsightEvent(event, 'cost')
    );
    const degradeMissingSections = swarmGraphish && !hasInsightEvents;
    const topology = extractTopology(events, degradeMissingSections);
    const consensus = extractConsensus(events, degradeMissingSections);
    const cost = extractCost(events, degradeMissingSections);
    const runtimeMetadata = extractRuntimeMetadata(trace);
    const sections = [topology.status, consensus.status, cost.status];
    const status: SwarmGraphInsightStatus = sections.includes('present')
        ? 'present'
        : swarmGraphish
            ? 'degraded'
            : 'empty';
    const reasons = status === 'empty'
        ? ['No SwarmGraph trace events found.']
        : sections.includes('degraded')
            ? ['SwarmGraph run detected, but one or more insight event types are missing or incomplete.']
            : [];

    return { status, topology, consensus, cost, runtimeMetadata, reasons };
}
