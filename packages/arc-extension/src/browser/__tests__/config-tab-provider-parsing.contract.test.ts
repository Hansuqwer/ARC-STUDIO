/**
 * ConfigTab provider telemetry parsing contract tests.
 * Static/source fixtures only; no Theia/jsdom runtime required.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('ConfigTab provider telemetry parsing contract', () => {
    let source: string;
    let stateSource: string;
    let combined: string;
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
        stateSource = await fs.readFile(
            path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs', 'useConfigTabState.ts'),
            'utf-8'
        );
        combined = `${source}\n${stateSource}`;
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

        expect(stateSource).toMatch(/parseQuotaCounters\(providerQuota\)/);
        expect(combined).not.toMatch(/function quotaCounterRows/);
        expect(combined).not.toMatch(/\^\(dry_run\|live\):\(provider\|account\):\(\[A-Za-z0-9_\.:-\]\+\)\$/);
        expect(rows).toEqual([
            { key: 'dry_run:provider:openai', bucket: 'dry_run', scope: 'provider', id: 'openai', count: 3 },
            { key: 'live:account:acct-1', bucket: 'live', scope: 'account', id: 'acct-1', count: 7 },
        ]);
    });

    it('handles provider diagnostics field aliases in source', () => {
        expect(stateSource).toMatch(/getProviderDiagnostics/);
        expect(helperSource).toMatch(/live_tests_enabled', 'liveTestsEnabled', 'liveTests/);
        expect(helperSource).toMatch(/routing_default', 'routingDefault', 'default_provider', 'defaultProvider/);
        expect(helperSource).toMatch(/configured_providers_count', 'configuredProvidersCount/);
        expect(helperSource).toMatch(/configured_accounts_count', 'configuredAccountsCount/);
        expect(helperSource).toMatch(/quotaObject\?\.counters/);
    });

    it('wires optional provider telemetry helpers reset gate and cost policy summary into ConfigTab', () => {
        expect(stateSource).toMatch(/parseProviderDiagnostics/);
        expect(stateSource).toMatch(/parseQuotaCounters/);
        expect(stateSource).toMatch(/summarizeProfileCostPolicy/);
        expect(stateSource).toMatch(/buildQuotaResetConfirmation/);
        expect(stateSource).toMatch(/buildLiveProviderGate/);
        expect(stateSource).toMatch(/canResetQuota/);
        expect(stateSource).toMatch(/if \(providerTelemetryService\.getProviderDiagnostics\)/);
        expect(stateSource).toMatch(/if \(providerTelemetryService\.getProviderQuota\)/);
        expect(stateSource).toMatch(/resetProviderQuota/);
        expect(source).toMatch(/Local quota-counter reset/);
        expect(source).toMatch(/no provider network calls/i);
    });

    it('shows preview-only live provider gate without provider/proxy/billing calls or real execution claims', () => {
        expect(helperSource).toMatch(/providerCall: false/);
        expect(helperSource).toMatch(/backend-enforced opt-in/i);
        expect(helperSource).toMatch(/preview\/offline|offline\/local|local preview/i);
        expect(helperSource).toMatch(/never enables provider execution|provider execution is not implemented/i);
        expect(helperSource).toMatch(/local\/offline quota\/cost preview only|local counters only/i);
        expect(helperSource).not.toMatch(/state:\s*'ready'/);
        expect(helperSource).not.toMatch(/preview ready/i);
        expect(combined).not.toMatch(/providerProxy/i);
        expect(combined).not.toMatch(/billingEndpoint/i);
        expect(combined).not.toMatch(/liveProviderExecution/i);
        expect(combined).not.toMatch(/enableRealProvider/i);
        expect(combined).not.toMatch(/executeProvider/i);
        expect(combined).not.toMatch(/fetch\(/);
        expect(combined).not.toMatch(/axios\./);
    });

    it('does not imply live provider readiness, configured live tests, or paid-call enablement', () => {
        expect(combined).not.toMatch(/Local provider readiness gate:[^`]*'ready'/s);
        expect(combined).not.toMatch(/\bLive tests:\s*[^`]*'configured'/s);
        expect(combined).not.toMatch(/Allow paid provider calls/);
        expect(source).toMatch(/backend[- ](?:enforced )?paid-call opt-in|backend-enforced opt-in/i);
        expect(source).toMatch(/disabled\/gated/);
        expect(source).toMatch(/does not enable real provider execution/i);
    });

    it('keeps quota reset copy local-only and non-networked', () => {
        expect(source).toMatch(/Local quota-counter reset/);
        expect(stateSource).toMatch(/resetProviderQuota/);
        expect(source).toMatch(/no provider network calls|no provider call attempted/i);
        expect(source).toMatch(/no live API/i);
        expect(source).toMatch(/no billing action/i);
        expect(source).toMatch(/local counters only|ARC storage counters only/i);
        expect(combined).not.toMatch(/remote quota reset/i);
        expect(combined).not.toMatch(/provider quota reset/i);
    });

    it('keeps R3 provider controls explicit copy/preview only, not execution controls', () => {
        expect(source).toMatch(/copy|preview/i);
        expect(source).toMatch(/dry-run\/offline|offline\/local|local preview/i);
        expect(source).toMatch(/local quota|local counters|ARC storage counters/i);
        expect(source).toMatch(/providerCall:false|providerCall: false/);
        expect(combined).not.toMatch(/runLiveProvider|startProviderRun|executeProvider|enableRealProvider/);
    });

    it('requires explicit paid-call confirmation and fails closed without optional backend method', () => {
        expect(helperSource).toMatch(/I UNDERSTAND THIS MAY COST MONEY/);
        expect(helperSource).toMatch(/optional backend action is unavailable; fail closed/);
        expect(helperSource).toMatch(/provider=\$\{provider\}, model=\$\{model\}/);
        expect(helperSource).toMatch(/Local accounting preview only/);
        expect(stateSource).toMatch(/confirmProviderAction\?:/);
        expect(source).toMatch(/providerActionAvailable/);
        expect(source).toMatch(/liveProviderConfirmPhrase/);
        expect(source).toMatch(/arc-studio-config__provider-action-confirm/);
        expect(source).toMatch(/arc-studio-config__provider-action-warning/);
        expect(source).toMatch(/arc-studio-config__provider-accounting-label/);
        expect(source).toMatch(/Backend action unavailable - fail closed/);
        expect(source).toMatch(/disabled=\{liveProviderActionDisabled\}/);
        expect(source).toMatch(/Local accounting only; no provider call attempted/);
        expect(source).toMatch(/no raw secrets/i);
    });

    it('launches only one backend-gated provider action after confirmation', () => {
        expect(stateSource).toMatch(/runGatedProviderAction/);
        expect(stateSource).toMatch(/DEFAULT_PROVIDER_ACTION_PROVIDER = '9router'/);
        expect(stateSource).toMatch(/DEFAULT_PROVIDER_ACTION_MODEL = 'qwen\/qwen3-coder'/);
        expect(stateSource).toMatch(/DEFAULT_PROVIDER_ACTION_PROMPT/);
        expect(stateSource).toMatch(/confirmProviderCall: liveProviderActionConfirmed/);
        expect(stateSource).toMatch(/allowPaidCalls: !dryRun && allowPaidCalls/);
        expect(source).toMatch(/disabled=\{liveProviderActionDisabled\}/);
        expect(stateSource).toMatch(/!providerActionAvailable/);
        expect(source).toMatch(/Run one backend-gated provider action/);
        expect(source).toMatch(/Narrow provider action gate/);
        expect(source).toMatch(/one narrow provider action, not provider-backed adoption or runtime support/i);
    });

    it('surfaces gated action result and accounting without raw secret display', () => {
        expect(source).toMatch(/arc-studio-config__provider-action-result/);
        expect(source).toMatch(/success=\{String\(providerActionResult\.success\)\}/);
        expect(source).toMatch(/blocked=\{String\(providerActionResult\.blocked\)\}/);
        expect(source).toMatch(/dryRun=\{String\(providerActionResult\.dryRun\)\}/);
        expect(source).toMatch(/providerCall=\{String\(providerActionResult\.providerCall\)\}/);
        expect(source).toMatch(/raw keys are never displayed/i);
        expect(combined).not.toMatch(/apiKey|secretKey|rawKey/);
        expect(combined).not.toMatch(/provider-backed adoption (ready|enabled|supported)/i);
    });
});
