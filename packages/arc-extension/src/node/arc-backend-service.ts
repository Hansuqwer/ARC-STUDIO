/**
 * ARC Backend Service - Orchestration Layer
 *
 * Implements the ArcService interface by delegating to specialized services:
 * - WorkflowExecutor: Workflow execution and cancellation
 * - TraceParser: Trace file parsing and streaming
 * - WorkflowDetector: Workflow detection in workspace
 * - FileManager: Trace file management
 *
 * This class is an orchestration layer with minimal business logic.
 * All implementation details are in the specialized services.
 */

import { injectable } from '@theia/core/shared/inversify';
import { execFileSync } from 'child_process';
import * as path from 'path';
import {
    ArcService,
    ExecutionOptions,
    ExecutionResult,
    TraceFile,
    TraceData,
    TraceEvent,
    WorkflowInfo,
    ValidationResult,
    CancelResult,
    ArcError,
    ArcErrorCode,
    RuntimeCapabilitiesResponse,
    ProviderStatus,
    ConfigStatus,
    ArcProfileInfo,
    IsolationProviderInfo,
    IsolationStatus,
    SafeConfigUpdate,
    SafeProviderKeyStatus,
    SafeRuntimeConfig,
    TrustStatus,
    ProviderCatalogEntry,
    ProviderDiagnosticsInfo,
    ProviderQuotaInfo,
    ProviderQuotaResetResult,
    ProviderKeyRefRequest,
    ProviderTestResult,
    ProviderModel,
    GatedProviderActionRequest,
    GatedProviderActionResult,
    RunPreflightRequest,
    RunPreflightResponse,
    StartRunRequest,
    StartRunResponse,
    RunLinksResponse,
    RunReceipt,
    FailureAutopsy,
    RunContract,
    CapabilityDiffResponse,
    CapabilityDiff,
    HitlPromptInfo,
    HitlRespondRequest,
    AuditChainInfo,
    ReplayResult,
    ReplayEvent,
    RunDiffResult,
    ActiveTraceStreamRequest,
    ActiveTraceEventChunk,
    BattleRun,
    BattleDetails,
    EloRating,
    ChatSessionSummary,
    ChatSessionDetail,
} from '../common/arc-protocol';
import { validateWorkspaceRoot, validateTraceId, validateRunId } from './security-utils';
import { WorkflowExecutor } from './services/workflow-executor';
import { TraceParser } from './services/trace-parser';
import { WorkflowDetector } from './services/workflow-detector';
import { FileManager } from './services/file-manager';
import { ConfigService } from './services/config-service';
import { RunLifecycleService } from './services/run-lifecycle-service';
import { AuditBridgeService } from './services/audit-bridge-service';
import { BattleService } from './services/battle-service';
import { SessionBridgeService } from './services/session-bridge-service';

const ARC_CLI_ENV_ALLOWLIST = ['PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR'];
const ARC_PYTHON_DAEMON_URL_ENV = 'ARC_PYTHON_DAEMON_URL';

const TRUST_SENSITIVE_FLAGS = [
    'can_run',
    'requires_paid_calls',
    'requires_shell',
    'requires_secrets',
    'requires_network',
];

const SAFE_CONFIG_KEYS = ['defaultRuntime', 'mode', 'isolation', 'allowPaidCalls', 'dryRun', 'routingMode', 'selectedProfile'];
const UNSAFE_CONFIG_KEY_PATTERN = /(secret|token|password|api[_-]?key|raw.*key|credential)/i;

function buildArcCliEnv(): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {};
    for (const key of ARC_CLI_ENV_ALLOWLIST) {
        const value = process.env[key];
        if (value !== undefined) {
            env[key] = value;
        }
    }
    return env;
}

@injectable()
export class ArcBackendService implements ArcService {
    private readonly executor: WorkflowExecutor;
    private readonly parser: TraceParser;
    private readonly detector: WorkflowDetector;
    private readonly fileManager: FileManager;
    private readonly configService: ConfigService;
    private readonly runLifecycleService: RunLifecycleService;
    private readonly auditBridgeService: AuditBridgeService;
    private readonly battleService: BattleService;
    private readonly sessionBridgeService: SessionBridgeService;
    private readonly activeStreamCancels = new Map<string, { cancelled: boolean }>();
    private workspaceRoot: string;

