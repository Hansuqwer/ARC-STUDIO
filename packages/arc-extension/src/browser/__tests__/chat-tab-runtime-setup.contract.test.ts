/**
 * Chat runtime setup contract tests.
 * Static source checks only; no Theia/jsdom runtime required.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ChatTab runtime setup UX contract', () => {
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs', 'ChatTab.tsx'),
            'utf-8'
        );
    });

    it('loads config status when backend supports it', () => {
        expect(source).toMatch(/getConfigStatus/);
        expect(source).toMatch(/setConfigStatus/);
        expect(source).toMatch(/status\.runtime\.defaultRuntime/);
        expect(source).toMatch(/status\.runtime\.isolation/);
    });

    it('keeps fallback profiles but does not render hardcoded-only profile options', () => {
        expect(source).toMatch(/FALLBACK_PROFILES/);
        expect(source).toMatch(/profileOptions/);
        expect(source).toMatch(/profileOptions\.map/);
        expect(source).not.toMatch(/<option value='local-safe'>local-safe<\/option>/);
        expect(source).not.toMatch(/<option value='local-paid'>local-paid<\/option>/);
    });

    it('shows isolation selector derived from config or safe fallback', () => {
        expect(source).toMatch(/FALLBACK_ISOLATION/);
        expect(source).toMatch(/isolationOptions/);
        expect(source).toMatch(/arc-studio-chat__isolation-selector/);
        expect(source).toMatch(/setIsolationId/);
    });

    it('passes selected runtime profile paid flag and dry-run to preflight/start', () => {
        expect(source).toMatch(/runtimeId,/);
        expect(source).toMatch(/profileId,/);
        expect(source).toMatch(/allowPaidCalls,/);
        expect(source).toMatch(/dryRun: true/);
        expect(source).toMatch(/preflightRun\(\{/);
        expect(source).toMatch(/startRun\(\{/);
    });

    it('preserves fake offline launch label and dry-run provider-call guard text', () => {
        expect(source).toMatch(/CrewAI \+ SwarmGraph \(fake\/offline\)/);
        expect(source).toMatch(/Run fake\/offline/);
        expect(source).toMatch(/Dry-run preflight/);
        expect(source).toMatch(/providerCall:false/);
    });

    it('surfaces capability metadata as keys only without provider readiness claim', () => {
        expect(source).toMatch(/arc-studio-chat__runtime-metadata/);
        expect(source).toMatch(/Capability metadata keys/);
        expect(source).toMatch(/Trace metadata keys/);
        expect(source).toMatch(/safeMetadataKeys/);
        expect(source).not.toMatch(/provider ready/i);
    });

    it('does not expose raw key or secret inputs', () => {
        expect(source).not.toMatch(/apiKey|secret|password/i);
        expect(source).not.toMatch(/type=['"]password['"]/);
    });
});
