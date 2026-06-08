import * as fs from 'fs';
import * as path from 'path';

const src = fs.readFileSync(
    path.join(__dirname, '..', 'arc-status-bar-contribution.ts'),
    'utf-8',
);

describe('IDE status rail (R-AUDIT27)', () => {
    it('surfaces mode, trust, runtime, and daemon slots', () => {
        expect(src).toMatch(/MODE_STATUS_ID/);
        expect(src).toMatch(/TRUST_STATUS_ID/);
        expect(src).toMatch(/RUNTIME_STATUS_ID/);
        expect(src).toMatch(/BACKEND_STATUS_ID/);
    });

    it('derives every slot from a single getConfigStatus call', () => {
        expect(src).toMatch(/getConfigStatus\(\)/);
        expect(src).toMatch(/config\?\.workspace\?\.trustLevel/);
        expect(src).toMatch(/config\?\.runtime\?\.defaultRuntime/);
        expect(src).toMatch(/config\?\.mode/);
    });

    it('degrades to unknown/offline when the daemon is unreachable (producer-truth)', () => {
        expect(src).toMatch(/config = undefined/);
        expect(src).toMatch(/daemon offline/);
        expect(src).toMatch(/'unknown'/);
    });

    it('attaches ARIA accessibilityInformation to every entry', () => {
        expect(src).toMatch(/accessibilityInformation: \{ label: e\.label, role: 'status' \}/);
    });
});
