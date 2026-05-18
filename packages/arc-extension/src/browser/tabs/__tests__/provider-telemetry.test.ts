import {
    buildLiveProviderGate,
    buildQuotaResetConfirmation,
    canResetQuota,
    parseProviderDiagnostics,
    parseQuotaCounters,
    summarizeProfileCostPolicy,
} from '../provider-telemetry';

describe('provider telemetry helpers', () => {
    it('parses provider diagnostics aliases', () => {
        expect(
            parseProviderDiagnostics({
                live_tests_enabled: true,
                routing_default: 'openai',
                configured_providers: ['openai', 'anthropic', 7],
                configured_accounts: ['acct-1'],
            })
        ).toEqual({
            liveTestsEnabled: true,
            routingDefault: 'openai',
            configuredProvidersCount: 2,
            configuredAccountsCount: 1,
            providers: ['openai', 'anthropic'],
            accounts: ['acct-1'],
        });

        expect(
            parseProviderDiagnostics({
                liveTests: true,
                defaultProvider: 'anthropic',
                configuredProvidersCount: 3,
                configuredAccountsCount: 4,
            })
        ).toMatchObject({
            liveTestsEnabled: true,
            routingDefault: 'anthropic',
            configuredProvidersCount: 3,
            configuredAccountsCount: 4,
        });
    });

    it('handles malformed diagnostics safely', () => {
        expect(parseProviderDiagnostics(null)).toEqual({
            liveTestsEnabled: false,
            routingDefault: '',
            configuredProvidersCount: 0,
            configuredAccountsCount: 0,
            providers: [],
            accounts: [],
        });

        expect(parseProviderDiagnostics({
            live_tests_enabled: 'true',
            routing_default: 12,
            configured_providers: 'openai',
            configured_accounts_count: Number.POSITIVE_INFINITY,
        })).toEqual({
            liveTestsEnabled: false,
            routingDefault: '',
            configuredProvidersCount: 0,
            configuredAccountsCount: 0,
            providers: [],
            accounts: [],
        });
    });

    it('parses nested quota counters and ignores invalid/non-number values', () => {
        expect(
            parseQuotaCounters({
                quota: {
                    counters: {
                        'dry_run:provider:openai': 3,
                        'live:account:acct-1': 7,
                        'live:provider:anthropic': '4',
                        'bad:provider:openai': 1,
                        'dry_run:account:acct-2': Number.NaN,
                    },
                },
            })
        ).toEqual([
            { key: 'dry_run:provider:openai', bucket: 'dry_run', scope: 'provider', id: 'openai', count: 3 },
            { key: 'live:account:acct-1', bucket: 'live', scope: 'account', id: 'acct-1', count: 7 },
        ]);
    });

    it('parses flat counters payloads', () => {
        expect(
            parseQuotaCounters({
                counters: {
                    'dry_run:provider:openai': 1,
                },
            })
        ).toEqual([
            { key: 'dry_run:provider:openai', bucket: 'dry_run', scope: 'provider', id: 'openai', count: 1 },
        ]);
    });

    it('returns no quota rows for malformed or partial telemetry', () => {
        expect(parseQuotaCounters(null)).toEqual([]);
        expect(parseQuotaCounters([])).toEqual([]);
        expect(parseQuotaCounters({ quota: null })).toEqual([]);
        expect(parseQuotaCounters({ quota: { counters: ['dry_run:provider:openai'] } })).toEqual([]);
        expect(parseQuotaCounters({ quota: { counters: { 'dry_run:provider:openai': Infinity } } })).toEqual([]);
    });

    it('detects resettable quota only when valid counters exist', () => {
        expect(canResetQuota({ counters: { 'dry_run:provider:openai': 1 } })).toBe(true);
        expect(canResetQuota({ counters: { 'dry_run:provider:openai': '1' } })).toBe(false);
    });

    it('summarizes profile cost policy with dry-run paid-call blocking', () => {
        expect(summarizeProfileCostPolicy({ name: 'safe' }, true, true)).toEqual({
            label:
                'safe: dry-run/offline hard-blocks paid/live provider calls (backend-enforced opt-in; UI preview only)',
            dryRun: true,
            paidCallsAllowed: false,
            paidCallsBlocked: true,
            liveCallsGated: true,
            enforcement: 'informational',
            enforced: false,
            dryRunHardBlock: true,
        });

        expect(summarizeProfileCostPolicy({ id: 'prod' }, false, false)).toMatchObject({
            label: 'prod: paid/live provider calls gated (backend-enforced opt-in; UI preview only)',
            paidCallsAllowed: false,
            paidCallsBlocked: true,
            enforcement: 'informational',
            enforced: false,
        });
    });

    it('marks cost policy as enforced only when explicit flag is provided', () => {
        expect(summarizeProfileCostPolicy({ name: 'prod' }, false, true, true)).toMatchObject({
            label: 'prod: paid/live provider calls explicitly allowed (backend-enforced opt-in)',
            enforcement: 'enforced',
            enforced: true,
            dryRunHardBlock: false,
        });
    });

    it('requires exact quota reset confirmation phrase', () => {
        const empty = buildQuotaResetConfirmation();
        expect(empty).toMatchObject({
            requiredPhrase: 'RESET LOCAL PROVIDER QUOTA',
            confirmed: false,
            disabledReason: 'Type RESET LOCAL PROVIDER QUOTA to enable local reset',
        });

        expect(buildQuotaResetConfirmation({ confirmationText: 'reset local provider quota' })).toMatchObject({
            confirmed: false,
        });
        expect(buildQuotaResetConfirmation({ confirmationText: 'RESET LOCAL PROVIDER QUOTA' })).toMatchObject({
            confirmed: true,
            disabledReason: '',
        });
    });

    it('warns quota reset is local only with no provider execution or billing action', () => {
        expect(buildQuotaResetConfirmation().warning).toBe(
            'Resets local ARC provider quota counters only; no provider execution, billing action, or remote quota change occurs.'
        );
    });

    it('blocks live provider preview when dry-run is enabled', () => {
        expect(
            buildLiveProviderGate({
                dryRun: true,
                allowPaidCalls: true,
                liveTestsEnabled: true,
                profile: { name: 'safe' },
            })
        ).toEqual({
            state: 'blocked',
            reasons: ['dry-run is enabled; live provider calls are hard-blocked'],
            cta: 'safe: disable dry-run before local live-readiness preview can proceed',
            enforcement: 'backend-enforced opt-in; UI remains preview/offline and never enables provider execution',
            message:
                'Local/offline quota/cost preview only; blocked by dry-run is enabled; live provider calls are hard-blocked.',
            providerCall: false,
        });
    });

    it('gates live provider preview when paid calls are not allowed', () => {
        expect(
            buildLiveProviderGate({ dryRun: false, allowPaidCalls: false, liveTestsEnabled: true })
        ).toMatchObject({
            state: 'gated',
            reasons: ['paid/live provider calls are not explicitly allowed'],
            providerCall: false,
        });
    });

    it('gates live provider preview when live tests are disabled', () => {
        expect(
            buildLiveProviderGate({ dryRun: false, allowPaidCalls: true, liveTestsEnabled: false })
        ).toMatchObject({
            state: 'gated',
            reasons: ['live provider tests are disabled'],
            providerCall: false,
        });
    });

    it('never enables provider calls for live provider preview', () => {
        expect(
            buildLiveProviderGate({ dryRun: false, allowPaidCalls: true, liveTestsEnabled: true })
        ).toEqual({
            state: 'ready',
            reasons: [],
            cta: 'current profile: local/offline preview ready; provider execution remains disabled here',
            enforcement: 'backend-enforced opt-in; UI remains preview/offline and never enables provider execution',
            message: 'Local/offline quota/cost preview only; no provider execution is enabled by this state.',
            providerCall: false,
        });
    });

    it('keeps providerCall false across all gate combinations', () => {
        const bools = [false, true];
        for (const dryRun of bools) {
            for (const allowPaidCalls of bools) {
                for (const liveTestsEnabled of bools) {
                    expect(buildLiveProviderGate({ dryRun, allowPaidCalls, liveTestsEnabled }).providerCall).toBe(false);
                }
            }
        }
    });

    it('keeps ready-state text explicitly local and non-enabling', () => {
        const gate = buildLiveProviderGate({ dryRun: false, allowPaidCalls: true, liveTestsEnabled: true });

        expect(gate.providerCall).toBe(false);
        expect(gate.cta).toContain('provider execution remains disabled');
        expect(gate.message).toContain('no provider execution is enabled');
        expect(gate.enforcement).toContain('backend-enforced opt-in');
        expect(gate.enforcement).toContain('preview/offline');
        expect(gate.enforcement).toContain('never enables provider execution');
        expect(gate.enforcement).not.toContain('network');
        expect(gate.enforcement).not.toContain('API');
    });

    it('does not expose live execution enablement in any gate state', () => {
        const cases = [
            buildLiveProviderGate({ dryRun: true, allowPaidCalls: false, liveTestsEnabled: false }),
            buildLiveProviderGate({ dryRun: false, allowPaidCalls: false, liveTestsEnabled: false }),
            buildLiveProviderGate({ dryRun: false, allowPaidCalls: true, liveTestsEnabled: true }),
        ];

        for (const gate of cases) {
            expect(gate.providerCall).toBe(false);
            expect(`${gate.cta} ${gate.message} ${gate.enforcement}`).toContain('Local/offline');
            expect(`${gate.cta} ${gate.message} ${gate.enforcement}`).not.toMatch(/enable(s|d)? live provider execution/i);
        }
    });
});
