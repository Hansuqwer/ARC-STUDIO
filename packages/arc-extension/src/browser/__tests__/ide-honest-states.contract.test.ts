/**
 * IDE Honest-States Contract Tests (Prompt B — CR-011 / CR-013 / CR-020)
 *
 * Source-pattern contract tests (same approach as ui-components.contract.test.ts):
 * read the TSX/TS source and assert the structural guarantees of the DoD-elevation
 * slice — explicit error states, per-tab error boundary, and guarded keybindings.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

const browserDir = path.join(__dirname, '..', '..', '..', 'src', 'browser');

describe('IDE honest states (Prompt B)', () => {
    describe('CR-020 ErrorBoundary', () => {
        let source: string;
        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'components', 'ErrorBoundary.tsx'), 'utf-8');
        });
        it('is a React class component (error boundaries cannot be hooks)', () => {
            expect(source).toMatch(/class ErrorBoundary extends React\.Component/);
        });
        it('implements both error-boundary lifecycle methods', () => {
            expect(source).toMatch(/static getDerivedStateFromError/);
            expect(source).toMatch(/componentDidCatch/);
        });
        it('renders an accessible, recoverable fallback', () => {
            expect(source).toMatch(/role='alert'/);
            expect(source).toMatch(/aria-label=\{`Retry/);
        });
        it('is exported from the components barrel', async () => {
            const barrel = await fs.readFile(path.join(browserDir, 'components', 'index.ts'), 'utf-8');
            expect(barrel).toMatch(/export \{ ErrorBoundary \}/);
        });
        it('wraps the ARC Studio tab content and resets per tab', async () => {
            const widget = await fs.readFile(path.join(browserDir, 'arc-studio-widget.tsx'), 'utf-8');
            expect(widget).toMatch(/<ErrorBoundary key=\{activeTab\}/);
            expect(widget).toMatch(/<\/ErrorBoundary>/);
        });
    });

    describe('CR-011 RunsTab honest states', () => {
        let source: string;
        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'tabs', 'RunsTab.tsx'), 'utf-8');
        });
        it('no longer silently swallows detail errors with .catch(() => null)', () => {
            expect(source).not.toMatch(/\.catch\(\(\)\s*=>\s*null\)/);
        });
        it('uses Promise.allSettled to distinguish a fetch error from an absent artifact', () => {
            expect(source).toMatch(/Promise\.allSettled/);
            expect(source).toMatch(/status === 'rejected'/);
        });
        it('tracks explicit error state for details, audit and replay', () => {
            expect(source).toMatch(/detailsError:\s*string\s*\|\s*null/);
            expect(source).toMatch(/auditError:\s*string\s*\|\s*null/);
            expect(source).toMatch(/replayError:\s*string\s*\|\s*null/);
        });
        it('renders an error state distinct from the empty state', () => {
            expect(source).toMatch(/detailsError &&/);
            // Empty state must require absence of error AND all three artifacts.
            expect(source).toMatch(/!detailsError && !receipt && !autopsy && !contract/);
        });
        it('offers a retry from the error state', () => {
            expect(source).toMatch(/aria-label='Retry loading run details'/);
        });
        it('has no remaining empty catch blocks', () => {
            expect(source).not.toMatch(/\}\s*catch\s*\{\s*\n\s*setState/);
        });
    });

    describe('CR-013 keybinding when-guards', () => {
        let source: string;
        beforeAll(async () => {
            source = await fs.readFile(path.join(browserDir, 'arc-keybinding-contribution.ts'), 'utf-8');
        });
        it('guards every ARC keybinding with a when clause', () => {
            const registrations = source.match(/registerKeybinding\(\{[^}]*\}\)/g) ?? [];
            expect(registrations.length).toBeGreaterThanOrEqual(3);
            for (const reg of registrations) {
                expect(reg).toMatch(/when:/);
            }
        });
        it('uses the editor-text-focus guard idiom', () => {
            expect(source).toMatch(/when: '!editorTextFocus'/);
        });
    });
});
