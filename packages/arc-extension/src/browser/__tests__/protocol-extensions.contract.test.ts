/**
 * Protocol Extensions Contract Tests (Session B + B7)
 *
 * Static source-pattern tests for Config tab and Cross-linking protocol types.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('Protocol Extensions (Session B + B7)', () => {
    const protocolFile = path.join(__dirname, '..', '..', '..', 'src', 'common', 'arc-protocol.ts');
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(protocolFile, 'utf-8');
    });

    describe('Config Tab Types (Session B)', () => {
        it('should export SafeProviderKeyStatus', () => {
            expect(source).toMatch(/export interface SafeProviderKeyStatus/);
        });

        it('should have SafeProviderKeyStatus with source field, no raw key', () => {
            expect(source).toMatch(/SafeProviderKeyStatus/);
            expect(source).toMatch(/source:\s*'keyring'\s*\|\s*'env'\s*\|\s*'file'\s*\|\s*'unset'/);
            expect(source).not.toMatch(/SafeProviderKeyStatus[\s\S]*?rawKey/);
            expect(source).not.toMatch(/SafeProviderKeyStatus[\s\S]*?api_key:\s*string/);
        });

        it('should export TrustStatus', () => {
            expect(source).toMatch(/export interface TrustStatus/);
        });

        it('should have TrustStatus with trusted and trustLevel fields', () => {
            expect(source).toMatch(/TrustStatus/);
            expect(source).toMatch(/trusted:\s*boolean/);
            expect(source).toMatch(/trustLevel/);
        });

        it('should export SafeRuntimeConfig', () => {
            expect(source).toMatch(/export interface SafeRuntimeConfig/);
        });

        it('should have SafeRuntimeConfig with mode/routing fields', () => {
            expect(source).toMatch(/SafeRuntimeConfig/);
            expect(source).toMatch(/defaultRuntime/);
            expect(source).toMatch(/routingMode/);
            expect(source).toMatch(/dryRun/);
            expect(source).toMatch(/isolation/);
        });

        it('should export ConfigStatus', () => {
            expect(source).toMatch(/export interface ConfigStatus/);
        });

        it('should have ConfigStatus with backendAvailable field', () => {
            expect(source).toMatch(/ConfigStatus/);
            expect(source).toMatch(/backendAvailable:\s*boolean/);
        });

        it('should export SafeConfigUpdate', () => {
            expect(source).toMatch(/export interface SafeConfigUpdate/);
        });

        it('should have SafeConfigUpdate with only safe fields', () => {
            expect(source).toMatch(/SafeConfigUpdate/);
            expect(source).toMatch(/defaultRuntime\?/);
            expect(source).toMatch(/mode\?/);
            expect(source).toMatch(/isolation\?/);
            expect(source).toMatch(/allowPaidCalls\?/);
            expect(source).toMatch(/routingMode\?/);
        });

        it('should have getConfigStatus method on ArcService', () => {
            expect(source).toMatch(/getConfigStatus\(\):\s*Promise<ConfigStatus>/);
        });

        it('should have saveConfig method on ArcService', () => {
            expect(source).toMatch(/saveConfig\(update:\s*SafeConfigUpdate\)/);
        });
    });

    describe('Run Links Types (Session B7)', () => {
        it('should export RunLinksResponse', () => {
            expect(source).toMatch(/export interface RunLinksResponse/);
        });

        it('should have RunLinksResponse with chain fields', () => {
            expect(source).toMatch(/RunLinksResponse/);
            expect(source).toMatch(/nodeChains/);
            expect(source).toMatch(/messageChains/);
            expect(source).toMatch(/toolCallChains/);
            expect(source).toMatch(/evidenceChains/);
        });

        it('should have RunLinksResponse with stable ID metadata', () => {
            expect(source).toMatch(/hasStableIds:\s*boolean/);
            expect(source).toMatch(/stableIdCount:\s*number/);
        });

        it('should export EvidenceSelectionEvent', () => {
            expect(source).toMatch(/export interface EvidenceSelectionEvent/);
        });

        it('should have EvidenceSelectionEvent with source and timestamp', () => {
            expect(source).toMatch(/EvidenceSelectionEvent/);
            expect(source).toMatch(/evidenceRef:\s*EvidenceRef/);
            expect(source).toMatch(/source:\s*'chip-click'\s*\|\s*'keyboard'\s*\|\s*'context-menu'/);
            expect(source).toMatch(/timestamp:\s*string/);
        });

        it('should have getRunLinks method on ArcService', () => {
            expect(source).toMatch(/getRunLinks\(runId:\s*string/);
        });
    });

    describe('ProviderStatus safety', () => {
        it('should document that secrets are never exposed', () => {
            expect(source).toMatch(/Secrets are never exposed as raw values/);
        });
    });
});

describe('Backend Service Extensions (Session B + B7)', () => {
    const backendFile = path.join(__dirname, '..', '..', '..', 'src', 'node', 'arc-backend-service.ts');
    let source: string;

    beforeAll(async () => {
        source = await fs.readFile(backendFile, 'utf-8');
    });

    describe('Config methods', () => {
        it('should implement getConfigStatus', () => {
            expect(source).toMatch(/async getConfigStatus\(\)/);
        });

        it('should call arc providers status CLI', () => {
            expect(source).toMatch(/providers.*status.*--json/);
        });

        it('should call arc config show CLI', () => {
            expect(source).toMatch(/config.*show.*--json/);
        });

        it('should handle unavailable backend gracefully', () => {
            expect(source).toMatch(/backendAvailable\s*=\s*false/);
            expect(source).toMatch(/Backend unavailable/);
        });

        it('should implement saveConfig', () => {
            expect(source).toMatch(/async saveConfig\(update:\s*SafeConfigUpdate\)/);
        });

        it('should validate safe keys before saving', () => {
            expect(source).toMatch(/safeKeys/);
            expect(source).toMatch(/Rejected unsafe config field/);
        });

        it('should NOT pass raw secret values to CLI', () => {
            expect(source).not.toMatch(/api_key\s*=\s*['"]/);
            expect(source).not.toMatch(/secret\s*:\s*['"]/);
            expect(source).not.toMatch(/password\s*=\s*['"]/);
            expect(source).not.toMatch(/rawKey/);
            expect(source).not.toMatch(/rawApiKey/);
        });
    });

    describe('Run links methods', () => {
        it('should implement getRunLinks', () => {
            expect(source).toMatch(/async getRunLinks\(runId:\s*string/);
        });

        it('should call arc runs links CLI', () => {
            expect(source).toMatch(/runs.*links/);
        });

        it('should support filter and stableId params', () => {
            expect(source).toMatch(/--filter/);
            expect(source).toMatch(/--stable-id/);
        });

        it('should map Python snake_case to camelCase', () => {
            expect(source).toMatch(/node_chains/);
            expect(source).toMatch(/nodeChains/);
            expect(source).toMatch(/has_stable_ids/);
            expect(source).toMatch(/hasStableIds/);
        });
    });

    describe('Import types', () => {
        it('should import ConfigStatus', () => {
            expect(source).toMatch(/ConfigStatus/);
        });

        it('should import SafeConfigUpdate', () => {
            expect(source).toMatch(/SafeConfigUpdate/);
        });

        it('should import RunLinksResponse', () => {
            expect(source).toMatch(/RunLinksResponse/);
        });
    });
});
