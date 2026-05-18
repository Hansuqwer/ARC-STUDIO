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
} from '../common/arc-protocol';
import { validateWorkspaceRoot, validateTraceId, validateRunId } from './security-utils';
import { WorkflowExecutor } from './services/workflow-executor';
import { TraceParser } from './services/trace-parser';
import { WorkflowDetector } from './services/workflow-detector';
import { FileManager } from './services/file-manager';

const ARC_CLI_ENV_ALLOWLIST = ['PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR'];

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
    private readonly activeStreamCancels = new Map<string, { cancelled: boolean }>();
    private workspaceRoot: string;

    constructor(
        executor?: WorkflowExecutor,
        parser?: TraceParser,
        detector?: WorkflowDetector,
        fileManager?: FileManager
    ) {
        this.executor = executor ?? new WorkflowExecutor();
        this.parser = parser ?? new TraceParser();
        this.detector = detector ?? new WorkflowDetector();
        this.fileManager = fileManager ?? new FileManager();
        this.workspaceRoot = validateWorkspaceRoot(process.cwd());
    }

    // ========== Workflow Execution ==========

    /**
     * Execute a SwarmGraph workflow.
     * Delegates to WorkflowExecutor after ensuring traces directory exists.
     */
    async executeWorkflow(
        prompt: string,
        options?: ExecutionOptions
    ): Promise<ExecutionResult> {
        await this.fileManager.ensureTracesDir(this.workspaceRoot);
        return this.executor.executeWorkflow(prompt, {
            ...options,
            workspaceRoot: this.workspaceRoot
        });
    }

    /**
     * Cancel a running workflow execution.
     */
    async cancelWorkflow(runId: string): Promise<CancelResult> {
        return this.executor.cancelWorkflow(runId);
    }

    // ========== Trace Management ==========

    /**
     * Get all trace files from .arc/traces/ directory.
     */
    async getTraces(): Promise<TraceFile[]> {
        return this.fileManager.getTraceFiles(this.workspaceRoot);
    }

    /**
     * Read and parse a specific trace file by ID.
     */
    async readTrace(traceId: string): Promise<TraceData> {
        try {
            const tracePath = this.fileManager.getTracePath(
                this.workspaceRoot,
                traceId
            );

            const result = await this.parser.parseTrace(tracePath, traceId);
            if (!result) {
                throw new ArcError(
                    ArcErrorCode.PARSE_ERROR,
                    `Failed to parse trace file: ${traceId}`,
                    { traceId }
                );
            }

            return result;
        } catch (error) {
            if (error instanceof ArcError) {
                throw error;
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read trace: ${traceId}`,
                { error: error instanceof Error ? error.message : 'Unknown error' }
            );
        }
    }

    /**
     * Stream trace events from a trace file as an async iterable.
     */
    async streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>> {
        try {
            validateTraceId(traceId);

            const tracePath = this.fileManager.getTracePath(
                this.workspaceRoot,
                traceId
            );

            // Check file exists before returning iterable
            const fs = await import('fs-extra');
            if (!await fs.pathExists(tracePath)) {
                throw new ArcError(
                    ArcErrorCode.TRACE_NOT_FOUND,
                    `Trace file not found: ${traceId}`,
                    { traceId }
                );
            }

            return this.parser.streamTrace(tracePath);
        } catch (error) {
            if (error instanceof ArcError) {
                throw error;
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to stream trace: ${traceId}`,
                { error: error instanceof Error ? error.message : 'Unknown error' }
            );
        }
    }

    async streamActiveTrace(request: ActiveTraceStreamRequest): Promise<AsyncIterable<ActiveTraceEventChunk>> {
        validateRunId(request.runId);
        if (request.mode !== 'live' && request.mode !== 'replay') {
            throw new ArcError(ArcErrorCode.INVALID_INPUT, `Unsupported stream mode: ${request.mode}`);
        }
        const cancelToken = { cancelled: false };
        this.activeStreamCancels.set(request.runId, cancelToken);
        return this.createActiveTraceIterable(request, cancelToken);
    }

    async cancelActiveTraceStream(runId: string): Promise<{ success: boolean; message: string }> {
        validateRunId(runId);
        const token = this.activeStreamCancels.get(runId);
        if (!token) {
            return { success: false, message: `No active stream proxy for run: ${runId}` };
        }
        token.cancelled = true;
        this.activeStreamCancels.delete(runId);
        return { success: true, message: `Cancelled active stream proxy for run: ${runId}` };
    }

    /**
     * Validate a trace file format.
     */
    async validateTrace(traceId: string): Promise<ValidationResult> {
        const errors: string[] = [];
        const warnings: string[] = [];
        let format: 'json' | 'jsonl' | 'unknown' = 'unknown';

        try {
            validateTraceId(traceId);

            const tracePath = this.fileManager.getTracePath(
                this.workspaceRoot,
                traceId
            );

            if (!await this.fileExists(tracePath)) {
                errors.push(`Trace file not found: ${traceId}`);
                return { valid: false, errors, warnings, format };
            }

            const content = await this.readFileContent(tracePath);
            const lines = content
                .split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0);

            const parseErrors = this.parser.validateJsonlStructure(lines);

            // Determine format
            if (lines.length === 1) {
                format = 'json';
            } else if (lines.length > 1) {
                format = 'jsonl';
            }

            warnings.push(...parseErrors.warnings);

            const traceData = this.parser.parseJsonlContent(content, traceId);

            if (!traceData && parseErrors.errors.length > 0) {
                errors.push(...parseErrors.errors);
                return { valid: false, errors, warnings, format };
            }

            if (!traceData) {
                errors.push('Failed to parse trace file');
                return { valid: false, errors, warnings, format };
            }

            if (!traceData.id) {
                errors.push('Missing required field: id');
            }
            if (!traceData.workflowId) {
                warnings.push('Missing field: workflowId');
            }
            if (!traceData.runtime) {
                warnings.push('Missing field: runtime');
            }
            if (!traceData.status) {
                errors.push('Missing required field: status');
            }
            if (!traceData.startedAt) {
                errors.push('Missing required field: startedAt');
            }
            if (!traceData.events || !Array.isArray(traceData.events)) {
                errors.push('Missing or invalid field: events (must be an array)');
            }

            if (traceData.events && Array.isArray(traceData.events)) {
                traceData.events.forEach((event, index) => {
                    if (!event.type) {
                        errors.push(`Event ${index}: missing type`);
                    }
                    if (!event.timestamp) {
                        errors.push(`Event ${index}: missing timestamp`);
                    }
                    if (event.sequence === undefined) {
                        warnings.push(`Event ${index}: missing sequence number`);
                    }
                });
            }

            return {
                valid: errors.length === 0,
                errors,
                warnings,
                format
            };
        } catch (error) {
            errors.push(`Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`);
            return { valid: false, errors, warnings, format };
        }
    }

    // ========== Workflow Detection ==========

    /**
     * Detect workflows in the workspace.
     */
    async detectWorkflows(): Promise<WorkflowInfo[]> {
        return this.detector.detectWorkflows(this.workspaceRoot);
    }

    // ========== Runtime Capabilities (arc-adapters) ==========

    /**
     * List runtime capability reports by calling the Python CLI.
     */
    async listRuntimeCapabilities(): Promise<RuntimeCapabilitiesResponse> {
        try {
            const output = execFileSync('arc', [
                'runtimes',
                '--capabilities',
                '--workspace',
                this.workspaceRoot,
                '--json',
            ], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                return parsed.data as RuntimeCapabilitiesResponse;
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                parsed?.error?.message || 'CLI returned no data',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
                `Failed to list capabilities: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    async preflightRun(request: RunPreflightRequest): Promise<RunPreflightResponse> {
        try {
            const args = [
                'run',
                request.workflow || 'crew.py',
                '--runtime',
                request.runtimeId,
                '--profile-id',
                request.profileId || 'local-safe',
                '--workspace',
                this.workspaceRoot,
                '--dry-run',
                '--json',
            ];
            if (request.prompt) {
                args.push('--prompt', request.prompt);
            }
            const paidCallAllowed = request.allowPaidCalls === true;
            if (paidCallAllowed) {
                args.push('--allow-paid-calls');
            }
            const output = execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok || !parsed.data) {
                throw new ArcError(ArcErrorCode.EXECUTION_FAILED, parsed?.error?.message || 'Preflight failed');
            }
            const data = parsed.data;
            const costMetadata = {
                paidCallRequired: Boolean(data.paid_call_required),
                paidCallAllowed,
                providerCall: false as const,
                dryRun: true,
                quota: data.quota || data.provider_quota,
                provider: data.provider,
                estimatedCost: data.estimated_cost || null,
            };
            return {
                workflow: data.workflow,
                runtime: data.runtime,
                profile: data.profile,
                runnable: Boolean(data.runnable),
                blockers: data.blockers || [],
                warnings: data.warnings || [],
                doctorActions: data.doctor_actions || data.doctorActions || [],
                paidCallRequired: costMetadata.paidCallRequired,
                keyRefStatus: data.key_ref_status || {},
                exportTargetStatus: data.export_target_status || {},
                dependencyStatus: data.dependency_status || {},
                dryRun: true,
                providerCall: false,
                costMetadata,
            };
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
                `Failed to preflight run: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    async startRun(request: StartRunRequest): Promise<StartRunResponse> {
        try {
            const args = [
                'run',
                request.workflow || 'crew.py',
                '--runtime',
                request.runtimeId,
                '--profile-id',
                request.profileId || 'local-safe',
                '--workspace',
                this.workspaceRoot,
                '--json',
            ];
            if (request.prompt) {
                args.push('--prompt', request.prompt);
            }
            const paidCallAllowed = request.allowPaidCalls === true;
            if (paidCallAllowed) {
                args.push('--allow-paid-calls');
            }
            const output = execFileSync('arc', args, {
                timeout: 120000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok || !parsed.data) {
                throw new ArcError(ArcErrorCode.EXECUTION_FAILED, parsed?.error?.message || 'Run failed');
            }
            const data = parsed.data;
            return {
                runId: data.id,
                status: data.status,
                runtime: data.runtime,
                tracePath: data.metadata?.trace_path,
                metadata: data.metadata || {},
                costMetadata: {
                    paidCallRequired: Boolean(data.paid_call_required || data.metadata?.paid_call_required),
                    paidCallAllowed,
                    providerCall: false,
                    dryRun: false,
                    quota: data.quota || data.provider_quota || data.metadata?.quota,
                    provider: data.provider || data.metadata?.provider,
                    estimatedCost: data.estimated_cost || data.metadata?.estimated_cost || null,
                },
            };
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
                `Failed to start run: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    /**
     * Get provider configuration status by calling the Python CLI.
     */
    async getProviderStatus(provider: string, baseUrl?: string): Promise<ProviderStatus> {
        try {
            const output = execFileSync('arc', ['providers', 'status', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && Array.isArray(parsed.data)) {
                const found = parsed.data.find((p: { provider: string }) => p.provider === provider);
                if (found) return found as ProviderStatus;
            }
            // Return a default status if provider not found
            return {
                provider,
                baseUrlConfigured: !!baseUrl,
                apiKeyConfigured: false,
                runtimeAvailable: false,
                message: 'Provider not configured',
            };
        } catch (error) {
            return {
                provider,
                baseUrlConfigured: !!baseUrl,
                apiKeyConfigured: false,
                runtimeAvailable: false,
                message: `Status unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    /**
     * Get current workspace status.
     */
    async getWorkspaceStatus(): Promise<{ frontendPath: string; backendPath: string; source: string }> {
        return {
            frontendPath: this.workspaceRoot,
            backendPath: this.workspaceRoot,
            source: 'filesystem',
        };
    }

    // ========== Config Tab Methods (Session B) ==========

    /**
     * Get config status with all secret values stripped.
     * Calls the Python CLI for provider statuses and reads workspace trust state.
     * Gracefully handles unavailable backend by returning degraded state.
     */
    async getConfigStatus(): Promise<ConfigStatus> {
        const trustStatus: TrustStatus = {
            trusted: false,
            workspacePath: this.workspaceRoot,
            trustLevel: 'unknown',
            reason: 'status_unverified',
        };

        const runtimeConfig: SafeRuntimeConfig = {
            defaultRuntime: 'swarmgraph',
            autoDetect: true,
            fallback: 'stub',
            isolation: 'none',
            timeoutSeconds: 300,
            allowPaidCalls: false,
            dryRun: true,
            routingMode: 'manual',
        };

        let providers: SafeProviderKeyStatus[] = [];
        let backendAvailable = true;
        let backendMessage: string | undefined;
        let selectedProfile: string | undefined;

        try {
            const output = execFileSync('arc', ['providers', 'status', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && Array.isArray(parsed.data)) {
                providers = parsed.data.map((p: any) => ({
                    provider: p.provider || 'unknown',
                    displayName: p.display_name || p.provider || 'Unknown',
                    configured: !!p.apiKeyConfigured || !!p.api_key_configured,
                    source: p.apiKeySource || (p.apiKeyConfigured ? 'env' : 'unset'),
                    defaultModel: p.default_model,
                    envOverride: p.api_key_env,
                })) as SafeProviderKeyStatus[];
            }
        } catch (error) {
            backendAvailable = false;
            backendMessage = `Backend unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`;
            providers = [
                { provider: 'openai', displayName: 'OpenAI', configured: false, source: 'unset' },
                { provider: 'anthropic', displayName: 'Anthropic', configured: false, source: 'unset' },
                { provider: 'ollama', displayName: 'Ollama', configured: false, source: 'unset' },
            ];
        }

        try {
            const configOutput = execFileSync('arc', ['config', 'show', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const configParsed = JSON.parse(configOutput);
            if (configParsed.ok && configParsed.data) {
                const data = configParsed.data;
                if (data.runtime) {
                    runtimeConfig.defaultRuntime = data.runtime.default || runtimeConfig.defaultRuntime;
                    runtimeConfig.autoDetect = data.runtime.auto_detect ?? runtimeConfig.autoDetect;
                    runtimeConfig.fallback = data.runtime.fallback || runtimeConfig.fallback;
                }
                if (data.execution) {
                    runtimeConfig.isolation = data.execution.isolation || runtimeConfig.isolation;
                    runtimeConfig.timeoutSeconds = data.execution.timeout_seconds || runtimeConfig.timeoutSeconds;
                    runtimeConfig.allowPaidCalls = data.execution.allow_paid_calls ?? runtimeConfig.allowPaidCalls;
                }
                if (data.providers) {
                    runtimeConfig.dryRun = data.providers.dry_run ?? runtimeConfig.dryRun;
                    runtimeConfig.routingMode = data.providers.routing_mode || runtimeConfig.routingMode;
                }
                if (data.profiles) {
                    selectedProfile = data.profiles.selected_profile || data.profiles.selected || data.profiles.default;
                }
                if (data.workspace) {
                    trustStatus.trustLevel = data.workspace.trust_level || trustStatus.trustLevel;
                    trustStatus.trusted = trustStatus.trustLevel === 'trusted';
                }
            }
        } catch {
            // Config show failed; keep defaults
        }

        return {
            workspace: trustStatus,
            runtime: runtimeConfig,
            providers,
            mode: 'build',
            selectedProfile,
            backendAvailable,
            backendMessage,
        };
    }

    /**
     * Save safe config fields only.
     * Validates that no secret values are included before writing.
     */
    async saveConfig(update: SafeConfigUpdate): Promise<{ success: boolean; message: string }> {
        const safeKeys = SAFE_CONFIG_KEYS;
        const updateKeys = Object.keys(update);

        for (const key of updateKeys) {
            if (!safeKeys.includes(key) || UNSAFE_CONFIG_KEY_PATTERN.test(key)) {
                return {
                    success: false,
                    message: `Rejected unsafe config field: ${key}. Only non-secret fields are allowed.`,
                };
            }
        }

        if (updateKeys.length === 0) {
            return { success: false, message: 'No config fields to update.' };
        }

        try {
            const args = ['config', 'set'];
            if (update.defaultRuntime) {
                args.push(`runtime.default=${update.defaultRuntime}`);
            }
            if (update.mode) {
                args.push(`execution.mode=${update.mode}`);
            }
            if (update.isolation) {
                args.push(`execution.isolation=${update.isolation}`);
            }
            if (update.allowPaidCalls !== undefined) {
                args.push(`execution.allow_paid_calls=${update.allowPaidCalls}`);
            }
            if (update.dryRun !== undefined) {
                args.push(`providers.dry_run=${update.dryRun}`);
            }
            if (update.routingMode) {
                args.push(`providers.routing_mode=${update.routingMode}`);
            }
            if (update.selectedProfile) {
                args.push(`profiles.selected_profile=${update.selectedProfile}`);
            }

            execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });

            return { success: true, message: 'Configuration saved.' };
        } catch (error) {
            return {
                success: false,
                message: `Failed to save config: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async listProfiles(): Promise<ArcProfileInfo[]> {
        try {
            const output = execFileSync('arc', ['profiles', 'list', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            const profiles = Array.isArray(parsed?.data) ? parsed.data : Array.isArray(parsed?.profiles) ? parsed.profiles : [];
            return profiles.map((profile: any) => ({
                id: String(profile.id || profile.profile_id || profile.name || 'unknown'),
                name: String(profile.name || profile.id || profile.profile_id || 'Unknown'),
                mode: profile.mode,
                description: profile.description,
                allowPaidCalls: profile.allow_paid_calls ?? profile.allowPaidCalls,
                dryRun: profile.dry_run ?? profile.dryRun,
                provider: profile.provider,
                runtime: profile.runtime,
            }));
        } catch {
            return [
                { id: 'local-safe', name: 'local-safe', allowPaidCalls: false, dryRun: true },
                { id: 'local-paid', name: 'local-paid', allowPaidCalls: true, dryRun: false },
            ];
        }
    }

    async getIsolationStatus(): Promise<IsolationStatus> {
        try {
            const output = execFileSync('arc', ['isolation', 'status', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            const data = parsed?.data || parsed || {};
            return {
                current: String(data.current || data.provider || data.isolation || 'none'),
                available: data.available !== false,
                providers: this.mapIsolationProviders(data.providers || []),
                message: data.message,
            };
        } catch (error) {
            return {
                current: 'none',
                available: true,
                providers: [{ id: 'none', name: 'None', available: true, active: true }],
                message: `Isolation status unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    async listIsolationProviders(): Promise<IsolationProviderInfo[]> {
        try {
            const output = execFileSync('arc', ['isolation', 'list', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            const providers = Array.isArray(parsed?.data) ? parsed.data : Array.isArray(parsed?.providers) ? parsed.providers : [];
            return this.mapIsolationProviders(providers);
        } catch {
            return [{ id: 'none', name: 'None', available: true, active: true }];
        }
    }

    private mapIsolationProviders(providers: any[]): IsolationProviderInfo[] {
        return providers.map((provider: any) => ({
            id: String(provider.id || provider.name || 'unknown'),
            name: String(provider.display_name || provider.name || provider.id || 'Unknown'),
            available: provider.available !== false,
            active: !!provider.active,
            reason: provider.reason || provider.message,
        }));
    }

    async getProviderCatalog(): Promise<ProviderCatalogEntry[]> {
        const output = execFileSync('arc', ['providers', 'catalog', '--json'], {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        const parsed = JSON.parse(output);
        if (parsed.ok && Array.isArray(parsed.data)) {
            return parsed.data.map((p: any) => ({
                ...p,
                displayName: p.display_name,
                authKind: p.auth_kind,
                credentialLabel: p.credential_label,
                envKeyNames: p.env_key_names,
                defaultBaseUrl: p.default_base_url,
                docsUrl: p.docs_url,
            })) as ProviderCatalogEntry[];
        }
        return [];
    }

    async getProviderDiagnostics(): Promise<ProviderDiagnosticsInfo> {
        try {
            const output = execFileSync('arc', ['providers', 'diagnostics', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok) {
                throw new ArcError(
                    ArcErrorCode.EXECUTION_FAILED,
                    parsed?.error?.message || 'Provider diagnostics failed',
                    { error: parsed?.error }
                );
            }
            return (parsed.data || {}) as ProviderDiagnosticsInfo;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
                `Provider diagnostics unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    async getProviderQuota(provider?: string): Promise<ProviderQuotaInfo> {
        try {
            const args = ['providers', 'quota', 'show'];
            if (provider) {
                args.push('--provider', provider);
            }
            args.push('--json');
            const output = execFileSync('arc', args, {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok) {
                throw new ArcError(
                    ArcErrorCode.EXECUTION_FAILED,
                    parsed?.error?.message || 'Provider quota failed',
                    { error: parsed?.error }
                );
            }
            return (parsed.data || {}) as ProviderQuotaInfo;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
                `Provider quota unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    async resetProviderQuota(): Promise<ProviderQuotaResetResult> {
        try {
            const output = execFileSync('arc', ['providers', 'quota', 'reset', '--json'], {
                timeout: 10000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok) {
                throw new ArcError(
                    ArcErrorCode.EXECUTION_FAILED,
                    parsed?.error?.message || 'Provider quota reset failed',
                    { error: parsed?.error }
                );
            }
            return {
                success: true,
                message:
                    typeof parsed?.data?.message === 'string'
                        ? parsed.data.message
                        : 'Local provider quota counters reset',
            };
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
                `Provider quota reset unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    async runGatedProviderAction(request: GatedProviderActionRequest): Promise<GatedProviderActionResult> {
        const dryRun = request.dryRun !== false;
        const args = ['providers', 'action', '--provider', request.provider, '--prompt', request.prompt, '--json'];
        if (request.model) {
            args.push('--model', request.model);
        }
        if (!dryRun) {
            args.push('--live');
        }
        if (request.allowPaidCalls) {
            args.push('--allow-paid-calls');
        }
        if (request.confirmProviderCall && request.model) {
            args.push('--confirm', `RUN_PROVIDER_ACTION:${request.provider}:${request.model}`);
        }

        try {
            const output = execFileSync('arc', args, {
                timeout: 30000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            return this.mapGatedProviderActionOutput(output, dryRun, request);
        } catch (error: any) {
            const output = String(error?.stdout || error?.stderr || '');
            if (output.trim()) {
                return this.mapGatedProviderActionOutput(output, dryRun, request, true);
            }
            return {
                success: false,
                blocked: true,
                dryRun,
                providerCall: false,
                provider: request.provider,
                model: request.model,
                message: `Provider action unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`,
            };
        }
    }

    private mapGatedProviderActionOutput(
        output: string,
        dryRun: boolean,
        request: GatedProviderActionRequest,
        cliFailed = false
    ): GatedProviderActionResult {
        try {
            const parsed = JSON.parse(output);
            const data = parsed?.data || {};
            const error = parsed?.error;
            const ok = parsed?.ok === true && !cliFailed;
            return {
                success: ok,
                blocked: !ok || data.blocked === true,
                dryRun: data.dry_run ?? dryRun,
                providerCall: data.provider_call === true,
                provider: data.provider || request.provider,
                model: data.model || request.model,
                message: data.message || error?.message || (ok ? 'Provider action completed.' : 'Provider action blocked.'),
                quota: data.quota || data.provider_quota,
                estimatedCost: data.estimated_cost ?? null,
                data,
                error,
            };
        } catch {
            return {
                success: false,
                blocked: true,
                dryRun,
                providerCall: false,
                provider: request.provider,
                model: request.model,
                message: output.trim() || 'Provider action failed.',
            };
        }
    }

    async setProviderKeyRef(request: ProviderKeyRefRequest): Promise<{ success: boolean; message: string }> {
        if (/sk-|bearer\s+|token[:=]|api[_-]?key[:=]/i.test(request.envVar)) {
            return { success: false, message: 'Rejected raw key material. Enter an environment variable name only.' };
        }
        const args = ['providers', 'key', 'set', request.provider, '--env', request.envVar, '--json'];
        if (request.label) {
            args.push('--label', request.label);
        }
        if (request.model) {
            args.push('--model', request.model);
        }
        execFileSync('arc', args, {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        return { success: true, message: `Saved ${request.provider} key reference (${request.envVar}).` };
    }

    async unsetProviderKeyRef(providerOrAccountId: string): Promise<{ success: boolean; message: string }> {
        execFileSync('arc', ['providers', 'key', 'unset', providerOrAccountId, '--json'], {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        return { success: true, message: `Removed provider key reference: ${providerOrAccountId}.` };
    }

    // ========== Run Links Methods (Session B7) ==========

    /**
     * Get cross-linked event chains for a run.
     * Calls the Python CLI to retrieve linked events by stable ID.
     */
    async getRunLinks(runId: string, filter?: string, stableId?: string): Promise<RunLinksResponse> {
        try {
            const args = ['runs', 'links', runId, '--json'];
            if (filter) {
                args.push('--filter', filter);
            }
            if (stableId) {
                args.push('--stable-id', stableId);
            }

            const output = execFileSync('arc', args, {
                timeout: 15000,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                const data = parsed.data;
                return {
                    nodeChains: data.node_chains || {},
                    messageChains: data.message_chains || {},
                    toolCallChains: data.tool_call_chains || {},
                    evidenceChains: data.evidence_chains || {},
                    hasStableIds: !!data.has_stable_ids,
                    stableIdCount: data.stable_id_count || 0,
                };
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                parsed?.error?.message || 'CLI returned no data for run links',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to get run links: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    // ========== Run Details (Cockpit Cards) ==========

    /**
     * Get run receipt for a completed/failed/cancelled run.
     */
    async getRunReceipt(runId: string): Promise<RunReceipt> {
        try {
            validateRunId(runId);
            const receiptPath = path.join(this.workspaceRoot, '.arc', 'receipts', `${runId}.json`);
            const fs = await import('fs-extra');
            if (!await fs.pathExists(receiptPath)) {
                throw new ArcError(ArcErrorCode.TRACE_NOT_FOUND, `No receipt found for run: ${runId}`, { runId });
            }
            const content = await fs.readFile(receiptPath, 'utf-8');
            return JSON.parse(content) as RunReceipt;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read receipt: ${error instanceof Error ? error.message : 'Unknown error'}`,
                { runId }
            );
        }
    }

    /**
     * Get failure autopsy for a failed run. Returns null if no autopsy exists.
     */
    async getRunAutopsy(runId: string): Promise<FailureAutopsy | null> {
        try {
            validateRunId(runId);
            const autopsyPath = path.join(this.workspaceRoot, '.arc', 'autopsies', `${runId}.json`);
            const fs = await import('fs-extra');
            if (!await fs.pathExists(autopsyPath)) {
                return null;
            }
            const content = await fs.readFile(autopsyPath, 'utf-8');
            return JSON.parse(content) as FailureAutopsy;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read autopsy: ${error instanceof Error ? error.message : 'Unknown error'}`,
                { runId }
            );
        }
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
                ArcErrorCode.EXECUTION_FAILED,
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
                ArcErrorCode.EXECUTION_FAILED,
                parsed?.error?.message || 'HITL respond failed',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
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
                ArcErrorCode.EXECUTION_FAILED,
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
                ArcErrorCode.EXECUTION_FAILED,
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
                ArcErrorCode.EXECUTION_FAILED,
                parsed?.error?.message || 'CLI returned no data for run diff',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.EXECUTION_FAILED,
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
                ArcErrorCode.EXECUTION_FAILED,
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
        const baseUrl = request.baseUrl?.trim();
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
            streamUrl = new URL(`/api/runs/${encodeURIComponent(request.runId)}/events`, baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`);
        } catch {
            yield this.activeTraceTerminalChunk(request, 1, 'STREAM_END', 'error', 'Invalid Python web/SSE base URL.');
            return;
        }
        if (streamUrl.protocol !== 'http:' && streamUrl.protocol !== 'https:') {
            yield this.activeTraceTerminalChunk(request, 1, 'STREAM_END', 'error', 'Python web/SSE base URL must use http or https.');
            return;
        }
        if (streamUrl.username || streamUrl.password) {
            yield this.activeTraceTerminalChunk(request, 1, 'STREAM_END', 'error', 'Python web/SSE base URL must not include credentials.');
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
                yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'error', `Live SSE request failed with HTTP ${response.status}.`);
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
            yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'error', error instanceof Error ? error.message : 'Unknown live SSE error');
        } finally {
            clearTimeout(timeout);
            controller.abort();
        }
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

    private extractAuditRecordCount(reason?: string): number {
        if (!reason) {
            return 0;
        }
        const match = reason.match(/verified\s+(\d+)\s+records?/i);
        return match ? Number(match[1]) : 0;
    }
}
