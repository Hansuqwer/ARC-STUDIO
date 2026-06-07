/**
 * ConfigTab pure helpers, display constants, and shared types.
 * Stateless and side-effect-free; safe to import from the component and the state hook.
 */

import type { ArcProfileInfo, IsolationProviderInfo } from '../../common/arc-protocol';

export const RUNTIME_DISPLAY: Record<string, { label: string; badge: string }> = {
    'swarmgraph': { label: 'SwarmGraph', badge: 'SG' },
    'langgraph': { label: 'LangGraph', badge: 'LG' },
    'crewai': { label: 'CrewAI', badge: 'CR' },
    'crewai+swarmgraph': { label: 'CrewAI + SwarmGraph', badge: 'CS' },
    'openai-agents': { label: 'OpenAI Agents', badge: 'OA' },
    'ag2': { label: 'AG2', badge: 'A2' },
};

export const MODE_OPTIONS = [
    { value: 'plan' as const, label: 'Plan', description: 'read-only' },
    { value: 'build' as const, label: 'Build', description: 'edit' },
    { value: 'auto' as const, label: 'Auto', description: 'policy-driven' },
];

export const FALLBACK_ISOLATION_OPTIONS: IsolationProviderInfo[] = [
    { id: 'none', name: 'None', available: true },
    { id: 'subprocess', name: 'Subprocess', available: true },
    { id: 'docker', name: 'Docker', available: false, reason: 'status unknown' },
];

export const FALLBACK_PROFILE_OPTIONS: ArcProfileInfo[] = [
    { id: 'local-safe', name: 'local-safe', allowPaidCalls: false, dryRun: true },
    { id: 'local-paid', name: 'local-paid', allowPaidCalls: true, dryRun: false },
];

export const PROVIDER_DISPLAY: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    azure: 'Azure OpenAI',
    bedrock: 'Bedrock',
    vertex: 'Vertex',
    ollama: 'Ollama',
    qwen: 'Qwen',
    '9router': '9router',
};

export type JsonObject = Record<string, unknown>;

export function asObject(value: unknown): JsonObject | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : null;
}

export function providerSourceBadge(source: string): string {
    switch (source) {
        case 'keyring': return 'keyring';
        case 'env': return 'env';
        case 'file': return 'file';
        default: return 'unset';
    }
}

export function providerSourceColor(source: string): string {
    switch (source) {
        case 'keyring': return '#66bb6a';
        case 'env': return '#4fc3f7';
        case 'file': return '#ffb74d';
        default: return '#999';
    }
}

export function formatMetadataKeys(metadata?: Record<string, unknown>): string {
    const keys = Object.keys(metadata || {}).filter(key => !/secret|token|pass(?:word)?|api[_-]?key|credential/i.test(key));
    return keys.length > 0 ? keys.slice(0, 6).join(', ') : 'none';
}