    constructor(
        executor?: WorkflowExecutor,
        parser?: TraceParser,
        detector?: WorkflowDetector,
        fileManager?: FileManager,
        configService?: ConfigService,
        runLifecycleService?: RunLifecycleService,
        auditBridgeService?: AuditBridgeService,
        battleService?: BattleService,
        sessionBridgeService?: SessionBridgeService
    ) {
        this.executor = executor ?? new WorkflowExecutor();
        this.parser = parser ?? new TraceParser();
        this.detector = detector ?? new WorkflowDetector();
        this.fileManager = fileManager ?? new FileManager();
        this.workspaceRoot = validateWorkspaceRoot(process.cwd());
        this.configService = configService ?? new ConfigService(this.workspaceRoot);
        this.runLifecycleService = runLifecycleService ?? new RunLifecycleService(
            this.executor,
            this.parser,
            this.detector,
            this.fileManager,
            this.workspaceRoot
        );
        this.auditBridgeService = auditBridgeService ?? new AuditBridgeService(this.workspaceRoot);
        this.battleService = battleService ?? new BattleService();
        this.sessionBridgeService = sessionBridgeService ?? new SessionBridgeService(this.workspaceRoot);
    }

    // ========== Workflow Execution ==========

    /**
     * Execute a SwarmGraph workflow.
     * @deprecated Use RunLifecycleService.executeWorkflow() directly. Will be removed in v0.3.0.
     */
    async executeWorkflow(
        prompt: string,
        options?: ExecutionOptions
    ): Promise<ExecutionResult> {
        return this.runLifecycleService.executeWorkflow(prompt, options);
    }

    /**
     * Cancel a running workflow execution.
     * @deprecated Use RunLifecycleService.cancelWorkflow() directly. Will be removed in v0.3.0.
     */
    async cancelWorkflow(runId: string): Promise<CancelResult> {
        return this.runLifecycleService.cancelWorkflow(runId);
    }

    // ========== Trace Management ==========

    /**
     * Get all trace files from .arc/traces/ directory.
     * @deprecated Use RunLifecycleService.getTraces() directly. Will be removed in v0.3.0.
     */
    async getTraces(): Promise<TraceFile[]> {
        return this.runLifecycleService.getTraces();
    }

    /**
     * Read and parse a specific trace file by ID.
     * @deprecated Use RunLifecycleService.readTrace() directly. Will be removed in v0.3.0.
     */
    async readTrace(traceId: string): Promise<TraceData> {
        return this.runLifecycleService.readTrace(traceId);
    }

    /**
     * Stream trace events from a trace file as an async iterable.
     * @deprecated Use RunLifecycleService.streamTrace() directly. Will be removed in v0.3.0.
     */
    async streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>> {
        return this.runLifecycleService.streamTrace(traceId);
    }

    /**
     * @deprecated Use RunLifecycleService.streamActiveTrace() directly. Will be removed in v0.3.0.
     */
    async streamActiveTrace(request: ActiveTraceStreamRequest): Promise<AsyncIterable<ActiveTraceEventChunk>> {
        return this.runLifecycleService.streamActiveTrace(request);
    }

    /**
     * @deprecated Use RunLifecycleService.readActiveTraceStream() directly. Will be removed in v0.3.0.
     */
    async readActiveTraceStream(request: ActiveTraceStreamRequest): Promise<ActiveTraceEventChunk[]> {
        return this.runLifecycleService.readActiveTraceStream(request);
    }

    /**
     * @deprecated Use RunLifecycleService.cancelActiveTraceStream() directly. Will be removed in v0.3.0.
     */
    async cancelActiveTraceStream(runId: string): Promise<{ success: boolean; message: string }> {
        return this.runLifecycleService.cancelActiveTraceStream(runId);
    }

    /**
     * Validate a trace file format.
     */
    /**
     * Validate a trace file format.
     * @deprecated Use RunLifecycleService.validateTrace() directly. Will be removed in v0.3.0.
     */
    async validateTrace(traceId: string): Promise<ValidationResult> {
        return this.runLifecycleService.validateTrace(traceId);
    }

    // ========== Workflow Detection ==========

    /**
     * Detect workflows in the workspace.
     * @deprecated Use RunLifecycleService.detectWorkflows() directly. Will be removed in v0.3.0.
     */
    async detectWorkflows(): Promise<WorkflowInfo[]> {
        return this.runLifecycleService.detectWorkflows();
    }

    // ========== Runtime Capabilities (arc-adapters) ==========

    /**
     * List runtime capability reports by calling the Python CLI.
     * @deprecated Use RunLifecycleService.listRuntimeCapabilities() directly. Will be removed in v0.3.0.
     */
    async listRuntimeCapabilities(): Promise<RuntimeCapabilitiesResponse> {
        return this.runLifecycleService.listRuntimeCapabilities();
    }

