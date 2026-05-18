/**
 * ConfigTab provider telemetry parsing contract tests.
 * Static/source fixtures only; no Theia/jsdom runtime required.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ConfigTab provider telemetry parsing contract', () => {
    let source: string;
    let helperSource: string;

    beforeAll(async () => {
        source = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs', 'ConfigTab.tsx'),
            'utf-8'
        );
        helperSource = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs', 'provider-telemetry.ts'),
            'utf-8'
        );
    });

    it('parses supported quota counter keys and ignores invalid/non-number values', () => {
        const counterPattern = /\^\(dry_run\|live\):\(provider\|account\):\(\[A-Za-z0-9_\.:-\]\+\)\$/;
        expect(helperSource).toMatch(counterPattern);
        expect(helperSource).toMatch(/typeof count !== 'number'/);
        expect(helperSource).toMatch(/bucket: match\[1\] as 'dry_run' \| 'live'/);

        const matcher = /^(dry_run|live):(provider|account):([A-Za-z0-9_.:-]+)$/;
        const fixtures: Record<string, unknown> = {
            'dry_run:provider:openai': 3,
            'live:account:acct-1': 7,
            'live:provider:anthropic': '4',
            'bad:provider:openai': 1,
        };
        const rows = Object.entries(fixtures).flatMap(([key, value]) => {
            const match = matcher.exec(key);
            if (!match || typeof value !== 'number') return [];
            return [{ key, bucket: match[1], scope: match[2], id: match[3], count: value }];
        });

        expect(source).toMatch(/parseQuotaCounters\(providerQuota\)/);
        expect(source).not.toMatch(/function quotaCounterRows/);
        expect(source).not.toMatch(/\^\(dry_run\|live\):\(provider\|account\):\(\[A-Za-z0-9_\.:-\]\+\)\$/);
        expect(rows).toEqual([
            { key: 'dry_run:provider:openai', bucket: 'dry_run', scope: 'provider', id: 'openai', count: 3 },
            { key: 'live:account:acct-1', bucket: 'live', scope: 'account', id: 'acct-1', count: 7 },
        ]);
    });

    it('handles provider diagnostics field aliases in source', () => {
        expect(source).toMatch(/getProviderDiagnostics/);
        expect(helperSource).toMatch(/live_tests_enabled', 'liveTestsEnabled', 'liveTests/);
        expect(helperSource).toMatch(/routing_default', 'routingDefault', 'default_provider', 'defaultProvider/);
        expect(helperSource).toMatch(/configured_providers_count', 'configuredProvidersCount/);
        expect(helperSource).toMatch(/configured_accounts_count', 'configuredAccountsCount/);
        expect(helperSource).toMatch(/quotaObject\?\.counters/);
    });

    it('wires optional provider telemetry helpers reset gate and cost policy summary into ConfigTab', () => {
        expect(source).toMatch(/parseProviderDiagnostics/);
        expect(source).toMatch(/parseQuotaCounters/);
        expect(source).toMatch(/summarizeProfileCostPolicy/);
        expect(source).toMatch(/buildQuotaResetConfirmation/);
        expect(source).toMatch(/buildLiveProviderGate/);
        expect(source).toMatch(/canResetQuota/);
        expect(source).toMatch(/if \(providerTelemetryService\.getProviderDiagnostics\)/);
        expect(source).toMatch(/if \(providerTelemetryService\.getProviderQuota\)/);
        expect(source).toMatch(/resetProviderQuota/);
        expect(source).toMatch(/Local quota-counter reset/);
        expect(source).toMatch(/no provider network calls/i);
    });

    it('shows preview-only live provider gate without provider/proxy/billing calls or real execution claims', () => {
        expect(helperSource).toMatch(/providerCall: false/);
        expect(helperSource).toMatch(/backend-enforced opt-in; UI remains preview\/offline and never enables provider execution/);
        expect(helperSource).toMatch(/Local\/offline quota\/cost preview only/);
        expect(helperSource).not.toMatch(/state:\s*'ready'/);
        expect(helperSource).not.toMatch(/preview ready/i);
        expect(source).not.toMatch(/providerProxy/i);
        expect(source).not.toMatch(/billingEndpoint/i);
        expect(source).not.toMatch(/liveProviderExecution/i);
        expect(source).not.toMatch(/enableRealProvider/i);
        expect(source).not.toMatch(/executeProvider/i);
        expect(source).not.toMatch(/fetch\(/);
        expect(source).not.toMatch(/axios\./);
    });

    it('does not imply live provider readiness, configured live tests, or paid-call enablement', () => {
        expect(source).not.toMatch(/Local provider readiness gate:[^`]*'ready'/s);
        expect(source).not.toMatch(/\bLive tests:\s*[^`]*'configured'/s);
        expect(source).not.toMatch(/Allow paid provider calls/);
        expect(source).toMatch(/backend paid-call opt-in/i);
        expect(source).toMatch(/disabled\/gated/);
        expect(source).toMatch(/provider execution is not implemented here/);
    });

    it('keeps quota reset copy local-only and non-networked', () => {
        expect(source).toMatch(/Local quota-counter reset/);
        expect(source).toMatch(/resetProviderQuota/);
        expect(source).toMatch(/no provider network calls/i);
        expect(source).toMatch(/no live API/i);
        expect(source).toMatch(/no billing action/i);
        expect(source).not.toMatch(/remote quota reset/i);
        expect(source).not.toMatch(/provider quota reset/i);
    });
});
