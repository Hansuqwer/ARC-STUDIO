import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { AGUIEventType } from '../../../arc-ag-ui/src/event-types';

const FIXTURE_DIR = join(__dirname, '../../../../protocol/fixtures/run-event');

describe('AG-UI event-type parity', () => {
  it('every fixture event.type is a known AGUIEventType', () => {
    const enumValues = new Set<string>(Object.values(AGUIEventType));
    const missing: string[] = [];
    
    const files = readdirSync(FIXTURE_DIR).filter(f => f.endsWith('.json'));
    
    for (const file of files) {
      const fixturePath = join(FIXTURE_DIR, file);
      const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
      
      if (!enumValues.has(fixture.type)) {
        missing.push(`${file}: ${fixture.type}`);
      }
    }
    
    expect(missing).toEqual([]);
  });
});