    /**
     * @deprecated Use RunLifecycleService.preflightRun() directly. Will be removed in v0.3.0.
     */
    async preflightRun(request: RunPreflightRequest): Promise<RunPreflightResponse> {
        return this.runLifecycleService.preflightRun(request);
    }

    /**
     * @deprecated Use RunLifecycleService.startRun() directly. Will be removed in v0.3.0.
     */
    async startRun(request: StartRunRequest): Promise<StartRunResponse> {
        return this.runLifecycleService.startRun(request);
    }

    /**
     * Get provider configuration status by calling the Python CLI.
     */
    /**
     * @deprecated Use ConfigService.getProviderStatus() directly. Will be removed in v0.3.0.
     */
    async getProviderStatus(provider: string, baseUrl?: string): Promise<ProviderStatus> {
        return this.configService.getProviderStatus(provider, baseUrl);
    }

    /**
     * Get current workspace status.
     * @deprecated Use ConfigService.getWorkspaceStatus() directly. Will be removed in v0.3.0.
     */
    async getWorkspaceStatus(): Promise<{ frontendPath: string; backendPath: string; source: string }> {
        return this.configService.getWorkspaceStatus();
    }

    // ========== Config Tab Methods (Session B) ==========

    /**
     * Get config status with all secret values stripped.
     * Calls the Python CLI for provider statuses and reads workspace trust state.
     * Gracefully handles unavailable backend by returning degraded state.
     */
    /**
     * @deprecated Use ConfigService.getConfigStatus() directly. Will be removed in v0.3.0.
     */
    async getConfigStatus(): Promise<ConfigStatus> {
        return this.configService.getConfigStatus();
    }

    /**
     * Save safe config fields only.
     * @deprecated Use ConfigService.saveConfig() directly. Will be removed in v0.3.0.
     */
    async saveConfig(update: SafeConfigUpdate): Promise<{ success: boolean; message: string }> {
        return this.configService.saveConfig(update);
    }

    /**
     * @deprecated Use ConfigService.listProfiles() directly. Will be removed in v0.3.0.
     */
    async listProfiles(): Promise<ArcProfileInfo[]> {
        return this.configService.listProfiles();
    }

    /**
     * @deprecated Use ConfigService.getIsolationStatus() directly. Will be removed in v0.3.0.
     */
    async getIsolationStatus(): Promise<IsolationStatus> {
        return this.configService.getIsolationStatus();
    }

    /**
     * @deprecated Use ConfigService.listIsolationProviders() directly. Will be removed in v0.3.0.
     */
    async listIsolationProviders(): Promise<IsolationProviderInfo[]> {
        return this.configService.listIsolationProviders();
    }

    /**
     * @deprecated Use ConfigService.getProviderCatalog() directly. Will be removed in v0.3.0.
     */
    async getProviderCatalog(): Promise<ProviderCatalogEntry[]> {
        return this.configService.getProviderCatalog();
    }

    /**
     * @deprecated Use ConfigService.getProviderDiagnostics() directly. Will be removed in v0.3.0.
     */
    async getProviderDiagnostics(): Promise<ProviderDiagnosticsInfo> {
        return this.configService.getProviderDiagnostics();
    }

    /**
     * @deprecated Use ConfigService.getProviderQuota() directly. Will be removed in v0.3.0.
     */
    async getProviderQuota(provider?: string): Promise<ProviderQuotaInfo> {
        return this.configService.getProviderQuota(provider);
    }

    /**
     * @deprecated Use ConfigService.resetProviderQuota() directly. Will be removed in v0.3.0.
     */
    async resetProviderQuota(): Promise<ProviderQuotaResetResult> {
        return this.configService.resetProviderQuota();
    }

    /**
     * @deprecated Use ConfigService.runGatedProviderAction() directly. Will be removed in v0.3.0.
     */
    async runGatedProviderAction(request: GatedProviderActionRequest): Promise<GatedProviderActionResult> {
        return this.configService.runGatedProviderAction(request);
    }

    /**
     * @deprecated Use ConfigService.setProviderKeyRef() directly. Will be removed in v0.3.0.
     */
    async setProviderKeyRef(request: ProviderKeyRefRequest): Promise<{ success: boolean; message: string }> {
        return this.configService.setProviderKeyRef(request);
    }

