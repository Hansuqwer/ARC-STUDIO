import * as fs from 'fs';
import * as path from 'path';
import { KNOWN_TRACE_EVENT_TYPES } from '../../common/arc-protocol';

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
});
