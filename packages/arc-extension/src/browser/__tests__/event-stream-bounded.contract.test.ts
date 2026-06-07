/**
 * CR-014: the live event buffer must be bounded (memory + re-render cost).
 *
 * Source-pattern contract test (same approach as ui-components.contract.test.ts).
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ArcEventStreamWidget bounded live buffer (CR-014)', () => {
    let source: string;
    beforeAll(async () => {
        source = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'arc-event-stream-widget.tsx'),
            'utf-8',
        );
    });

    it('defines a finite cap on the live buffer', () => {
        expect(source).toMatch(/const MAX_LIVE_EVENTS = \d+/);
    });

    it('evicts oldest events past the cap instead of growing unbounded', () => {
        expect(source).toMatch(/next\.length > MAX_LIVE_EVENTS/);
        expect(source).toMatch(/next\.slice\(next\.length - MAX_LIVE_EVENTS\)/);
        // The old unbounded append must be gone.
        expect(source).not.toMatch(/this\.liveEvents = \[\.\.\.this\.liveEvents, event\];/);
    });

    it('tracks and surfaces an eviction count', () => {
        expect(source).toMatch(/evictedEventCount/);
        expect(source).toMatch(/this\.evictedEventCount > 0 &&/);
        expect(source).toMatch(/evicted to bound memory/);
    });

    it('resets the eviction count when the buffer is cleared', () => {
        expect(source).toMatch(/this\.evictedEventCount = 0;/);
    });
});
