import * as fs from 'fs';
import * as path from 'path';
import { KNOWN_TRACE_EVENT_TYPES, TERMINAL_TRACE_EVENT_TYPES } from '../../common/arc-protocol';

describe('KnownTraceEventType registry parity (B2P-02)', () => {
    const root = path.join(__dirname, '..', '..', '..', '..', '..');
    const registry = JSON.parse(
        fs.readFileSync(path.join(root, 'protocol', 'fixtures', 'run-event-registry.json'), 'utf-8'),
    );

    it('covers every canonical event type in the cross-language registry', () => {
        const canonical: string[] = registry.eventTypes.map((e: { type: string }) => e.type);
        const known = new Set<string>(KNOWN_TRACE_EVENT_TYPES);
        const missing = canonical.filter(t => !known.has(t));
        expect(missing).toEqual([]);
    });

    it('has no duplicate literals', () => {
        expect(new Set(KNOWN_TRACE_EVENT_TYPES).size).toBe(KNOWN_TRACE_EVENT_TYPES.length);
    });

    it('terminal event types are valid canonical types (except the STREAM_END sentinel)', () => {
        const known = new Set<string>(KNOWN_TRACE_EVENT_TYPES);
        for (const t of TERMINAL_TRACE_EVENT_TYPES) {
            if (t === 'STREAM_END') {
                continue;
            }
            expect(known.has(t)).toBe(true);
        }
    });

    it('SwarmGraph insight event types are registered (consumers parse loose payloads of typed events)', () => {
        // The SwarmGraph insight consumers (swarmgraph-insight-model.ts) keep the loose `TraceEvent`
        // object type ON PURPOSE: they defensively parse loosely-shaped payloads (e.g. nodes with
        // id|name, edges with source|from) emitted by the adoption layer. The event TYPE NAMES are
        // nonetheless registered + parity-guarded above — so this is an intentional pattern, not
        // unmigrated debt.
        const known = new Set<string>(KNOWN_TRACE_EVENT_TYPES);
        for (const t of ['SWARMGRAPH_TOPOLOGY', 'SWARMGRAPH_CONSENSUS', 'SWARMGRAPH_COST']) {
            expect(known.has(t)).toBe(true);
        }
    });
});