    /**
     * @deprecated Use ConfigService.unsetProviderKeyRef() directly. Will be removed in v0.3.0.
     */
    async unsetProviderKeyRef(providerOrAccountId: string): Promise<{ success: boolean; message: string }> {
        return this.configService.unsetProviderKeyRef(providerOrAccountId);
    }

    /**
     * Test provider connection and configuration.
     * @deprecated Use ConfigService.testProvider() directly. Will be removed in v0.3.0.
     */
    async testProvider(providerId: string): Promise<ProviderTestResult> {
        return this.configService.testProvider(providerId);
    }

    /**
     * List available models for a provider.
     * @deprecated Use ConfigService.listProviderModels() directly. Will be removed in v0.3.0.
     */
    async listProviderModels(providerId?: string): Promise<ProviderModel[]> {
        return this.configService.listProviderModels(providerId);
    }

    // ========== Run Links Methods (Session B7) ==========

    /**
     * Get cross-linked event chains for a run.
     * @deprecated Use AuditBridgeService.getRunLinks() directly. Will be removed in v0.3.0.
     */
    async getRunLinks(runId: string, filter?: string, stableId?: string): Promise<RunLinksResponse> {
        return this.auditBridgeService.getRunLinks(runId, filter, stableId);
    }

    // ========== Run Details (Cockpit Cards) ==========

    /**
     * Get run receipt for a completed/failed/cancelled run.
     * @deprecated Use AuditBridgeService.getRunReceipt() directly. Will be removed in v0.3.0.
     */
    async getRunReceipt(runId: string): Promise<RunReceipt> {
        return this.auditBridgeService.getRunReceipt(runId);
    }

    /**
     * Get failure autopsy for a failed run. Returns null if no autopsy exists.
     * @deprecated Use AuditBridgeService.getRunAutopsy() directly. Will be removed in v0.3.0.
     */
    async getRunAutopsy(runId: string): Promise<FailureAutopsy | null> {
        return this.auditBridgeService.getRunAutopsy(runId);
    }

