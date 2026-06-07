/**
 * RunLifecycleService - Run execution and trace management
 * 
 * Handles:
 * - Workflow execution and cancellation
 * - Run preflight and start
 * - Trace reading, streaming, validation
 * - Active trace streaming (live SSE and replay)
 * - Workflow detection
 * - Runtime capabilities
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import {
    ExecutionOptions,
    ExecutionResult,
    TraceFile,
    TraceData,
    TraceEvent,
    WorkflowInfo,
    ValidationResult,
    CancelResult,
    RuntimeCapabilitiesResponse,
    RunPreflightRequest,
    RunPreflightResponse,
    StartRunRequest,
    StartRunResponse,
    ActiveTraceStreamRequest,
    ActiveTraceEventChunk,
    ArcError,
    ArcErrorCode,
    ReplayResult,
    ReplayEvent,
} from '../../common/arc-protocol';
import { WorkflowExecutor } from './workflow-executor';
import { TraceParser } from './trace-parser';
import { WorkflowDetector } from './workflow-detector';
import { FileManager } from './file-manager';
import { execArcCliAsync } from './arc-cli-utils';
import { validateTraceId, validateRunId } from '../security-utils';

const ARC_PYTHON_DAEMON_URL_ENV = 'ARC_PYTHON_DAEMON_URL';

@injectable()
export class RunLifecycleService {
    private readonly activeStreamCancels = new Map<string, { cancelled: boolean }>();

    constructor(
        @inject(WorkflowExecutor) private readonly executor: WorkflowExecutor,
        @inject(TraceParser) private readonly parser: TraceParser,
        @inject(WorkflowDetector) private readonly detector: WorkflowDetector,
        @inject(FileManager) private readonly fileManager: FileManager,
        @inject('WorkspaceRoot') private readonly workspaceRoot: string
    ) {}

    // ========== Workflow Execution ==========

    async executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult> {
        await this.fileManager.ensureTracesDir(this.workspaceRoot);
        return this.executor.executeWorkflow(prompt, {
            ...options,
            workspaceRoot: this.workspaceRoot
        });
    }

    async cancelWorkflow(runId: string): Promise<CancelResult> {
        return this.executor.cancelWorkflow(runId);
    }

    // ========== Trace Management ==========

    async getTraces(): Promise<TraceFile[]> {
        return this.fileManager.getTraceFiles(this.workspaceRoot);
    }

    async readTrace(traceId: string): Promise<TraceData> {
        try {
            const tracePath = this.fileManager.getTracePath(
                this.workspaceRoot,
                traceId
            );

            const result = await this.parser.parseTrace(tracePath, traceId);
            if (!result) {
                throw new ArcError(
                    ArcErrorCode.INVALID_INPUT,
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

    async streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>> {
        try {
            validateTraceId(traceId);

            const tracePath = this.fileManager.getTracePath(
                this.workspaceRoot,
                traceId
            );

            // Check file exists before returning iterable
            if (!await this.fileExists(tracePath)) {
                throw new ArcError(
                    ArcErrorCode.RUN_NOT_FOUND,
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

    async readActiveTraceStream(request: ActiveTraceStreamRequest): Promise<ActiveTraceEventChunk[]> {
        const stream = await this.streamActiveTrace(request);
        const chunks: ActiveTraceEventChunk[] = [];
        for await (const chunk of stream) {
            chunks.push(chunk);
        }
        return chunks;
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

    async detectWorkflows(): Promise<WorkflowInfo[]> {
        return this.detector.detectWorkflows(this.workspaceRoot);
    }

    // ========== Runtime Capabilities ==========

    async listRuntimeCapabilities(): Promise<RuntimeCapabilitiesResponse> {
        try {
            const output = await execArcCliAsync([
                'runtimes',
                '--capabilities',
                '--workspace',
                this.workspaceRoot,
                '--json',
            ], {
                timeout: 10000,
            });
            const parsed = JSON.parse(output);
            if (parsed.ok && parsed.data) {
                return {
                    ...parsed.data,
                    runtimes: (parsed.data.runtimes || []).map((runtime: any) => this.mapRuntimeCapability(runtime)),
                } as RuntimeCapabilitiesResponse;
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                parsed?.error?.message || 'CLI returned no data',
            );
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
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
            const output = await execArcCliAsync(args, {
                timeout: 10000,
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok || !parsed.data) {
                throw new ArcError(ArcErrorCode.RUN_FAILED, parsed?.error?.message || 'Preflight failed');
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
                ArcErrorCode.RUN_FAILED,
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
            const output = await execArcCliAsync(args, {
                timeout: 120000,
            });
            const parsed = JSON.parse(output);
            if (!parsed.ok || !parsed.data) {
                throw new ArcError(ArcErrorCode.RUN_FAILED, parsed?.error?.message || 'Run failed');
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
                ArcErrorCode.RUN_FAILED,
                `Failed to start run: ${error instanceof Error ? error.message : 'Unknown error'}`,
            );
        }
    }

    // ========== Private Helper Methods ==========

    private async fileExists(filePath: string): Promise<boolean> {
        const fs = await import('fs-extra');
        return fs.pathExists(filePath);
    }

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

        const maxRetries = 5;
        const baseRetryMs = 2000;
        let lastEventId = request.lastEventId ?? 0;
        let retryCount = 0;

        while (retryCount <= maxRetries && !cancelToken.cancelled) {
            if (Date.now() - startedAt > timeoutMs) {
                yield this.activeTraceTerminalChunk(request, 1, 'STREAM_END', 'error', 'Stream timed out.');
                return;
            }

            if (retryCount > 0 && lastEventId > 0) {
                const jitterMs = Math.random() * 1000;
                const delayMs = Math.min(baseRetryMs * Math.pow(2, retryCount - 1) + jitterMs, 30000);
                await new Promise(resolve => setTimeout(resolve, delayMs));
                yield {
                    runId: request.runId,
                    mode: 'live',
                    sequence: 1,
                    status: {
                        runId: request.runId,
                        mode: 'live',
                        state: 'reconnecting',
                        message: `Reconnecting (attempt ${retryCount}/${maxRetries}, last event ${lastEventId})...`,
                        baseUrlConfigured: true,
                        timestamp: new Date().toISOString(),
                    },
                    done: false,
                };
            }

            let streamUrl: URL;
            try {
                streamUrl = this.buildPythonDaemonStreamUrl(baseUrl, request.runId);
            } catch (error) {
                yield this.activeTraceTerminalChunk(request, 1, 'STREAM_END', 'error', 'Invalid Python web/SSE base URL.');
                return;
            }
            streamUrl.searchParams.set('mode', 'live');
            if (lastEventId > 0) {
                streamUrl.searchParams.set('last_event_id', String(lastEventId));
            }

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
                    retryCount += 1;
                    if (retryCount > maxRetries) {
                        yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'disconnected', `Live SSE proxy degraded; Python daemon returned HTTP ${response.status} after ${maxRetries} retries.`);
                        return;
                    }
                    continue;
                }
                retryCount = 0;

                if (lastEventId === 0) {
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
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let streamEnded = false;
                while (!cancelToken.cancelled && !streamEnded) {
                    if (Date.now() - startedAt > timeoutMs) {
                        controller.abort();
                        yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'error', 'Stream timed out.');
                        return;
                    }
                    const { done, value } = await reader.read();
                    if (done) {
                        streamEnded = true;
                        break;
                    }
                    buffer += decoder.decode(value, { stream: true });
                    const frames = buffer.split(/\r?\n\r?\n/);
                    buffer = frames.pop() ?? '';
                    for (const frame of frames) {
                        const event = this.parseSseEvent(frame);
                        if (!event) continue;

                        const frameEventId = this.parseSseEventId(frame);
                        if (frameEventId > 0) {
                            lastEventId = frameEventId;
                        }

                        const terminal = this.activeTraceTerminalFromEventType(String(event.type ?? ''));
                        yield { runId: request.runId, mode: 'live', sequence: sequence++, event, terminal, done: false };
                        if (terminal) {
                            yield this.activeTraceTerminalChunk(request, sequence, terminal, 'ended', 'Live SSE stream ended.');
                            return;
                        }
                    }
                }
                if (streamEnded) {
                    yield this.activeTraceTerminalChunk(
                        request,
                        sequence,
                        'STREAM_END',
                        'ended',
                        'Live SSE stream ended.'
                    );
                    return;
                }
            } catch (error) {
                retryCount += 1;
                if (retryCount > maxRetries) {
                    yield this.activeTraceTerminalChunk(request, sequence, 'STREAM_END', 'disconnected', `Live SSE proxy degraded; ${error instanceof Error ? error.message : 'Unknown live SSE error'} after ${maxRetries} retries.`);
                    return;
                }
            } finally {
                clearTimeout(timeout);
                controller.abort();
            }
        }
    }

    private parseSseEventId(frame: string): number {
        const idMatch = frame.match(/^id:\s*(\d+)/m);
        if (idMatch) {
            return parseInt(idMatch[1], 10);
        }
        return 0;
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

    private async replayRun(runId: string): Promise<ReplayResult> {
        try {
            const output = await execArcCliAsync(['runs', 'replay', runId, '--workspace', this.workspaceRoot, '--json'], {
                timeout: 30000,
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
}
