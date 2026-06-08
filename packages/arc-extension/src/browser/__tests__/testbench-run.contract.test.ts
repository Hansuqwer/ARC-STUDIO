import * as fs from 'fs';
import * as path from 'path';

const browser = path.join(__dirname, '..');
const root = path.join(browser, '..', '..');

function read(rel: string): string {
    return fs.readFileSync(path.join(root, 'src', rel), 'utf-8');
}

describe('TestBench Run button wiring (R-AUDIT29 / B2P parity)', () => {
    it('declares runTestbench + TestbenchRunResult in the ArcService protocol', () => {
        const proto = read('common/arc-protocol.ts');
        expect(proto).toMatch(/runTestbench\(command: string\): Promise<TestbenchRunResult>/);
        expect(proto).toMatch(/export interface TestbenchRunResult/);
        expect(proto).toMatch(/allowed: boolean/);
    });

    it('backend runs through the local-safe sandbox policy and surfaces non-zero exits', () => {
        const svc = read('node/arc-backend-service.ts');
        expect(svc).toMatch(/async runTestbench\(command: string\)/);
        expect(svc).toMatch(/'--policy', 'local-safe'/);
        expect(svc).toMatch(/execArcCliAsync/); // async, non-blocking
        // non-zero exit (deny/test-failure) is handled, not swallowed
        expect(svc).toMatch(/err\?\.stdout/);
        expect(svc).toMatch(/exitCode/);
    });

    it('tab has a confirm-gated, aria-labelled Run button calling runTestbench', () => {
        const tab = read('browser/tabs/TestBenchTab.tsx');
        expect(tab).toMatch(/arcService\.runTestbench\(/);
        expect(tab).toMatch(/window\.confirm\(/); // mutating action gate
        expect(tab).toMatch(/aria-label=\{`Run /);
        // explicit UX states: running, error, blocked, exit-code
        expect(tab).toMatch(/Running…/);
        expect(tab).toMatch(/Blocked by policy/);
        expect(tab).toMatch(/role='alert'/);
    });
});
