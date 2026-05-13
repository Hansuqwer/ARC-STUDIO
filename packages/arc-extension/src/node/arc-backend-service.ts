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
    ArcErrorCode
} from '../common/arc-protocol';
import { validateWorkspaceRoot, validateTraceId } from './security-utils';
import { WorkflowExecutor } from './services/workflow-executor';
import { TraceParser } from './services/trace-parser';
import { WorkflowDetector } from './services/workflow-detector';
import { FileManager } from './services/file-manager';

@injectable()
export class ArcBackendService implements ArcService {
    private readonly executor: WorkflowExecutor;
    private readonly parser: TraceParser;
    private readonly detector: WorkflowDetector;
    private readonly fileManager: FileManager;
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
}
