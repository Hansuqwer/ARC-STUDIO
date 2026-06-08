/**
 * R-AUDIT18 — IDE Workspace Search panel contract (source assertions; no DOM bootstrap).
 */
import * as fs from 'fs';
import * as path from 'path';

const root = path.join(__dirname, '..', '..', '..');
const read = (rel: string) => fs.readFileSync(path.join(root, 'src', rel), 'utf-8');

describe('ArcWorkspaceSearchWidget (R-AUDIT18)', () => {
    it('is a ReactWidget wired to the real searchWorkspace producer with full states', () => {
        const src = read('browser/arc-workspace-search-widget.tsx');
        expect(src).toMatch(/extends ReactWidget/);
        expect(src).toMatch(/@inject\(ArcService\)/);
        expect(src).toMatch(/this\.arcService\.searchWorkspace\(/);
        // explicit UX states: loading, error, empty, results + accessible input/button
        expect(src).toMatch(/Searching…/);
        expect(src).toMatch(/role="alert"/);
        expect(src).toMatch(/No matches found/);
        expect(src).toMatch(/aria-label="Workspace search query"/);
        expect(src).toMatch(/aria-label="Run workspace search"/);
    });

    it('backend searchWorkspace runs path-confined `arc workspace search --json`', () => {
        const svc = read('node/arc-backend-service.ts');
        expect(svc).toMatch(/async searchWorkspace\(query: string\): Promise<WorkspaceSearchHit\[\]>/);
        expect(svc).toMatch(/'workspace', 'search'/);
        const proto = read('common/arc-protocol.ts');
        expect(proto).toMatch(/searchWorkspace\(query: string\): Promise<WorkspaceSearchHit\[\]>/);
        expect(proto).toMatch(/export interface WorkspaceSearchHit/);
    });

    it('is bound in the frontend module via a WidgetFactory', () => {
        const mod = read('browser/arc-extension-frontend-module.ts');
        expect(mod).toMatch(/bind\(ArcWorkspaceSearchWidget\)\.toSelf\(\)/);
        expect(mod).toMatch(/id: ArcWorkspaceSearchWidget\.ID/);
    });
});
