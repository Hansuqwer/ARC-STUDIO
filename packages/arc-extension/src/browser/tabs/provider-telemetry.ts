export interface ProviderDiagnosticsSummary {
    liveTestsEnabled: boolean;
    routingDefault: string;
    configuredProvidersCount: number;
    configuredAccountsCount: number;
    providers: string[];
    accounts: string[];
}

export interface QuotaCounterRow {
    key: string;
    bucket: 'dry_run' | 'live';
    scope: 'provider' | 'account';
    id: string;
    count: number;
}

export interface ProfileCostPolicySummary {
    label: string;
    dryRun: boolean;
    paidCallsAllowed: boolean;
    paidCallsBlocked: boolean;
    liveCallsGated: boolean;
    enforcement: 'informational' | 'enforced';
    enforced: boolean;
    dryRunHardBlock: boolean;
}

export interface QuotaResetConfirmationInput {
    confirmationText?: string;
}

export interface QuotaResetConfirmationState {
    requiredPhrase: string;
    confirmed: boolean;
    disabledReason: string;
    warning: string;
    localOnly: boolean;
}

export interface LiveProviderGateInput {
    dryRun: boolean;
    allowPaidCalls: boolean;
    liveTestsEnabled: boolean;
    profile?: unknown;
}

export interface LiveProviderGateState {
    state: 'blocked' | 'gated' | 'preview';
    reasons: string[];
    cta: string;
    enforcement: string;
    message: string;
    providerCall: false;
}

const QUOTA_COUNTER_KEY = /^(dry_run|live):(provider|account):([A-Za-z0-9_.:-]+)$/;
const QUOTA_RESET_CONFIRMATION_PHRASE = 'RESET LOCAL PROVIDER QUOTA';

export function parseProviderDiagnostics(value: unknown): ProviderDiagnosticsSummary {
    const object = asRecord(value);
    const providers = stringArray(firstValue(object, ['providers', 'configured_providers', 'configuredProviders']));
    const accounts = stringArray(firstValue(object, ['accounts', 'configured_accounts', 'configuredAccounts']));

    return {
        liveTestsEnabled: booleanValue(firstValue(object, ['live_tests_enabled', 'liveTestsEnabled', 'liveTests'])),
        routingDefault: stringValue(
            firstValue(object, ['routing_default', 'routingDefault', 'default_provider', 'defaultProvider'])
        ),
        configuredProvidersCount: numberValue(
            firstValue(object, ['configured_providers_count', 'configuredProvidersCount']),
            providers.length
        ),
        configuredAccountsCount: numberValue(
            firstValue(object, ['configured_accounts_count', 'configuredAccountsCount']),
            accounts.length
        ),
        providers,
        accounts,
    };
}

export function parseQuotaCounters(value: unknown): QuotaCounterRow[] {
    const object = asRecord(value) ?? {};
    const quotaObject = asRecord(object.quota);
    const counters = asRecord(quotaObject?.counters) ?? asRecord(object.counters) ?? object;

    return Object.entries(counters).flatMap(([key, count]) => {
        const match = QUOTA_COUNTER_KEY.exec(key);
        if (!match || typeof count !== 'number' || !Number.isFinite(count)) {
            return [];
        }
        return [
            {
                key,
                bucket: match[1] as 'dry_run' | 'live',
                scope: match[2] as 'provider' | 'account',
                id: match[3],
                count,
            },
        ];
    });
}

export function canResetQuota(value: unknown): boolean {
    return parseQuotaCounters(value).length > 0;
}

export function summarizeProfileCostPolicy(
    profile: unknown,
    dryRun: boolean,
    allowPaidCalls: boolean,
    enforced = false
): ProfileCostPolicySummary {
    const object = asRecord(profile);
    const name = stringValue(firstValue(object, ['name', 'profile', 'id'])) || 'current profile';
    const paidCallsAllowed = !dryRun && allowPaidCalls;
    const paidCallsBlocked = dryRun || !allowPaidCalls;
    const liveCallsGated = dryRun || !allowPaidCalls;
    const enforcement = enforced ? 'enforced' : 'informational';
    const enforcementLabel = enforced ? 'backend-enforced opt-in' : 'advisory UI preview; not enforcement';
    const label = dryRun
        ? `${name}: dry-run/offline hard-blocks paid/live provider calls (${enforcementLabel})`
        : paidCallsAllowed
          ? `${name}: paid/live provider calls explicitly allowed (${enforcementLabel})`
          : `${name}: paid/live provider calls gated (${enforcementLabel})`;

    return {
        label,
        dryRun,
        paidCallsAllowed,
        paidCallsBlocked,
        liveCallsGated,
        enforcement,
        enforced,
        dryRunHardBlock: dryRun,
    };
}

export function buildQuotaResetConfirmation(
    input: QuotaResetConfirmationInput = {}
): QuotaResetConfirmationState {
    const confirmationText = typeof input.confirmationText === 'string' ? input.confirmationText.trim() : '';
    const confirmed = confirmationText === QUOTA_RESET_CONFIRMATION_PHRASE;
    return {
        requiredPhrase: QUOTA_RESET_CONFIRMATION_PHRASE,
        confirmed,
        disabledReason: confirmed ? '' : `Type ${QUOTA_RESET_CONFIRMATION_PHRASE} to enable local-only reset`,
        warning:
            'Resets local ARC provider quota counters only; no provider execution, billing action, remote quota change, or provider network call occurs.',
        localOnly: true,
    };
}

export function buildLiveProviderGate(input: LiveProviderGateInput): LiveProviderGateState {
    const profile = asRecord(input.profile);
    const name = stringValue(firstValue(profile, ['name', 'profile', 'id'])) || 'current profile';
    const reasons: string[] = [];
    const dryRun = input.dryRun === true;
    const allowPaidCalls = input.allowPaidCalls === true;
    const liveTestsEnabled = input.liveTestsEnabled === true;

    if (dryRun) {
        reasons.push('dry-run is enabled; live provider calls are hard-blocked');
    }
    if (!allowPaidCalls) {
        reasons.push('paid/live provider calls are not explicitly allowed');
    }
    if (!liveTestsEnabled) {
        reasons.push('live provider tests are disabled');
    }

    const state = dryRun ? 'blocked' : reasons.length > 0 ? 'gated' : 'preview';
    const cta =
        state === 'preview'
            ? `${name}: local/offline preview gates satisfied; provider execution remains disabled here`
            : state === 'blocked'
              ? `${name}: disable dry-run before local backend-gated preview can proceed`
              : `${name}: satisfy all gates before local backend-gated preview can proceed`;
    const message = reasons.length > 0
        ? `Local/offline quota/cost preview only; blocked by ${reasons.join('; ')}.`
        : 'Local/offline quota/cost preview only; no provider execution is enabled by this state.';
    const enforcement = 'backend-enforced opt-in; UI remains preview/offline and never enables provider execution';

    return { state, reasons, cta, enforcement, message, providerCall: false };
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        return undefined;
    }
    return value as Record<string, unknown>;
}

function firstValue(object: Record<string, unknown> | undefined, keys: string[]): unknown {
    if (!object) {
        return undefined;
    }
    return keys.find(key => object[key] !== undefined) ? object[keys.find(key => object[key] !== undefined)!] : undefined;
}

function booleanValue(value: unknown): boolean {
    return value === true;
}

function numberValue(value: unknown, fallback: number): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function stringValue(value: unknown): string {
    return typeof value === 'string' ? value : '';
}

function stringArray(value: unknown): string[] {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.filter((item): item is string => typeof item === 'string');
}
