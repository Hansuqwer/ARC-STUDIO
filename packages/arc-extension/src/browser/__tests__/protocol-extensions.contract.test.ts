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

        it('should expose profile and isolation service methods', () => {
            expect(source).toMatch(/export interface ArcProfileInfo/);
            expect(source).toMatch(/export interface IsolationStatus/);
            expect(source).toMatch(/export interface IsolationProviderInfo/);
            expect(source).toMatch(/listProfiles\(\):\s*Promise<ArcProfileInfo\[\]>/);
            expect(source).toMatch(/getIsolationStatus\(\):\s*Promise<IsolationStatus>/);
            expect(source).toMatch(/listIsolationProviders\(\):\s*Promise<IsolationProviderInfo\[\]>/);
        });

        it('should export provider catalog and key-ref protocol types', () => {
            expect(source).toMatch(/export interface ProviderCatalogEntry/);
            expect(source).toMatch(/export interface ProviderKeyRefRequest/);
            expect(source).toMatch(/ProviderAuthKind/);
        });

        it('should expose provider catalog and key-ref service methods', () => {
            expect(source).toMatch(/getProviderCatalog\(\):\s*Promise<ProviderCatalogEntry\[\]>/);
            expect(source).toMatch(/setProviderKeyRef\(request:\s*ProviderKeyRefRequest\)/);
            expect(source).toMatch(/unsetProviderKeyRef\(providerOrAccountId:\s*string\)/);
        });

        it('should export provider diagnostics and quota protocol types', () => {
            expect(source).toMatch(/export interface ProviderDiagnosticsInfo/);
            expect(source).toMatch(/export interface ProviderQuotaInfo/);
            expect(source).toMatch(/export interface ProviderQuotaResetResult/);
            expect(source).toMatch(/success:\s*boolean/);
            expect(source).toMatch(/message:\s*string/);
            expect(source).toMatch(/providers\?:\s*Record<string, unknown>\[\]/);
            expect(source).toMatch(/routing\?:\s*Record<string, unknown>/);
            expect(source).toMatch(/accounts\?:\s*Record<string, unknown>\[\]/);
            expect(source).toMatch(/quota\?:\s*Record<string, unknown>/);
            expect(source).toMatch(/counters\?:\s*Record<string, unknown>/);
        });

        it('should expose provider diagnostics and quota service methods', () => {
            expect(source).toMatch(/getProviderDiagnostics\(\):\s*Promise<ProviderDiagnosticsInfo>/);
            expect(source).toMatch(/getProviderQuota\(provider\?:\s*string\):\s*Promise<ProviderQuotaInfo>/);
            expect(source).toMatch(/resetProviderQuota\(\):\s*Promise<ProviderQuotaResetResult>/);
        });

        it('should export run preflight protocol types', () => {
            expect(source).toMatch(/export interface RunPreflightRequest/);
            expect(source).toMatch(/export interface RunPreflightResponse/);
            expect(source).toMatch(/export interface RunBlocker/);
            expect(source).toMatch(/export interface StartRunRequest/);
            expect(source).toMatch(/export interface StartRunResponse/);
        });

        it('should expose preflightRun service method', () => {
            expect(source).toMatch(/preflightRun\(request:\s*RunPreflightRequest\):\s*Promise<RunPreflightResponse>/);
            expect(source).toMatch(/startRun\(request:\s*StartRunRequest\):\s*Promise<StartRunResponse>/);
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

    describe('HITL/Audit/Replay Types (Slice 7)', () => {
        it('should allow known and runtime-specific trace event type strings', () => {
            expect(source).toMatch(/export type KnownTraceEventType/);
            expect(source).toMatch(/type:\s*KnownTraceEventType \| \(string & \{\}\)/);
        });

        it('should export HitlPromptInfo', () => {
            expect(source).toMatch(/export interface HitlPromptInfo/);
        });

        it('should have HitlPromptInfo with promptId, runId, prompt fields', () => {
            expect(source).toMatch(/HitlPromptInfo/);
            expect(source).toMatch(/promptId:\s*string/);
            expect(source).toMatch(/runId:\s*string/);
            expect(source).toMatch(/prompt:\s*string/);
        });

        it('should have optional HITL status expiry and single-use fields', () => {
            expect(source).toMatch(/status\?:\s*'pending' \| 'approved' \| 'rejected' \| 'modified' \| 'expired' \| 'used' \| 'unknown'/);
            expect(source).toMatch(/expired\?:\s*boolean/);
            expect(source).toMatch(/singleUse\?:\s*boolean/);
            expect(source).toMatch(/usedAt\?:\s*string/);
        });

        it('should export HitlRespondRequest', () => {
            expect(source).toMatch(/export interface HitlRespondRequest/);
        });

        it('should have HitlRespondRequest with promptId and decision', () => {
            expect(source).toMatch(/HitlRespondRequest/);
            expect(source).toMatch(/promptId:\s*string/);
            expect(source).toMatch(/decision:\s*'approve'\s*\|\s*'reject'\s*\|\s*'modify'/);
            expect(source).toMatch(/token:\s*string/);
        });

        it('should export AuditChainInfo', () => {
            expect(source).toMatch(/export interface AuditChainInfo/);
        });

        it('should have AuditChainInfo with chainVerified, recordCount, signature', () => {
            expect(source).toMatch(/AuditChainInfo/);
            expect(source).toMatch(/chainVerified:\s*boolean/);
            expect(source).toMatch(/recordCount:\s*number/);
            expect(source).toMatch(/signature/);
        });

        it('should have optional audit state and reason fields', () => {
            expect(source).toMatch(/state\?:\s*'present' \| 'missing' \| 'degraded'/);
            expect(source).toMatch(/reason\?:\s*string/);
        });

        it('should export ReplayResult', () => {
            expect(source).toMatch(/export interface ReplayResult/);
        });

        it('should have ReplayResult with runId, events, totalEvents', () => {
            expect(source).toMatch(/ReplayResult/);
            expect(source).toMatch(/runId:\s*string/);
            expect(source).toMatch(/events:\s*ReplayEvent\[\]/);
            expect(source).toMatch(/totalEvents:\s*number/);
        });

        it('should have optional replay category annotations and metadata fields', () => {
            expect(source).toMatch(/category\?:\s*'lifecycle' \| 'message' \| 'tool' \| 'error' \| 'hitl' \| 'audit' \| 'unknown'/);
            expect(source).toMatch(/annotations\?:\s*string\[\]/);
            expect(source).toMatch(/metadata\?:\s*Record<string, unknown>/);
        });

        it('should have ArcService HITL/audit/replay methods', () => {
            expect(source).toMatch(/listPendingHitlPrompts\(\):\s*Promise<HitlPromptInfo\[\]>/);
            expect(source).toMatch(/respondHitlPrompt\(request:\s*HitlRespondRequest\)/);
            expect(source).toMatch(/getAuditChainInfo\(runId:\s*string\)/);
            expect(source).toMatch(/replayRun\(runId:\s*string\):\s*Promise<ReplayResult>/);
        });

        it('should expose run diff protocol types and method', () => {
            expect(source).toMatch(/export interface RunDiffResult/);
            expect(source).toMatch(/runAId:\s*string/);
            expect(source).toMatch(/typesOnlyInA:\s*string\[\]/);
            expect(source).toMatch(/errorEventsA:\s*Record<string, unknown>\[\]/);
            expect(source).toMatch(/toolCallsA:\s*number/);
            expect(source).toMatch(/diffRuns\(runAId:\s*string,\s*runBId:\s*string\):\s*Promise<RunDiffResult>/);
        });

        it('should expose active stream protocol types and methods', () => {
            expect(source).toMatch(/export type ActiveTraceStreamMode\s*=\s*'live'\s*\|\s*'replay'/);
            expect(source).toMatch(/export interface ActiveTraceStreamRequest/);
            expect(source).toMatch(/export interface ActiveTraceStreamStatus/);
            expect(source).toMatch(/export interface ActiveTraceEventChunk/);
            expect(source).toMatch(/RUN_COMPLETED/);
            expect(source).toMatch(/RUN_FAILED/);
            expect(source).toMatch(/RUN_CANCELLED/);
            expect(source).toMatch(/STREAM_END/);
            expect(source).toMatch(/state:\s*ActiveTraceStreamState/);
            expect(source).toMatch(/streamActiveTrace\(request:\s*ActiveTraceStreamRequest\)/);
            expect(source).toMatch(/cancelActiveTraceStream\(runId:\s*string\)/);
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
            expect(source).toMatch(/SAFE_CONFIG_KEYS/);
            expect(source).toMatch(/UNSAFE_CONFIG_KEY_PATTERN/);
            expect(source).toMatch(/Rejected unsafe config field/);
        });

        it('should allow only non-secret config fields including isolation dryRun paid routing', () => {
            expect(source).toMatch(/'defaultRuntime'/);
            expect(source).toMatch(/'mode'/);
            expect(source).toMatch(/'isolation'/);
            expect(source).toMatch(/'allowPaidCalls'/);
            expect(source).toMatch(/'dryRun'/);
            expect(source).toMatch(/'routingMode'/);
            expect(source).toMatch(/execution\.isolation/);
            expect(source).toMatch(/execution\.allow_paid_calls/);
            expect(source).toMatch(/providers\.dry_run/);
            expect(source).toMatch(/providers\.routing_mode/);
        });

        it('should NOT pass raw secret values to CLI', () => {
            expect(source).not.toMatch(/api_key\s*=\s*['"]/);
            expect(source).not.toMatch(/secret\s*:\s*['"]/);
            expect(source).not.toMatch(/password\s*=\s*['"]/);
            expect(source).not.toMatch(/rawKey/);
            expect(source).not.toMatch(/rawApiKey/);
        });

        it('should call provider catalog and key-ref CLI commands', () => {
            expect(source).toMatch(/providers.*catalog.*--json/);
            expect(source).toMatch(/providers.*key.*set/);
            expect(source).toMatch(/providers.*key.*unset/);
        });

        it('should implement provider diagnostics and quota CLI methods', () => {
            expect(source).toMatch(/async getProviderDiagnostics\(\)/);
            expect(source).toMatch(/providers.*diagnostics.*--json/);
            expect(source).toMatch(/async getProviderQuota\(provider\?:\s*string\)/);
            expect(source).toMatch(/providers.*quota.*show/);
            expect(source).toMatch(/async resetProviderQuota\(\)/);
            expect(source).toMatch(/\['providers', 'quota', 'reset', '--json'\]/);
            expect(source).toMatch(/--provider/);
            expect(source).toMatch(/Provider diagnostics unavailable/);
            expect(source).toMatch(/Provider quota unavailable/);
            expect(source).toMatch(/Provider quota reset unavailable/);
        });

        it('should implement dry-run preflight via CLI without provider calls', () => {
            expect(source).toMatch(/async preflightRun\(request:\s*RunPreflightRequest\)/);
            expect(source).toMatch(/--dry-run/);
            expect(source).toMatch(/providerCall:\s*false/);
        });

        it('should implement profile and isolation CLI JSON methods with safe fallback', () => {
            expect(source).toMatch(/async listProfiles\(\)/);
            expect(source).toMatch(/profiles.*list.*--json/);
            expect(source).toMatch(/local-safe/);
            expect(source).toMatch(/async getIsolationStatus\(\)/);
            expect(source).toMatch(/isolation.*status.*--json/);
            expect(source).toMatch(/async listIsolationProviders\(\)/);
            expect(source).toMatch(/isolation.*list.*--json/);
            expect(source).toMatch(/mapIsolationProviders/);
        });

        it('should implement startRun via CLI JSON output', () => {
            expect(source).toMatch(/async startRun\(request:\s*StartRunRequest\)/);
            expect(source).toMatch(/tracePath:\s*data\.metadata\?\.trace_path/);
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

        it('should import provider diagnostics and quota types', () => {
            expect(source).toMatch(/ProviderDiagnosticsInfo/);
            expect(source).toMatch(/ProviderQuotaInfo/);
        });

        it('should import SafeConfigUpdate', () => {
            expect(source).toMatch(/SafeConfigUpdate/);
        });

        it('should import RunLinksResponse', () => {
            expect(source).toMatch(/RunLinksResponse/);
        });

        it('should import HitlPromptInfo, HitlRespondRequest, AuditChainInfo, ReplayResult', () => {
            expect(source).toMatch(/HitlPromptInfo/);
            expect(source).toMatch(/HitlRespondRequest/);
            expect(source).toMatch(/AuditChainInfo/);
            expect(source).toMatch(/ReplayResult/);
            expect(source).toMatch(/ReplayEvent/);
            expect(source).toMatch(/ActiveTraceStreamRequest/);
            expect(source).toMatch(/ActiveTraceEventChunk/);
        });
    });

    describe('HITL/Audit/Replay methods', () => {
        it('should implement listPendingHitlPrompts', () => {
            expect(source).toMatch(/async listPendingHitlPrompts\(\)/);
        });

        it('should call arc hitl pending CLI', () => {
            expect(source).toMatch(/hitl.*pending.*--json/);
        });

        it('should implement respondHitlPrompt', () => {
            expect(source).toMatch(/async respondHitlPrompt\(request:\s*HitlRespondRequest\)/);
        });

        it('should call arc hitl respond CLI', () => {
            expect(source).toMatch(/hitl/);
            expect(source).toMatch(/respond/);
            expect(source).toMatch(/--token/);
        });

        it('should implement getAuditChainInfo', () => {
            expect(source).toMatch(/async getAuditChainInfo\(runId:\s*string\)/);
        });

        it('should call arc runs status to get audit path', () => {
            expect(source).toMatch(/runs.*status/);
            expect(source).toMatch(/audit_path/);
        });

        it('should call arc audit verify CLI', () => {
            expect(source).toMatch(/audit.*verify/);
            expect(source).toMatch(/--chain/);
        });

        it('should implement replayRun', () => {
            expect(source).toMatch(/async replayRun\(runId:\s*string\)/);
        });

        it('should call arc runs replay CLI', () => {
            expect(source).toMatch(/runs.*replay.*--json/);
        });

        it('should map Python snake_case to camelCase for replay events', () => {
            expect(source).toMatch(/run_id/);
            expect(source).toMatch(/runId/);
        });

        it('should map missing and degraded audit states with reason', () => {
            expect(source).toMatch(/state:\s*'missing'/);
            expect(source).toMatch(/reason:\s*'No audit path recorded for this run\.'/);
            expect(source).toMatch(/state:\s*data\.state \|\| \(chainVerified \? 'present' : 'degraded'\)/);
            expect(source).toMatch(/state:\s*'degraded'/);
            expect(source).toMatch(/reason:\s*parsed\?\.error\?\.message \|\| 'Audit verification returned no data\.'/);
        });

        it('should map replay category annotations and metadata', () => {
            expect(source).toMatch(/category:\s*ev\.category \|\| ev\.event_category \|\| ev\.eventCategory \|\| this\.replayCategoryForType\(ev\.type\)/);
            expect(source).toMatch(/annotations:\s*ev\.annotations \|\| ev\.notes/);
            expect(source).toMatch(/metadata:\s*ev\.metadata \|\| ev\.meta/);
            expect(source).toMatch(/annotations:\s*data\.annotations \|\| data\.notes/);
            expect(source).toMatch(/metadata:\s*data\.metadata \|\| data\.meta/);
        });

        it('should implement run diff via CLI with validation and snake-case mapping', () => {
            expect(source).toMatch(/async diffRuns\(runAId:\s*string,\s*runBId:\s*string\)/);
            expect(source).toMatch(/validateRunId\(runAId\)/);
            expect(source).toMatch(/validateRunId\(runBId\)/);
            expect(source).toMatch(/runs.*diff.*--json/);
            expect(source).toMatch(/run_a_id/);
            expect(source).toMatch(/types_only_in_a/);
            expect(source).toMatch(/typesOnlyInA/);
        });

        it('should implement active trace stream with replay and disconnected live semantics', () => {
            expect(source).toMatch(/async streamActiveTrace\(request:\s*ActiveTraceStreamRequest\)/);
            expect(source).toMatch(/async cancelActiveTraceStream\(runId:\s*string\)/);
            expect(source).toMatch(/createActiveTraceIterable/);
            expect(source).toMatch(/this\.replayRun\(request\.runId\)/);
            expect(source).toMatch(/Live SSE proxy is disconnected/);
            expect(source).toMatch(/RUN_CANCELLED/);
            expect(source).toMatch(/Stream timed out/);
        });
    });
});