    /**
     * Get run contract for a run. Returns null if no contract exists.
     */
    async getRunContract(runId: string): Promise<RunContract | null> {
        try {
            validateRunId(runId);
            const contractPath = path.join(this.workspaceRoot, '.arc', 'contracts', `${runId}.json`);
            const fs = await import('fs-extra');
            if (!await fs.pathExists(contractPath)) {
                return null;
            }
            const content = await fs.readFile(contractPath, 'utf-8');
            return JSON.parse(content) as RunContract;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read contract: ${error instanceof Error ? error.message : 'Unknown error'}`,
                { runId }
            );
        }
    }

    // ========== HITL Methods (Slice 7) ==========

    /**
     * List pending HITL prompts by calling the Python CLI.
     */
    async listPendingHitlPrompts(): Promise<HitlPromptInfo[]> {
        try {
            const output = execFileSync('arc', ['hitl', 'pending', '--workspace', this.workspaceRoot, '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && Array.isArray(parsed.data)) {
                return parsed.data.map((p: any) => ({
                    promptId: p.hitl_id || p.prompt_id || p.promptId,
                    runId: p.run_id || p.runId,
                    prompt: p.prompt_text || p.prompt || '',
                    createdAt: p.created_at || p.createdAt || '',
                    expiresAt: p.expires_at || p.expiresAt,
                    promptType: p.prompt_type || p.promptType,
                    token: p.token,
                    status: p.status || p.state,
                    expired: p.expired ?? p.is_expired ?? p.isExpired,
                    singleUse: p.single_use ?? p.singleUse,
                    usedAt: p.used_at || p.usedAt,
                })) as HitlPromptInfo[];
            }
            return [];
        } catch (error) {
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Failed to list HITL prompts: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    /**
     * Respond to a HITL prompt by calling the Python CLI.
     */
    async respondHitlPrompt(request: HitlRespondRequest): Promise<{ success: boolean; message: string }> {
        try {
            const args = [
                'hitl',
                'respond',
                request.promptId,
                '--decision',
                request.decision,
                '--token',
                request.token,
                '--workspace',
                this.workspaceRoot,
                '--json',
            ];
            if (request.response) {
                args.push('--notes', request.response);
            }
            const output = execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok) {
                return { success: true, message: parsed.data?.message || `HITL ${request.decision} for ${request.promptId}` };
            }
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                parsed?.error?.message || 'HITL respond failed',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Failed to respond to HITL prompt: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    // ========== Audit Methods (Slice 7) ==========

    /**
     * Get audit chain info for a run by calling the Python CLI.
     */
    async getAuditChainInfo(runId: string): Promise<AuditChainInfo | null> {
        try {
            // First check if there's an audit path for this run
            const traceOutput = execFileSync('arc', ['runs', 'status', runId, '--workspace', this.workspaceRoot, '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const traceParsed = JSON.parse(traceOutput);
            const auditPath = traceParsed?.data?.audit_path || traceParsed?.data?.auditPath;

            if (!auditPath) {
                return {
                    runId,
                    chainVerified: false,
                    recordCount: 0,
                    state: 'missing',
                    reason: 'No audit path recorded for this run.',
                };
            }

            try {
                const output = execFileSync('arc', ['audit', 'verify', runId, '--chain', auditPath, '--json'], {
                    timeout: 10000,
                    encoding: 'utf-8',
                    windowsHide: true,
                    env: buildArcCliEnv(),
                });
                const parsed = JSON.parse(output);
                if (parsed.ok && parsed.data) {
                    const data = parsed.data;
                    const chainVerified = Boolean(data.chain_verified ?? data.chainVerified ?? data.verified);
                    return {
                        runId,
                        auditPath,
                        chainVerified,
                        recordCount: data.record_count ?? data.recordCount ?? this.extractAuditRecordCount(data.reason),
                        state: data.state || (chainVerified ? 'present' : 'degraded'),
                        reason: data.reason || data.message,
                        signature: data.signature || undefined,
                        hmacAlgo: data.hmac_algo || data.hmacAlgo,
                    } as AuditChainInfo;
                }
                return {
                    runId,
                    auditPath,
                    chainVerified: false,
                    recordCount: 0,
                    state: 'degraded',
                    reason: parsed?.error?.message || 'Audit verification returned no data.',
                };
            } catch (verifyError) {
                return {
                    runId,
                    auditPath,
                    chainVerified: false,
                    recordCount: 0,
                    state: 'degraded',
                    reason: `Audit verification unavailable: ${verifyError instanceof Error ? verifyError.message : 'Unknown error'}`,
                };
            }
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Failed to get audit chain info: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    // ========== Replay Methods (Slice 7) ==========

    /**
     * Replay stored trace events for a run by calling the Python CLI.
     */
    async replayRun(runId: string): Promise<ReplayResult> {
        try {
            const output = execFileSync('arc', ['runs', 'replay', runId, '--workspace', this.workspaceRoot, '--json'], {
                timeout: 30000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                const data = parsed.data;
                const events: ReplayEvent[] = (data.events || []).map((ev: any) => ({
                    type: ev.type || 'UNKNOWN',
                    timestamp: ev.timestamp || '',
                    runId: ev.run_id || ev.runId || runId,
                    sequence: ev.sequence ?? 0,
                    data: ev.data || {},
                    category: ev.category || ev.event_category || ev.eventCategory || this.replayCategoryForType(ev.type),
                    annotations: ev.annotations || ev.notes,
                    metadata: ev.metadata || ev.meta,
                }));
                return {
                    runId,
                    events,
                    totalEvents: events.length,
                    annotations: data.annotations || data.notes,
                    metadata: data.metadata || data.meta,
                };
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                parsed?.error?.message || 'CLI returned no data for replay',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Failed to replay run: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    /**
     * Diff two stored runs by calling the Python CLI.
     */
    async diffRuns(runAId: string, runBId: string): Promise<RunDiffResult> {
        try {
            validateRunId(runAId);
            validateRunId(runBId);
            const output = execFileSync('arc', ['runs', 'diff', runAId, runBId, '--workspace', this.workspaceRoot, '--json'], {
                timeout: 30000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                const data = parsed.data;
                return {
                    runAId: data.run_a_id || data.runAId || runAId,
                    runBId: data.run_b_id || data.runBId || runBId,
                    statusA: data.status_a || data.statusA || 'unknown',
                    statusB: data.status_b || data.statusB || 'unknown',
                    runtimeA: data.runtime_a || data.runtimeA || 'unknown',
                    runtimeB: data.runtime_b || data.runtimeB || 'unknown',
                    durationAMs: data.duration_a_ms ?? data.durationAMs ?? null,
                    durationBMs: data.duration_b_ms ?? data.durationBMs ?? null,
                    eventCountA: data.event_count_a ?? data.eventCountA ?? 0,
                    eventCountB: data.event_count_b ?? data.eventCountB ?? 0,
                    typesOnlyInA: data.types_only_in_a || data.typesOnlyInA || [],
                    typesOnlyInB: data.types_only_in_b || data.typesOnlyInB || [],
                    typesCommon: data.types_common || data.typesCommon || [],
                    finalOutputA: data.final_output_a ?? data.finalOutputA ?? null,
                    finalOutputB: data.final_output_b ?? data.finalOutputB ?? null,
                    errorEventsA: data.error_events_a || data.errorEventsA || [],
                    errorEventsB: data.error_events_b || data.errorEventsB || [],
                    toolCallsA: data.tool_calls_a ?? data.toolCallsA ?? 0,
                    toolCallsB: data.tool_calls_b ?? data.toolCallsB ?? 0,
                };
            }
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                parsed?.error?.message || 'CLI returned no data for run diff',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Failed to diff runs: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    // ========== Capability Diff (Session B) ==========

    /**
     * Get capability diff between two runtimes.
     * Calls the Python CLI to compute the diff and analyzes trust boundary changes.
     */
    async getCapabilityDiff(fromRuntime: string, toRuntime: string): Promise<CapabilityDiffResponse> {
        try {
            const output = execFileSync('arc', [
                'runtimes',
                '--diff-from', fromRuntime,
                '--diff-to', toRuntime,
                '--workspace', this.workspaceRoot,
                '--json',
            ], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                const data = parsed.data;
                const diff: CapabilityDiff = {
                    schemaVersion: data.schema_version ?? 1,
                    diffId: data.diff_id,
                    runtimeId: data.runtime_id,
                    beforeSnapshotId: data.before_snapshot_id,
                    afterSnapshotId: data.after_snapshot_id,
                    addedCapabilities: data.added_capabilities ?? [],
                    removedCapabilities: data.removed_capabilities ?? [],
                    changedFlags: data.changed_flags ?? {},
                    requiresConfirmation: data.requires_confirmation ?? false,
                    timestamp: data.timestamp,
                };

                const trustSensitiveChanges = Object.keys(diff.changedFlags).filter(
                    key => TRUST_SENSITIVE_FLAGS.includes(key)
                );
                const trustBoundaryWidened = trustSensitiveChanges.some(key => {
                    const change = diff.changedFlags[key];
                    return change.after === true && change.before === false;
                });

                return {
                    diff,
                    fromRuntime,
                    toRuntime,
                    trustBoundaryWidened,
                    trustSensitiveChanges,
                };
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                parsed?.error?.message || 'CLI returned no data for capability diff',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Failed to get capability diff: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    // ========== Private Helpers ==========

    /**
     * Check if a file exists.
     */
    private async fileExists(filePath: string): Promise<boolean> {
        const fs = await import('fs-extra');
        return fs.pathExists(filePath);
    }

    /**
     * Read file content.
     */
    private async readFileContent(filePath: string): Promise<string> {
        const fs = await import('fs-extra');
        return fs.readFile(filePath, 'utf-8');
    }

    private async *createActiveTraceIterable(
        request: ActiveTraceStreamRequest,
        cancelToken: { cancelled: boolean }
    ): AsyncIterable<ActiveTraceEventChunk> {
        const timeoutMs = Math.min(Math.max(request.timeoutMs ?? 30000, 1), 300000);
        const startedAt = Date.now();
        const now = (): string => new Date().toISOString();
        try {
            yield {
                runId: request.runId,
                mode: request.mode,
                sequence: 0,
                status: {
                    runId: request.runId,
                    mode: request.mode,
                    state: request.mode === 'replay' ? 'replaying' : 'connecting',
                    timestamp: now(),
                },
                done: false,
            };

            if (cancelToken.cancelled) {
                yield this.activeTraceTerminalChunk(request, 1, 'RUN_CANCELLED', 'cancelled', 'Stream cancelled.');
                return;
            }

            if (request.mode === 'live') {
                yield* this.streamLiveActiveTrace(request, cancelToken, timeoutMs, startedAt);
                return;
            }

            const replay = await this.replayRun(request.runId);
            let sequence = 1;
            for (const event of replay.events) {
                if (cancelToken.cancelled) {
                    yield this.activeTraceTerminalChunk(request, sequence, 'RUN_CANCELLED', 'cancelled', 'Stream cancelled.');
                    return;
                }
                if (Date.now() - startedAt > timeoutMs) {
                    yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'error', 'Stream timed out.');
                    return;
                }
                yield {
                    runId: request.runId,
                    mode: 'replay',
                    sequence,
                    event,
                    terminal: this.activeTraceTerminalFromEventType(event.type),
                    done: false,
                };
                sequence += 1;
            }
            yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'ended', 'Replay stream ended.');
        } catch (error) {
            yield this.activeTraceTerminalChunk(
                request,
                1,
                'STREAM_END',
                'error',
                error instanceof Error ? error.message : 'Unknown stream error'
            );
        } finally {
            this.activeStreamCancels.delete(request.runId);
        }
    }

    private async *streamLiveActiveTrace(
        request: ActiveTraceStreamRequest,
        cancelToken: { cancelled: boolean },
        timeoutMs: number,
        startedAt: number
    ): AsyncIterable<ActiveTraceEventChunk> {
        const baseUrl = this.resolvePythonDaemonBaseUrl(request);
        if (!baseUrl) {
            yield this.activeTraceTerminalChunk(
                request,
                1,
                'STREAM_END',
                'disconnected',
                'Live SSE proxy disconnected; no Python web/SSE base URL configured.'
            );
            return;
        }

        let streamUrl: URL;
        try {
            streamUrl = this.buildPythonDaemonStreamUrl(baseUrl, request.runId);
        } catch (error) {
            yield this.activeTraceTerminalChunk(request, 1, 'STREAM_END', 'error', 'Invalid Python web/SSE base URL.');
            return;
        }
        streamUrl.searchParams.set('mode', 'live');

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), timeoutMs);
        let sequence = 1;
        try {
            const response = await fetch(streamUrl, {
                method: 'GET',
                headers: { Accept: 'text/event-stream' },
                signal: controller.signal,
            });
            if (!response.ok || !response.body) {
                yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'disconnected', `Live SSE proxy degraded; Python daemon returned HTTP ${response.status}.`);
                return;
            }
            yield {
                runId: request.runId,
                mode: 'live',
                sequence: sequence++,
                status: {
                    runId: request.runId,
                    mode: 'live',
                    state: 'connected',
                    message: 'Live SSE stream connected.',
                    baseUrlConfigured: true,
                    timestamp: new Date().toISOString(),
                },
                done: false,
            };

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (!cancelToken.cancelled) {
                if (Date.now() - startedAt > timeoutMs) {
                    controller.abort();
                    yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'error', 'Stream timed out.');
                    return;
                }
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const frames = buffer.split(/\r?\n\r?\n/);
                buffer = frames.pop() ?? '';
                for (const frame of frames) {
                    const event = this.parseSseEvent(frame);
                    if (!event) continue;
                    const terminal = this.activeTraceTerminalFromEventType(String(event.type ?? ''));
                    yield { runId: request.runId, mode: 'live', sequence: sequence++, event, terminal, done: false };
                    if (terminal) {
                        yield this.activeTraceTerminalChunk(request, sequence, terminal, 'ended', 'Live SSE stream ended.');
                        return;
                    }
                }
            }
            yield this.activeTraceTerminalChunk(
                request,
                sequence,
                cancelToken.cancelled ? 'RUN_CANCELLED' : 'STREAM_END',
                cancelToken.cancelled ? 'cancelled' : 'disconnected',
                cancelToken.cancelled ? 'Stream cancelled.' : 'Live SSE stream disconnected.'
            );
        } catch (error) {
            yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'disconnected', `Live SSE proxy degraded; ${error instanceof Error ? error.message : 'Unknown live SSE error'}`);
        } finally {
            clearTimeout(timeout);
            controller.abort();
        }
    }

    private resolvePythonDaemonBaseUrl(request: ActiveTraceStreamRequest): string | undefined {
        return request.baseUrl?.trim() || process.env[ARC_PYTHON_DAEMON_URL_ENV]?.trim() || undefined;
    }

    private buildPythonDaemonStreamUrl(baseUrl: string, runId: string): URL {
        const parsedBaseUrl = new URL(baseUrl);
        if (parsedBaseUrl.protocol !== 'http:' && parsedBaseUrl.protocol !== 'https:') {
            throw new Error('Python web/SSE base URL must use http or https.');
        }
        if (parsedBaseUrl.username || parsedBaseUrl.password) {
            throw new Error('Python web/SSE base URL must not include credentials.');
        }
        return new URL(`/api/runs/${encodeURIComponent(runId)}/events`, parsedBaseUrl.href.endsWith('/') ? parsedBaseUrl.href : `${parsedBaseUrl.href}/`);
    }

    private parseSseEvent(frame: string): Record<string, unknown> | undefined {
        const data = frame
            .split(/\r?\n/)
            .filter(line => line.startsWith('data:'))
            .map(line => line.slice(5).trimStart())
            .join('\n');
        if (!data) return undefined;
        try {
            return JSON.parse(data) as Record<string, unknown>;
        } catch {
            return { type: 'MESSAGE', data: { message: data } };
        }
    }

    private activeTraceTerminalChunk(
        request: ActiveTraceStreamRequest,
        sequence: number,
        terminal: ActiveTraceEventChunk['terminal'],
        state: NonNullable<ActiveTraceEventChunk['status']>['state'],
        message: string
    ): ActiveTraceEventChunk {
        return {
            runId: request.runId,
            mode: request.mode,
            sequence,
            status: {
                runId: request.runId,
                mode: request.mode,
                state,
                message,
                baseUrlConfigured: Boolean(request.baseUrl?.trim()),
                timestamp: new Date().toISOString(),
            },
            terminal,
            done: true,
        };
    }

    private activeTraceTerminalFromEventType(type: string): ActiveTraceEventChunk['terminal'] | undefined {
        if (type === 'RUN_COMPLETED' || type === 'RUN_FAILED' || type === 'RUN_CANCELLED') {
            return type;
        }
        return undefined;
    }

    private replayCategoryForType(type?: string): ReplayEvent['category'] {
        const normalized = (type || '').toUpperCase();
        if (normalized.includes('ERROR') || normalized.includes('FAILED')) return 'error';
        if (normalized.includes('MESSAGE')) return 'message';
        if (normalized.includes('TOOL')) return 'tool';
        if (normalized.includes('HITL')) return 'hitl';
        if (normalized.includes('AUDIT')) return 'audit';
        if (normalized.includes('RUN_') || normalized.includes('NODE_')) return 'lifecycle';
        return 'unknown';
    }

    private mapRuntimeCapability(runtime: any): RuntimeCapabilitiesResponse['runtimes'][number] {
        const metadata = runtime.metadata || runtime.meta || {};
        const traceMetadata = runtime.trace_metadata || runtime.traceMetadata || metadata.trace_metadata || metadata.traceMetadata || {};
        const gates = runtime.gates || metadata.gates || {};
        return {
            ...runtime,
            runtimeId: runtime.runtime_id || runtime.runtimeId,
            canRun: runtime.can_run ?? runtime.canRun,
            detectedArtifacts: runtime.detected_artifacts || runtime.detectedArtifacts || [],
            requiredEnv: runtime.required_env || runtime.requiredEnv || [],
            requiresPaidCalls: runtime.requires_paid_calls ?? runtime.requiresPaidCalls ?? false,
            doctorActions: runtime.doctor_actions || runtime.doctorActions || [],
            metadata,
            traceMetadata,
            gates,
            realRuntimeGate: runtime.real_runtime_gate ?? runtime.realRuntimeGate ?? gates.real_runtime ?? gates.realRuntime,
            providerBacked: runtime.provider_backed ?? runtime.providerBacked ?? metadata.provider_backed ?? metadata.providerBacked,
        };
    }

    private extractAuditRecordCount(reason?: string): number {
        if (!reason) {
            return 0;
        }
        const match = reason.match(/verified\s+(\d+)\s+records?/i);
        return match ? Number(match[1]) : 0;
    }

    async getPythonDaemonUrl(): Promise<string | undefined> {
        return process.env[ARC_PYTHON_DAEMON_URL_ENV]?.trim() || undefined;
    }

    async discoverPythonDaemonUrl(): Promise<string | undefined> {
        const defaultUrl = 'http://127.0.0.1:7777';
        try {
            const url = new URL('/health', defaultUrl);
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 2000);
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    signal: controller.signal,
                });
                if (response.ok) {
                    return defaultUrl;
                }
                return undefined;
            } finally {
                clearTimeout(timeout);
                controller.abort();
            }
        } catch {
            return undefined;
        }
    }

    // ========== Battle Methods (Phase 34.2) ==========

    async listBattles(options?: { status?: string; limit?: number }): Promise<BattleRun[]> {
        return this.battleService.listBattles(options);
    }

    async getBattleDetails(battleId: string): Promise<BattleDetails> {
        return this.battleService.getBattleDetails(battleId);
    }

    async getLeaderboard(limit?: number): Promise<EloRating[]> {
        return this.battleService.getLeaderboard(limit);
    }

    // ========== Session Bridge (Phase 43 — read-only) ==========

    async listChatSessions(): Promise<ChatSessionSummary[]> {
        return this.sessionBridgeService.listChatSessions();
    }

    async getChatSession(sessionId: string): Promise<ChatSessionDetail> {
        return this.sessionBridgeService.getChatSession(sessionId);
    }
}
