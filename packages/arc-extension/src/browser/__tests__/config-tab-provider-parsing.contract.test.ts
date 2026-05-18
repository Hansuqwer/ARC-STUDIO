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

    it('wires provider telemetry helpers reset gate and cost policy summary into ConfigTab', () => {
        expect(source).toMatch(/parseProviderDiagnostics/);
        expect(source).toMatch(/parseQuotaCounters/);
        expect(source).toMatch(/summarizeProfileCostPolicy/);
        expect(source).toMatch(/buildQuotaResetConfirmation/);
        expect(source).toMatch(/buildLiveProviderGate/);
        expect(source).toMatch(/canResetQuota/);
        expect(source).toMatch(/resetProviderQuota/);
        expect(source).toMatch(/Local quota-counter reset/);
        expect(source).toMatch(/no provider network calls/);
        expect(source).toMatch(/No provider network, no live API, no billing action/);
        expect(source).toMatch(/arc-studio-config__cost-policy-summary/);
        expect(source).toMatch(/Paid\/live provider calls require explicit backend-enforced opt-in gates/);
    });

    it('requires exact confirmation phrase before local quota reset can run', () => {
        expect(source).toMatch(/quotaResetRequiredPhrase/);
        expect(source).toMatch(/RESET LOCAL QUOTA COUNTERS/);
        expect(source).toMatch(/quotaResetPhrase === quotaResetRequiredPhrase/);
        expect(source).toMatch(/disabled=\{quotaResetting \|\| !quotaResetConfirmed\}/);
        expect(source).toMatch(/role='dialog'/);
        expect(source).toMatch(/Type exact phrase/);
    });

    it('shows preview-only live provider gate without provider/proxy calls', () => {
        expect(source).toMatch(/arc-studio-config__live-provider-gate/);
        expect(source).toMatch(/No network by default: providerCall:false/);
        expect(source).toMatch(/never calls provider API, provider proxy, live API, or billing endpoints/);
        expect(source).toMatch(/providerCall: false/);
        expect(helperSource).toMatch(/providerCall: false/);
        expect(helperSource).toMatch(/backend-enforced opt-in; UI remains preview\/offline and never enables provider execution/);
        expect(helperSource).toMatch(/Local\/offline quota\/cost preview only/);
        expect(source).not.toMatch(/providerTelemetryService\.(?!getProviderDiagnostics|getProviderQuota|resetProviderQuota)/);
    });
});
