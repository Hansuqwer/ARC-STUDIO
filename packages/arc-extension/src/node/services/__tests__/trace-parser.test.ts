/**
 * CR-015: TraceParser must bound memory — reject an oversized file for a full
 * in-memory parse rather than reading it all, while still parsing normal traces.
 */

import * as fs from 'fs-extra';
import * as os from 'os';
import * as path from 'path';
import { TraceParser } from '../trace-parser';

describe('TraceParser size caps (CR-015)', () => {
    const parser = new TraceParser();
    let dir: string;

    beforeEach(async () => {
        dir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-trace-'));
    });
    afterEach(async () => {
        await fs.remove(dir);
    });

    it('parses a normal small JSONL trace (happy-path regression)', async () => {
        const p = path.join(dir, 't.jsonl');
        await fs.writeFile(
            p,
            '{"type":"RUN_STARTED","timestamp":"2026-01-01T00:00:00Z","sequence":0}\n' +
                '{"type":"RUN_COMPLETED","timestamp":"2026-01-01T00:00:01Z","sequence":1}\n',
        );
        const result = await parser.parseTrace(p, 'r1');
        expect(result).not.toBeNull();
        expect(result!.events.length).toBe(2);
    });

    it('rejects a file larger than the cap instead of reading it all', async () => {
        const p = path.join(dir, 'big.jsonl');
        // Sparse file: 65 MB apparent size with no real bytes written.
        const fd = await fs.open(p, 'w');
        await fs.ftruncate(fd, 65 * 1024 * 1024);
        await fs.close(fd);
        await expect(parser.parseTrace(p, 'r1')).rejects.toThrow(/too large to parse fully/);
    });

    it('streams events from a normal trace', async () => {
        const p = path.join(dir, 's.jsonl');
        await fs.writeFile(
            p,
            '{"type":"RUN_STARTED","timestamp":"2026-01-01T00:00:00Z","sequence":0}\n' +
                '{"type":"RUN_COMPLETED","timestamp":"2026-01-01T00:00:01Z","sequence":1}\n',
        );
        const seen: string[] = [];
        for await (const event of parser.streamTrace(p)) {
            seen.push(event.type);
        }
        expect(seen).toEqual(['RUN_STARTED', 'RUN_COMPLETED']);
    });
});
