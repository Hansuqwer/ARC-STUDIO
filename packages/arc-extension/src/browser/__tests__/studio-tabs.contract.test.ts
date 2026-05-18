/**
 * Studio Tabs Contract Tests
 *
 * Static source-pattern tests for ChatTab, RunsTab, WorkflowsTab, AssuranceTab, ConfigTab.
 */

import * as fs from 'fs-extra';
import * as path from 'path';

describe('Studio Tabs Contracts', () => {
    const browserDir = path.join(__dirname, '..', '..', '..', 'src', 'browser');
    const tabsDir = path.join(__dirname, '..', '..', '..', 'src', 'browser', 'tabs');

    describe('tabs/index.ts exports', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'index.ts'), 'utf-8');
        });

        it('should export ChatTab', () => {
            expect(source).toMatch(/export.*ChatTab/);
        });

        it('should export ChatTabProps', () => {
            expect(source).toMatch(/export.*ChatTabProps/);
        });

        it('should export RunsTab', () => {
            expect(source).toMatch(/export.*RunsTab/);
        });

        it('should export RunsTabProps', () => {
            expect(source).toMatch(/export.*RunsTabProps/);
        });

        it('should export WorkflowsTab', () => {
            expect(source).toMatch(/export.*WorkflowsTab/);
        });

        it('should export WorkflowsTabProps', () => {
            expect(source).toMatch(/export.*WorkflowsTabProps/);
        });

        it('should export ConfigTab', () => {
            expect(source).toMatch(/export.*ConfigTab/);
        });

        it('should export ConfigTabProps', () => {
            expect(source).toMatch(/export.*ConfigTabProps/);
        });

        it('should export AssuranceTab and AssuranceTabProps', () => {
            expect(source).toMatch(/export.*AssuranceTab/);
            expect(source).toMatch(/export.*AssuranceTabProps/);
        });
    });

    describe('ChatTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'ChatTab.tsx'), 'utf-8');
        });

        it('should export ChatTabProps interface', () => {
            expect(source).toMatch(/export interface ChatTabProps/);
        });

        it('should have chat input field', () => {
            expect(source).toMatch(/arc-studio-chat__input/);
            expect(source).toMatch(/arc-studio-chat__input-field/);
        });

        it('should have mode indicator', () => {
            expect(source).toMatch(/arc-studio-chat__mode/);
            expect(source).toMatch(/Mode:/);
        });

        it('should have send button', () => {
            expect(source).toMatch(/arc-studio-chat__send/);
            expect(source).toMatch(/Send/);
        });

        it('should cycle through plan/build/auto modes', () => {
            expect(source).toMatch(/plan/);
            expect(source).toMatch(/build/);
            expect(source).toMatch(/auto/);
            expect(source).toMatch(/cycleMode/);
        });

        it('should have placeholder text', () => {
            expect(source).toMatch(/arc-studio-chat__placeholder/);
        });

        it('should load runtime capabilities for disabled selector states', () => {
            expect(source).toMatch(/listRuntimeCapabilities/);
            expect(source).toMatch(/FALLBACK_RUNTIMES/);
            expect(source).toMatch(/runtimeOptions/);
        });

        it('should disable runtime select option when can_run is false and show reason', () => {
            expect(source).toMatch(/disabled=\{disabled\}/);
            expect(source).toMatch(/\.reason/);
        });

        it('should expose runtime/profile selectors and dry-run preflight', () => {
            expect(source).toMatch(/arc-studio-chat__runtime-selector/);
            expect(source).toMatch(/arc-studio-chat__profile-selector/);
            expect(source).toMatch(/arc-studio-chat__paid-calls/);
            expect(source).toMatch(/allowPaidCalls/);
            expect(source).toMatch(/arc-studio-chat__dry-run/);
            expect(source).toMatch(/preflightRun/);
            expect(source).toMatch(/arc-studio-chat__run/);
            expect(source).toMatch(/startRun/);
        });

        it('should show paid-call gate warning from capability, preflight, or opt-in', () => {
            expect(source).toMatch(/arc-studio-chat__paid-call-warning/);
            expect(source).toMatch(/showPaidCallWarning/);
            expect(source).toMatch(/selectedCapability\?\.requires_paid_calls/);
            expect(source).toMatch(/preflight\?\.paidCallRequired/);
            expect(source).toMatch(/allowPaidCalls/);
            expect(source).toMatch(/Paid provider calls require explicit opt-in/);
            expect(source).toMatch(/Dry-run preflight makes no provider calls \(providerCall:false\)/);
            expect(source).not.toMatch(/api[_-]?key/i);
            expect(source).not.toMatch(/secret/i);
        });

        it('should show runtime readiness and keep local transcript', () => {
            expect(source).toMatch(/arc-studio-chat__runtime-readiness/);
            expect(source).toMatch(/selectedCapability/);
            expect(source).toMatch(/arc-studio-chat__transcript/);
            expect(source).toMatch(/setTranscript/);
        });

        it('should include CrewAI plus SwarmGraph fake offline option', () => {
            expect(source).toMatch(/crewai\+swarmgraph/);
            expect(source).toMatch(/CrewAI \+ SwarmGraph \(fake\/offline\)/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('RunsTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'RunsTab.tsx'), 'utf-8');
        });

        it('should export RunsTabProps interface', () => {
            expect(source).toMatch(/export interface RunsTabProps/);
        });

        it('should accept arcService prop', () => {
            expect(source).toMatch(/arcService:\s*ArcService/);
        });

        it('should have refresh button', () => {
            expect(source).toMatch(/arc-studio-runs__refresh/);
            expect(source).toMatch(/Refresh/);
        });

        it('should have placeholder', () => {
            expect(source).toMatch(/arc-studio-runs__placeholder/);
            expect(source).toMatch(/No runs yet/);
        });

        it('should have hint text', () => {
            expect(source).toMatch(/arc-studio-runs__hint/);
        });

        it('should have run list items with status badges', () => {
            expect(source).toMatch(/arc-studio-runs__item/);
            expect(source).toMatch(/arc-studio-runs__item-status/);
        });

        it('should have detail panel', () => {
            expect(source).toMatch(/arc-studio-runs__detail/);
            expect(source).toMatch(/arc-studio-runs__detail-placeholder/);
        });

        it('should import RunReceiptCard', () => {
            expect(source).toMatch(/RunReceiptCard/);
        });

        it('should import FailureAutopsyCard', () => {
            expect(source).toMatch(/FailureAutopsyCard/);
        });

        it('should import RunContractCard', () => {
            expect(source).toMatch(/RunContractCard/);
        });

        it('should use React.useState and React.useEffect', () => {
            expect(source).toMatch(/React\.useState/);
            expect(source).toMatch(/React\.useEffect/);
            expect(source).toMatch(/React\.useCallback/);
        });

        it('should call getTraces, getRunReceipt, getRunAutopsy, getRunContract', () => {
            expect(source).toMatch(/arcService\.getTraces/);
            expect(source).toMatch(/arcService\.getRunReceipt/);
            expect(source).toMatch(/arcService\.getRunAutopsy/);
            expect(source).toMatch(/arcService\.getRunContract/);
        });

        it('should expose run diff controls backed by ArcService.diffRuns', () => {
            expect(source).toMatch(/RunDiffResult/);
            expect(source).toMatch(/diffRunAId/);
            expect(source).toMatch(/diffRunBId/);
            expect(source).toMatch(/arcService\.diffRuns\(state\.diffRunAId, state\.diffRunBId\)/);
            expect(source).toMatch(/arc-studio-runs__diff-compare/);
            expect(source).toMatch(/JSON\.stringify\(diffResult, null, 2\)/);
            expect(source).not.toMatch(/fetch\(/);
            expect(source).not.toMatch(/arc-core/);
        });

        it('should render receipt card conditionally', () => {
            expect(source).toMatch(/receipt\s*&&\s*\(/);
            expect(source).toMatch(/<RunReceiptCard/);
        });

        it('should render autopsy card when available', () => {
            expect(source).toMatch(/autopsy/);
            expect(source).not.toMatch(/selectedRun\?\.status\s*===\s*'failed'/);
        });

        it('should tolerate missing run detail artifacts', () => {
            expect(source).toMatch(/getRunReceipt\(runId\)\.catch\(\(\) => null\)/);
            expect(source).toMatch(/getRunAutopsy\(runId\)\.catch\(\(\) => null\)/);
            expect(source).toMatch(/getRunContract\(runId\)\.catch\(\(\) => null\)/);
        });

        it('should render contract card conditionally', () => {
            expect(source).toMatch(/contract\s*&&\s*\(/);
            expect(source).toMatch(/<RunContractCard/);
        });

        it('should handle loading state', () => {
            expect(source).toMatch(/Loading runs…/);
            expect(source).toMatch(/Loading run details…/);
        });

        it('should handle error state', () => {
            expect(source).toMatch(/arc-studio-runs__error/);
        });

        it('should have layout container', () => {
            expect(source).toMatch(/arc-studio-runs__layout/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('WorkflowsTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'WorkflowsTab.tsx'), 'utf-8');
        });

        it('should export WorkflowsTabProps interface', () => {
            expect(source).toMatch(/export interface WorkflowsTabProps/);
        });

        it('should have workflows prop', () => {
            expect(source).toMatch(/workflows:\s*WorkflowInfo\[\]/);
        });

        it('should have isScanning prop', () => {
            expect(source).toMatch(/isScanning:\s*boolean/);
        });

        it('should have onScanWorkspace prop', () => {
            expect(source).toMatch(/onScanWorkspace/);
        });

        it('should have scan button', () => {
            expect(source).toMatch(/arc-studio-workflows__scan/);
            expect(source).toMatch(/Scan/);
        });

        it('should render workflow cards', () => {
            expect(source).toMatch(/arc-studio-workflows__card/);
        });

        it('should render workflow badges', () => {
            expect(source).toMatch(/arc-studio-workflows__badge/);
        });

        it('should have placeholder when no workflows', () => {
            expect(source).toMatch(/arc-studio-workflows__placeholder/);
            expect(source).toMatch(/No workflows detected/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('ConfigTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'ConfigTab.tsx'), 'utf-8');
        });

        it('should export ConfigTabProps interface', () => {
            expect(source).toMatch(/export interface ConfigTabProps/);
        });

        it('should have runtime radio group', () => {
            expect(source).toMatch(/type='radio'/);
            expect(source).toMatch(/name='runtime'/);
        });

        it('should have runtime display metadata for known runtimes', () => {
            expect(source).toMatch(/RUNTIME_DISPLAY/);
            expect(source).toMatch(/swarmgraph/);
            expect(source).toMatch(/langgraph/);
            expect(source).toMatch(/crewai/);
            expect(source).toMatch(/crewai\+swarmgraph/);
            expect(source).toMatch(/openai-agents/);
            expect(source).toMatch(/ag2/);
        });

        it('should load runtime capabilities from backend for disabled state', () => {
            expect(source).toMatch(/listRuntimeCapabilities/);
            expect(source).toMatch(/caps\.runtimes/);
        });

        it('should disable runtime radio when can_run is false', () => {
            expect(source).toMatch(/!opt\.canRun/);
            expect(source).toMatch(/disabled=\{disabled\}/);
        });

        it('should show capability-driven reason for disabled runtime', () => {
            expect(source).toMatch(/⛔/);
            expect(source).toMatch(/opt\.description/);
        });

        it('should have mode radio group', () => {
            expect(source).toMatch(/name='mode'/);
            expect(source).toMatch(/plan/);
            expect(source).toMatch(/build/);
            expect(source).toMatch(/auto/);
        });

        it('should have mode descriptions', () => {
            expect(source).toMatch(/read-only/);
            expect(source).toMatch(/edit/);
            expect(source).toMatch(/policy-driven/);
        });

        it('should have trust status', () => {
            expect(source).toMatch(/arc-studio-config__trusted/);
            expect(source).toMatch(/arc-studio-config__untrusted/);
            expect(source).toMatch(/Workspace.*trusted/);
        });

        it('should have save button', () => {
            expect(source).toMatch(/arc-studio-config__save/);
            expect(source).toMatch(/Save/);
        });

        it('should have providers section', () => {
            expect(source).toMatch(/Providers/);
        });

        it('should have provider dropdown and env var input', () => {
            expect(source).toMatch(/arc-studio-config__provider-dropdown/);
            expect(source).toMatch(/arc-studio-config__provider-env-input/);
            expect(source).toMatch(/OPENAI_API_KEY/);
        });

        it('should have save key reference button', () => {
            expect(source).toMatch(/Save key reference/);
            expect(source).toMatch(/setProviderKeyRef/);
        });

        it('should show web auth warning', () => {
            expect(source).toMatch(/Web session auth is research-only/);
            expect(source).toMatch(/does not capture browser cookies/);
        });

        it('should show provider source badges', () => {
            expect(source).toMatch(/keyring/);
            expect(source).toMatch(/env/);
            expect(source).toMatch(/unset/);
        });

        it('should show env override labels', () => {
            expect(source).toMatch(/arc-studio-config__env-override/);
            expect(source).toMatch(/envOverride/);
        });

        it('should display routing section', () => {
            expect(source).toMatch(/Routing/);
            expect(source).toMatch(/routingMode/);
            expect(source).toMatch(/dryRun/);
            expect(source).toMatch(/isolation/);
        });

        it('should expose editable safe run policy controls', () => {
            expect(source).toMatch(/Run Policy/);
            expect(source).toMatch(/arc-studio-config__isolation-select/);
            expect(source).toMatch(/arc-studio-config__profile-select/);
            expect(source).toMatch(/arc-studio-config__dry-run-toggle/);
            expect(source).toMatch(/arc-studio-config__paid-calls-toggle/);
            expect(source).toMatch(/FALLBACK_ISOLATION_OPTIONS/);
            expect(source).toMatch(/FALLBACK_PROFILE_OPTIONS/);
            expect(source).toMatch(/listProfiles/);
            expect(source).toMatch(/getIsolationStatus/);
            expect(source).toMatch(/listIsolationProviders/);
        });

        it('should save only safe config fields', () => {
            expect(source).toMatch(/defaultRuntime: selectedRuntime/);
            expect(source).toMatch(/mode: selectedMode/);
            expect(source).toMatch(/isolation: selectedIsolation/);
            expect(source).toMatch(/dryRun,/);
            expect(source).toMatch(/allowPaidCalls: dryRun \? false : allowPaidCalls/);
            expect(source).not.toMatch(/profile: selectedProfile/);
        });

        it('should keep profile selector as local fallback until protocol persistence exists', () => {
            expect(source).toMatch(/profile selection follows backend profile inventory/);
            expect(source).toMatch(/not persisted by this safe config update/);
            expect(source).toMatch(/value=\{selectedProfile\}/);
        });

        it('should export safe config snapshot without raw credentials', () => {
            expect(source).toMatch(/arc-studio-config__export-safe/);
            expect(source).toMatch(/buildSafeExport/);
            expect(source).toMatch(/arc-studio-config__safe-export-json/);
            expect(source).toMatch(/no raw credentials/);
            expect(source).toMatch(/source metadata only/);
        });

        it('should force paid calls off for dry-run config', () => {
            expect(source).toMatch(/providerCall:false/);
            expect(source).toMatch(/if \(next\) setAllowPaidCalls\(false\)/);
            expect(source).toMatch(/disabled=\{dryRun\}/);
        });

        it('should expose provider diagnostics quota and cost warning cards', () => {
            expect(source).toMatch(/arc-studio-config__provider-diagnostics/);
            expect(source).toMatch(/arc-studio-config__provider-quota/);
            expect(source).toMatch(/arc-studio-config__provider-cost/);
            expect(source).toMatch(/arc-studio-config__paid-call-warning/);
            expect(source).toMatch(/arc-studio-config__provider-refresh/);
            expect(source).toMatch(/Provider Diagnostics & Quota/);
            expect(source).toMatch(/Paid\/live provider calls require explicit opt-in/);
            expect(source).toMatch(/dry-run\/offline stays providerCall:false/);
            expect(source).toMatch(/Quota display and reset use local counters only/);
        });

        it('should load optional provider diagnostics and quota without hard protocol dependency', () => {
            expect(source).toMatch(/OptionalProviderTelemetryService/);
            expect(source).toMatch(/getProviderDiagnostics\?: \(\) => Promise<unknown>/);
            expect(source).toMatch(/getProviderQuota\?: \(provider\?: string\) => Promise<unknown>/);
            expect(source).toMatch(/resetProviderQuota\?: \(provider\?: string\) => Promise<unknown>/);
            expect(source).toMatch(/providerTelemetryService\.getProviderDiagnostics/);
            expect(source).toMatch(/providerTelemetryService\.getProviderQuota/);
            expect(source).toMatch(/quotaProviderFilter === 'all' \? undefined : quotaProviderFilter/);
            expect(source).toMatch(/getProviderQuota\(quotaProvider\)/);
            expect(source).toMatch(/catch\(\(\) => null\)/);
        });

        it('should expose provider quota filter with catalog fallback copy', () => {
            expect(source).toMatch(/quotaProviderFilter/);
            expect(source).toMatch(/setQuotaProviderFilter/);
            expect(source).toMatch(/arc-studio-config__quota-provider-filter/);
            expect(source).toMatch(/Quota provider filter/);
            expect(source).toMatch(/All providers/);
            expect(source).toMatch(/providerQuotaOptions/);
            expect(source).toMatch(/providerCatalog\.length \? providerCatalog/);
        });

        it('should parse provider quota counters into safe rows', () => {
            expect(source).toMatch(/parseQuotaCounters\(providerQuota\)/);
            expect(source).toMatch(/parseProviderDiagnostics\(providerDiagnostics\)/);
            expect(source).toMatch(/summarizeProfileCostPolicy/);
            expect(source).toMatch(/canResetQuota/);
            expect(source).not.toMatch(/function quotaCounterRows/);
            expect(source).not.toMatch(/\^\(dry_run\|live\):\(provider\|account\):/);
        });

        it('should expose local quota reset only through optional reset bridge and local-copy guard', () => {
            expect(source).toMatch(/resetProviderQuota/);
            expect(source).toMatch(/quotaResetAvailable/);
            expect(source).toMatch(/buildQuotaResetConfirmation/);
            expect(source).toMatch(/canResetQuota\(quotaObject\)/);
            expect(source).toMatch(/quotaResetPhrase === quotaResetRequiredPhrase/);
            expect(source).toMatch(/disabled=\{quotaResetting \|\| !quotaResetConfirmed\}/);
            expect(source).toMatch(/arc-studio-config__quota-reset-local/);
            expect(source).toMatch(/Local quota-counter reset/);
            expect(source).toMatch(/no provider network calls/);
            expect(source).toMatch(/no live API calls/);
            expect(source).toMatch(/no billing action/);
        });

        it('should show profile-linked cost policy summary and explicit gates', () => {
            expect(source).toMatch(/arc-studio-config__cost-policy-summary/);
            expect(source).toMatch(/costPolicySummary/);
            expect(source).toMatch(/current profile dryRun=\{String\(Boolean\(currentProfile\?\.dryRun\)\)\}/);
            expect(source).toMatch(/allowPaidCalls=\{String\(Boolean\(currentProfile\?\.allowPaidCalls\)\)\}/);
            expect(source).toMatch(/effective allowPaidCalls=\{String\(costPolicySummary\.paidCallsAllowed\)\}/);
            expect(source).toMatch(/Dry-run blocks paid calls/);
            expect(source).toMatch(/not full provider-side cost enforcement/);
            expect(source).toMatch(/buildLiveProviderGate/);
            expect(source).toMatch(/arc-studio-config__live-provider-gate/);
            expect(source).toMatch(/Preview-only\/no network: providerCall:false/);
            expect(source).toMatch(/never calls provider API, provider proxy, live API, or billing endpoints/);
        });

        it('should render richer quota rows without raw quota JSON dump', () => {
            expect(source).toMatch(/arc-studio-config__quota-row/);
            expect(source).toMatch(/arc-studio-config__quota-bucket/);
            expect(source).toMatch(/arc-studio-config__quota-scope/);
            expect(source).toMatch(/row\.bucket/);
            expect(source).toMatch(/row\.scope/);
            expect(source).toMatch(/row\.id/);
            expect(source).toMatch(/row\.count/);
            expect(source).not.toMatch(/JSON\.stringify\(providerQuota/);
        });

        it('should summarize redacted provider telemetry only', () => {
            expect(source).toMatch(/liveTestsEnabled/);
            expect(source).toMatch(/routingDefault/);
            expect(source).toMatch(/configuredProvidersCount/);
            expect(source).toMatch(/configuredAccountsCount/);
            expect(source).toMatch(/quotaCounters/);
            expect(source).not.toMatch(/JSON\.stringify\(providerDiagnostics/);
            expect(source).not.toMatch(/JSON\.stringify\(providerQuota/);
        });

        it('should handle unavailable backend gracefully', () => {
            expect(source).toMatch(/arc-studio-config__unavailable/);
            expect(source).toMatch(/Backend unavailable/);
            expect(source).toMatch(/Retry/);
        });

        it('should have config save method', () => {
            expect(source).toMatch(/handleSave/);
            expect(source).toMatch(/saveConfig/);
        });

        it('should NOT render raw api_key values', () => {
            expect(source).not.toMatch(/api_key[^_]/);
            expect(source).not.toMatch(/apiKey[^C]/);
            expect(source).not.toMatch(/password/);
            expect(source).not.toMatch(/type='password'/);
            expect(source).not.toMatch(/type="password"/);
        });

        it('should persist provider key refs only, not raw secrets', () => {
            expect(source).toMatch(/envVar: providerEnvVar\.trim\(\)/);
            expect(source).toMatch(/Save key reference/);
            expect(source).not.toMatch(/setProviderKey\(/);
            expect(source).not.toMatch(/rawKey/);
        });

        it('should show keys as source/status only', () => {
            expect(source).toMatch(/source\/status only/);
            expect(source).toMatch(/raw values are never displayed/);
        });

        it('should load config from backend', () => {
            expect(source).toMatch(/getConfigStatus/);
            expect(source).toMatch(/loadConfig/);
        });

        it('should NOT import TraceViewerSection', () => {
            expect(source).not.toMatch(/TraceViewerSection/);
        });
    });

    describe('AssuranceTab', () => {
        let source: string;

        beforeAll(async () => {
            source = await fs.readFile(path.join(tabsDir, 'AssuranceTab.tsx'), 'utf-8');
        });

        it('should export AssuranceTabProps interface and accept ArcService', () => {
            expect(source).toMatch(/export interface AssuranceTabProps/);
            expect(source).toMatch(/arcService:\s*ArcService/);
        });

        it('should render root assurance class', () => {
            expect(source).toMatch(/className='arc-studio-assurance'/);
            expect(source).toMatch(/aria-label='Assurance panel'/);
        });

        it('should expose HITL inbox backed by ArcService only', () => {
            expect(source).toMatch(/HITL Inbox/);
            expect(source).toMatch(/listPendingHitlPrompts/);
            expect(source).toMatch(/respondHitlPrompt/);
            expect(source).not.toMatch(/fetch\(/);
        });

        it('should support approve reject and modify HITL decisions', () => {
            expect(source).toMatch(/type HitlDecision = 'approve' \| 'reject' \| 'modify'/);
            expect(source).toMatch(/respondHitl\(prompt, 'approve'\)/);
            expect(source).toMatch(/respondHitl\(prompt, 'reject'\)/);
            expect(source).toMatch(/respondHitl\(prompt, 'modify'\)/);
            expect(source).toMatch(/Optional modified response/);
        });

        it('should disable HITL actions for missing or expired tokens', () => {
            expect(source).toMatch(/function isExpired/);
            expect(source).toMatch(/function hitlBlocked/);
            expect(source).toMatch(/!prompt\.token \|\| isExpired\(prompt\.expiresAt\)/);
            expect(source).toMatch(/disabled=\{blocked \|\| responding\}/);
            expect(source).toMatch(/token missing/);
            expect(source).toMatch(/token expired/);
        });

        it('should render audit present missing degraded states honestly', () => {
            expect(source).toMatch(/type AuditState = 'present' \| 'missing' \| 'degraded'/);
            expect(source).toMatch(/return 'missing'/);
            expect(source).toMatch(/return info\.chainVerified \? 'present' : 'degraded'/);
            expect(source).toMatch(/state:\s*\{state\}/);
            expect(source).toMatch(/No adapter-wide keyed audit\/HMAC claim/);
            expect(source).not.toMatch(/adapter-wide keyed audit\/HMAC verified/);
        });

        it('should expose replay stepper with prev next controls', () => {
            expect(source).toMatch(/Replay Stepper/);
            expect(source).toMatch(/replayRun/);
            expect(source).toMatch(/setActiveStep\(step => Math\.max\(0, step - 1\)\)/);
            expect(source).toMatch(/setActiveStep\(step => Math\.min\(replayEvents\.length - 1, step \+ 1\)\)/);
            expect(source).toMatch(/Prev/);
            expect(source).toMatch(/Next/);
        });

        it('should show replay annotations and event data', () => {
            expect(source).toMatch(/eventAnnotations/);
            expect(source).toMatch(/activeAnnotations/);
            expect(source).toMatch(/arc-studio-assurance__annotations/);
            expect(source).toMatch(/arc-studio-assurance__annotation/);
            expect(source).toMatch(/JSON\.stringify\(activeEvent\.data, null, 2\)/);
        });
    });

    describe('SwarmGraph Insight Tab', () => {
        let studioSource: string;
        let tabsIndexSource: string;
        let insightSource: string;

        beforeAll(async () => {
            studioSource = await fs.readFile(path.join(browserDir, 'arc-studio-widget.tsx'), 'utf-8');
            tabsIndexSource = await fs.readFile(path.join(tabsDir, 'index.ts'), 'utf-8');
            insightSource = await fs.readFile(path.join(tabsDir, 'SwarmGraphInsightTab.tsx'), 'utf-8');
        });

        it('should export and wire SwarmGraph Insight tab from the main studio host', () => {
            expect(tabsIndexSource).toMatch(/export.*SwarmGraphInsightTab/);
            expect(tabsIndexSource).toMatch(/export.*SwarmGraphInsightTabProps/);
            expect(studioSource).toMatch(/SwarmGraphInsightTab/);
            expect(studioSource).toMatch(/swarmgraph-insight/);
            expect(studioSource).toMatch(/SwarmGraph Insight/);
        });

        it('should render honest empty and degraded topology consensus cost panels', () => {
            expect(insightSource).toMatch(/Topology/);
            expect(insightSource).toMatch(/Consensus/);
            expect(insightSource).toMatch(/Cost/);
            expect(insightSource).toMatch(/No SwarmGraph topology events found/);
            expect(insightSource).toMatch(/No SwarmGraph consensus events found/);
            expect(insightSource).toMatch(/No SwarmGraph cost events found/);
            expect(insightSource).toMatch(/degraded/i);
            expect(insightSource).toMatch(/trace events/i);
            expect(insightSource).not.toContain(['real', 'trace events present'].join(' '));
        });

        it('should source insight only from trace reads while showing runtime metadata separately', () => {
            expect(insightSource).toMatch(/arcService\.getTraces/);
            expect(insightSource).toMatch(/arcService\.readTrace/);
            expect(insightSource).toMatch(/event\.type/);
            expect(insightSource).not.toMatch(/metadata\.consensus/);
            expect(insightSource).toMatch(/Runtime Metadata/);
            expect(insightSource).toMatch(/runtimeMetadata/);
            expect(insightSource).toMatch(/fake\/offline\/no provider call/i);
            expect(insightSource).toMatch(/real runtime gated/i);
            expect(insightSource).toMatch(/real path absent/i);
            expect(insightSource).toMatch(/not promoted to topology, consensus, or cost insight/);
            expect(insightSource).not.toMatch(/crewai\+swarmgraph/);
        });

        it('should expose honest live-aware controls backed by streamActiveTrace', () => {
            expect(insightSource).toMatch(/arcService\.streamActiveTrace\(\{ runId, mode: 'live' \}\)/);
            expect(insightSource).toMatch(/buildActiveTrace/);
            expect(insightSource).toMatch(/Live insight:/);
            expect(insightSource).toMatch(/disconnected\/degraded/);
            expect(insightSource).toMatch(/No real-live backend claim/);
        });
    });
});
