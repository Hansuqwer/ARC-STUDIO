import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { AGUIEventType } from '../../../arc-ag-ui/src/event-types';
import { parseRunEvent } from '../run-events';

const FIXTURE_DIR = join(__dirname, '../../../../protocol/fixtures/run-event');

describe('AG-UI event-type parity', () => {
  it('round-trips every fixture through the TS RunEvent parser', () => {
    const files = readdirSync(FIXTURE_DIR).filter(f => f.endsWith('.json'));

    for (const file of files) {
      const fixturePath = join(FIXTURE_DIR, file);
      const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
      const parsed = parseRunEvent(fixture);

      expect(parsed).toEqual(fixture);
    }
  });

  it('allows ARC-private fixture types outside AG-UI without dropping data', () => {
    const enumValues = new Set<string>(Object.values(AGUIEventType));
    const files = readdirSync(FIXTURE_DIR).filter(f => f.endsWith('.json'));
    let privateTypeCount = 0;

    for (const file of files) {
      const fixturePath = join(FIXTURE_DIR, file);
      const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));

      if (!enumValues.has(fixture.type)) {
        privateTypeCount += 1;
        const parsed = parseRunEvent(fixture);
        expect(parsed.type).toBe(fixture.type);
        expect(parsed.data).toEqual(fixture.data);
      }
    }

    expect(privateTypeCount).toBeGreaterThan(0);
  });
});
