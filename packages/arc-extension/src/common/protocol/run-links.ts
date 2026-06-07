/**
 * Run links / cross-link selection types (LinkedEventChain, RunLinksResponse,
 * EvidenceSelectionEvent). Extracted from arc-protocol.ts (CR-027); re-exported via the
 * barrel. Back-imports TraceEvent from the barrel and EvidenceRef from contracts-graph.
 */

import type { TraceEvent } from '../arc-protocol';
import type { EvidenceRef } from './contracts-graph';


/**
 * Linked event chain for a single stable ID.
 */
export interface LinkedEventChain {
    stableId: string;
    events: TraceEvent[];
}

/**
 * Run links response from /api/runs/{id}/links.
 * Contains cross-referenced event chains keyed by stable ID type.
 */
export interface RunLinksResponse {
    nodeChains: Record<string, TraceEvent[]>;
    messageChains: Record<string, TraceEvent[]>;
    toolCallChains: Record<string, TraceEvent[]>;
    evidenceChains: Record<string, TraceEvent[]>;
    hasStableIds: boolean;
    stableIdCount: number;
}

/**
 * Evidence selection event emitted when EvidenceChip is opened.
 */
export interface EvidenceSelectionEvent {
    evidenceRef: EvidenceRef;
    source: 'chip-click' | 'keyboard' | 'context-menu';
    timestamp: string;
}
