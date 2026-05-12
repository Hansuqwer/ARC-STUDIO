/**
 * ARC Backend Service
 *
 * Implements the ARC service protocol for executing workflows,
 * managing traces, and detecting workflows in the workspace.
 *
 * Phase 3 Enhancements:
 * - Improved command execution with streaming and progress tracking
 * - Robust JSONL trace parser with line-by-line processing
 * - Comprehensive workflow detection (SwarmGraph + LangGraph)
 */

import { injectable } from '@theia/core/shared/inversify';
import {
    ArcService,
    ExecutionOptions,
    ExecutionResult,
    TraceFile,
    TraceData,
    WorkflowInfo,
    ValidationResult,
    CancelResult,
    TraceEvent,
    ArcError,
    ArcErrorCode
} from '../common/arc-protocol';
import {
    sanitizePrompt as strictSanitizePrompt,
    validateTraceId as strictValidateTraceId,
    validateBackend as strictValidateBackend,
    sanitizeErrorMessage as strictSanitizeErrorMessage,
    validateWorkspaceRoot as strictValidateWorkspaceRoot,
} from './security-utils';
import * as fs from 'fs-extra';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';

@injectable()
export class ArcBackendService implements ArcService {
    private workspaceRoot: string;
    private runningProcesses: Map<string, ChildProcess> = new Map();

    constructor() {
        this.workspaceRoot = strictValidateWorkspaceRoot(process.cwd());
    }

    // ========== Public API ==========

    /**
     * Execute a SwarmGraph workflow with enhanced validation and error handling.
     *
     * Improvements over Phase 2:
     * - Validates SwarmGraph CLI availability before execution
     * - Uses proper streaming with output buffering
     * - Captures exit code and stderr for comprehensive error reporting
     * - Extracts run ID from multiple possible formats
     * - Computes proper trace path even on failure
     */
    async executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult> {
        const startTime = Date.now();

        try {
            // Input validation
            this.validatePrompt(prompt);

            // Validate and sanitize options
            const backend = strictValidateBackend(options?.backend || 'gateway');
            const costAllowed = options?.costAllowed !== false;
            const timeout = options?.timeout || 300000;
            const workspaceRoot = options?.workspaceRoot || this.workspaceRoot;

            // Check SwarmGraph CLI availability
            const cliPath = await this.findExecutable('swarmgraph');
            if (!cliPath) {
                throw new ArcError(
                    ArcErrorCode.EXECUTION_FAILED,
                    'SwarmGraph CLI (swarmgraph) not found. Please install SwarmGraph first.',
                    { command: 'swarmgraph' }
                );
            }

            // Sanitize prompt for safe command execution
            const sanitizedPrompt = strictSanitizePrompt(prompt);

            // Build command arguments:
            // swarmgraph swarm --json "<prompt>" [--backend gateway|stub]
            const args = this.buildSwarmArgs(sanitizedPrompt, backend, costAllowed);

            // Generate tentative run ID for tracking
            const tentativeRunId = `run-sg-${Date.now().toString(16)}`;
            this.runningProcesses.set(tentativeRunId, null as any); // placeholder

            // Execute command with streaming support
            const result = await this.executeCommandWithTimeout(
                'swarmgraph',
                args,
                timeout,
                workspaceRoot,
                tentativeRunId
            );

            // Always compute a trace path (even on failure, may have partial trace)
            const tracePath = `.arc/traces/${tentativeRunId}.jsonl`;

            // Parse output to extract definitive run ID
            const runId = this.extractRunId(result.stdout) || tentativeRunId;

            // Determine execution status
            const status = this.determineExecutionStatus(result);

            // Build result
            const duration = Date.now() - startTime;

            if (status === 'failed') {
                return {
                    runId,
                    status: 'failed',
                    error: this.formatErrorMessage(result),
                    tracePath,
                    duration
                };
            }

            return {
                runId,
                status,
                output: this.extractOutput(result.stdout),
                tracePath,
                duration
            };
        } catch (error: any) {
            const duration = Date.now() - startTime;

            if (error instanceof ArcError) {
                // Re-throw validation errors as-is
                if (error.code === ArcErrorCode.INVALID_INPUT) {
                    throw error;
                }
                // Convert execution errors to result
                return {
                    runId: 'failed',
                    status: 'failed',
                    error: error.message,
                    tracePath: '',
                    duration
                };
            }

            return {
                runId: 'failed',
                status: 'failed',
                error: strictSanitizeErrorMessage(error),
                tracePath: '',
                duration
            };
        }
    }

    /**
     * Get all trace files from .arc/traces/ directory.
     *
     * Improvements:
     * - Properly handles malformed JSONL lines (skip, don't fail)
     * - Validates each trace file and includes error count in metadata
     * - Sorts by timestamp descending (most recent first)
     */
     async getTraces(): Promise<TraceFile[]> {
        const startTime = Date.now();
        try {
            const tracesDir = path.join(this.workspaceRoot, '.arc', 'traces');

            if (!await fs.pathExists(tracesDir)) {
                return [];
            }

            const files = await fs.readdir(tracesDir);
            const traces: TraceFile[] = [];

            for (const file of files) {
                if (!file.endsWith('.jsonl')) {
                    continue;
                }

                const filePath = path.join(tracesDir, file);
                const traceFile = await this.readTraceFileMetadata(file, filePath);
                if (traceFile) {
                    traces.push(traceFile);
                }
            }

            const duration = Date.now() - startTime;
            console.log(`[ARC Performance] Loaded ${traces.length} traces in ${duration}ms`);

            return traces.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
        } catch (error) {
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                'Failed to retrieve trace files',
                { error: strictSanitizeErrorMessage(error) }
            );
        }
    }

    /**
     * Read and parse a specific trace file by ID.
     */
     async readTrace(traceId: string): Promise<TraceData> {
        const startTime = Date.now();
        try {
            strictValidateTraceId(traceId);

            const tracePath = path.join(this.workspaceRoot, '.arc', 'traces', `${traceId}.jsonl`);

            if (!await fs.pathExists(tracePath)) {
                throw new ArcError(
                    ArcErrorCode.TRACE_NOT_FOUND,
                    `Trace file not found: ${traceId}`,
                    { traceId, tracePath }
                );
            }

            const content = await fs.readFile(tracePath, 'utf-8');
            const traceData = this.parseJsonlTrace(content, traceId);

            if (!traceData) {
                throw new ArcError(
                    ArcErrorCode.PARSE_ERROR,
                    `Failed to parse trace file: ${traceId}`,
                    { traceId }
                );
            }

            const duration = Date.now() - startTime;
            console.log(`[ARC Performance] Read trace ${traceId} in ${duration}ms (${traceData.events.length} events)`);

            return traceData;
        } catch (error) {
            if (error instanceof ArcError) {
                throw error;
            }
            throw new ArcError(
                ArcErrorCode.UNKNOWN,
                `Failed to read trace: ${traceId}`,
                { error: strictSanitizeErrorMessage(error) }
            );
        }
    }

    /**
     * Stream trace events from a trace file as an async iterable.
     *
     * Uses line-by-line parsing to handle large trace files efficiently.
     */
    async streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>> {
        strictValidateTraceId(traceId);

        const tracePath = path.join(this.workspaceRoot, '.arc', 'traces', `${traceId}.jsonl`);

        if (!await fs.pathExists(tracePath)) {
            throw new ArcError(
                ArcErrorCode.TRACE_NOT_FOUND,
                `Trace file not found: ${traceId}`,
                { traceId }
            );
        }

        // Return async iterable that reads lines one at a time
        return this.streamJsonlEvents(tracePath);
    }

    /**
     * Detect workflows in the workspace.
     *
     * Improvements over Phase 2:
     * - Detects SwarmGraph CLI installations (local + PATH)
     * - Scans for LangGraph StateGraph workflows (Python files)
     * - Returns proper workflow metadata with type-specific details
     */
    async detectWorkflows(): Promise<WorkflowInfo[]> {
        const startTime = Date.now();
        const workflows: WorkflowInfo[] = [];

        try {
            // 1. Detect SwarmGraph CLI
            const swarmStart = Date.now();
            const swarmgraphWorkflows = await this.detectSwarmGraph();
            console.log(`[ARC Performance] SwarmGraph detection: ${Date.now() - swarmStart}ms (${swarmgraphWorkflows.length} found)`);
            workflows.push(...swarmgraphWorkflows);

            // 2. Detect LangGraph workflows
            const langStart = Date.now();
            const langgraphWorkflows = await this.detectLangGraphWorkflows();
            console.log(`[ARC Performance] LangGraph detection: ${Date.now() - langStart}ms (${langgraphWorkflows.length} found)`);
            workflows.push(...langgraphWorkflows);

            const duration = Date.now() - startTime;
            console.log(`[ARC Performance] Total workflow detection: ${duration}ms (${workflows.length} total)`);

            return workflows;
        } catch (error) {
            const duration = Date.now() - startTime;
            console.log(`[ARC Performance] Workflow detection failed after ${duration}ms`);
            console.warn('Failed to detect workflows:', error);
            return workflows;
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
            strictValidateTraceId(traceId);

            const tracePath = path.join(this.workspaceRoot, '.arc', 'traces', `${traceId}.jsonl`);

            if (!await fs.pathExists(tracePath)) {
                errors.push(`Trace file not found: ${traceId}`);
                return { valid: false, errors, warnings, format };
            }

            const content = await fs.readFile(tracePath, 'utf-8');
            const lines = this.splitJsonlLines(content);
            const parseErrors = this.validateJsonlStructure(lines);

            // Determine format
            if (lines.length === 1) {
                format = 'json';
            } else if (lines.length > 1) {
                format = 'jsonl';
            }

            // Collect parse warnings (non-fatal)
            warnings.push(...parseErrors.warnings);

            // Try to parse
            const traceData = this.parseJsonlTrace(content, traceId);

            if (!traceData && parseErrors.errors.length > 0) {
                errors.push(...parseErrors.errors);
                return { valid: false, errors, warnings, format };
            }

            // Validate required fields
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

            // Validate individual events
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
            errors.push(`Validation error: ${strictSanitizeErrorMessage(error)}`);
            return { valid: false, errors, warnings, format };
        }
    }

    /**
     * Cancel a running workflow execution.
     */
    async cancelWorkflow(runId: string): Promise<CancelResult> {
        try {
            const process = this.runningProcesses.get(runId);

            if (!process || (process as any).killed) {
                return {
                    success: false,
                    runId,
                    message: 'No running process found for this run ID'
                };
            }

            process.kill('SIGTERM');
            this.runningProcesses.delete(runId);

            return {
                success: true,
                runId,
                message: 'Workflow execution cancelled'
            };
        } catch (error) {
            return {
                success: false,
                runId,
                message: strictSanitizeErrorMessage(error)
            };
        }
    }

    // ========== SwarmGraph Execution ==========

    /**
     * Build swarmgraph CLI arguments.
     */
    private buildSwarmArgs(prompt: string, backend: string, costAllowed: boolean): string[] {
        return [
            'swarm',
            '--json',
            prompt,
            ...(backend !== 'gateway' ? ['--backend', backend] : []),
            ...(costAllowed ? ['--cost-allowed'] : ['--no-cost'])
        ];
    }

    /**
     * Execute a command with timeout and streaming support.
     *
     * Improvements:
     * - Proper streaming with buffered output
     * - Tracks the child process for cancellation
     * - Handles both SIGTERM and SIGKILL for timeout
     * - Separates stdout/stderr capture
     */
    private executeCommandWithTimeout(
        command: string,
        args: string[],
        timeout: number,
        cwd: string,
        runId: string
    ): Promise<{ stdout: string; stderr: string; exitCode: number; timedOut: boolean }> {
        return new Promise((resolve, reject) => {
            const child = spawn(command, args, {
                cwd,
                shell: false, // Critical: disable shell to prevent command injection
                env: { ...process.env },
                stdio: ['ignore', 'pipe', 'pipe'] // stdin disconnected, capture stdout/stderr
            });

            // Track process for cancellation
            this.runningProcesses.set(runId, child);

            let stdout = '';
            let stderr = '';
            let killed = false;
            let timeoutHandle: NodeJS.Timeout;

            child.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr.on('data', (data) => {
                // SwarmGraph CLI uses stderr for progress/debug info
                // Aggregate it but don't treat it as an error
                stderr += data.toString();
            });

            child.on('close', (code) => {
                clearTimeout(timeoutHandle);
                this.runningProcesses.delete(runId);

                if (killed) {
                    resolve({
                        stdout,
                        stderr,
                        exitCode: 124, // standard timeout exit code
                        timedOut: true
                    });
                } else {
                    resolve({
                        stdout,
                        stderr,
                        exitCode: code ?? 0,
                        timedOut: false
                    });
                }
            });

            child.on('error', (error) => {
                clearTimeout(timeoutHandle);
                this.runningProcesses.delete(runId);
                reject(new ArcError(
                    ArcErrorCode.EXECUTION_FAILED,
                    `Failed to execute command: ${command} ${args.join(' ')}`,
                    { error: error.message, command, args }
                ));
            });

            // Handle timeout with graceful termination first
            timeoutHandle = setTimeout(() => {
                killed = true;
                // Send SIGTERM first (graceful)
                child.kill('SIGTERM');

                // Force kill after 5 seconds if still running
                setTimeout(() => {
                    if (!child.killed) {
                        child.kill('SIGKILL');
                    }
                }, 5000);

                reject(new ArcError(
                    ArcErrorCode.TIMEOUT,
                    `Command execution timed out after ${timeout}ms`,
                    { command, args, timeout }
                ));
            }, timeout);
        });
    }

    /**
     * Validate prompt input.
     */
    private validatePrompt(prompt: string): void {
        if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
            throw new ArcError(
                ArcErrorCode.INVALID_INPUT,
                'Prompt must be a non-empty string',
                { prompt: typeof prompt === 'string' ? prompt.substring(0, 100) : prompt }
            );
        }

        if (prompt.length > 10000) {
            throw new ArcError(
                ArcErrorCode.INVALID_INPUT,
                'Prompt exceeds maximum length of 10000 characters',
                { length: prompt.length, max: 10000 }
            );
        }
    }

    /**
     * Determine execution status from command result.
     */
    private determineExecutionStatus(result: { stdout: string; stderr: string; exitCode: number }): 'completed' | 'failed' | 'running' {
        // Non-zero exit code = failure
        if (result.exitCode !== 0) {
            return 'failed';
        }

        // Check stdout for error indicators in JSON
        try {
            const lines = result.stdout.split('\n').filter(line => line.trim());
            for (const line of lines) {
                if (line.startsWith('{')) {
                    const jsonData = JSON.parse(line);
                    // Status field explicitly marks failure
                    if (jsonData.status === 'failed' || jsonData.status === 'error') {
                        return 'failed';
                    }
                    // SwarmGraph may include error messages in response
                    if (jsonData.error || jsonData.exception) {
                        return 'failed';
                    }
                }
            }
        } catch {
            // JSON parse errors are non-fatal
        }

        return 'completed';
    }

    /**
     * Extract meaningful output from stdout.
     * Strips noisy JSON metadata lines and returns the human-readable result.
     */
    private extractOutput(stdout: string): string {
        const lines = stdout.split('\n').filter(line => line.trim());
        const outputLines: string[] = [];

        for (const line of lines) {
            if (line.startsWith('{')) {
                try {
                    const json = JSON.parse(line);
                    // Extract useful output from JSON
                    if (json.output) {
                        outputLines.push(json.output);
                    }
                    if (json.result) {
                        outputLines.push(json.result);
                    }
                    if (json.message) {
                        outputLines.push(json.message);
                    }
                    if (json.final_output) {
                        outputLines.push(json.final_output);
                    }
                } catch {
                    // Not valid JSON, include as raw line
                    outputLines.push(line);
                }
            } else {
                // Non-JSON lines are included directly
                outputLines.push(line);
            }
        }

        return outputLines.join('\n').trim() || stdout.trim();
    }

    /**
     * Format error message from execution result.
     */
    private formatErrorMessage(result: { stdout: string; stderr: string; exitCode: number }): string {
        // Try to extract error from stdout JSON first
        try {
            const lines = result.stdout.split('\n').filter(line => line.trim());
            for (const line of lines) {
                if (line.startsWith('{')) {
                    const json = JSON.parse(line);
                    if (json.error) {
                        return String(json.error);
                    }
                    if (json.exception) {
                        return String(json.exception);
                    }
                    if (json.message && json.status === 'failed') {
                        return String(json.message);
                    }
                }
            }
        } catch {
            // Fall through to stderr
        }

        // Fall back to stderr if it contains useful info
        const stderr = result.stderr.trim();
        if (stderr && !stderr.includes('DEBUG') && !stderr.includes('INFO')) {
            return stderr;
        }

        return `Workflow execution failed with exit code ${result.exitCode}`;
    }

    // ========== JSONL Trace Parser ==========

    /**
     * Parse a JSONL trace file line by line.
     *
     * Improvements over Phase 2:
     * - Handles malformed lines gracefully (skip with warning)
     * - Supports both single-object JSON and multi-line JSONL
     * - Normalizes field names to protocol format (snake_case → camelCase)
     * - Handles empty lines and blank files
     */
     private parseJsonlTrace(content: string, fallbackId?: string): TraceData | null {
        const startTime = Date.now();
        const lines = this.splitJsonlLines(content);

        if (lines.length === 0) {
            return null;
        }

        let result: TraceData | null = null;

        // Single-line JSON (Phase 2 format): entire trace is one JSON object
        if (lines.length === 1) {
            result = this.parseJsonObject(lines[0], fallbackId);
        } else {
            // Multi-line JSONL: first line = trace header, remaining = events
            // SwarmGraph Phase 2+ format: all trace data on first line with events array
            // LangGraph format: one TraceEvent per line
            const firstLine = lines[0];

            // Check if first line is a complete trace header
            try {
                const first = JSON.parse(firstLine);
                // If it has the standard trace fields, treat as Phase 2+ format
                if (first.id || first.workflow_id || first.workflowId) {
                    result = this.normalizeTraceData(first, fallbackId);
                }
            } catch {
                // First line is not JSON — treat every line as an event (LangGraph style)
            }

            // LangGraph-style: each line is an event
            if (!result) {
                result = this.parseLangGraphStyleJsonl(lines, fallbackId);
            }
        }

        const duration = Date.now() - startTime;
        const eventCount = result?.events?.length || 0;
        console.log(`[ARC Performance] Parsed trace in ${duration}ms (${eventCount} events, ${lines.length} lines)`);

        return result;
    }

    /**
     * Split content into JSONL lines, skipping empty ones.
     */
    private splitJsonlLines(content: string): string[] {
        return content
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);
    }

    /**
     * Parse a single JSON object with error handling.
     */
    private parseJsonObject(line: string, fallbackId?: string): TraceData | null {
        try {
            return this.normalizeTraceData(JSON.parse(line), fallbackId);
        } catch (error) {
            console.warn('Failed to parse JSON line:', error);
            return null;
        }
    }

    /**
     * Normalize trace data from various formats to our TraceData interface.
     *
     * Handles:
     * - snake_case keys from SwarmGraph (workflow_id, started_at, etc.)
     * - camelCase keys from other sources
     * - Missing optional fields
     * - Event array normalization
     */
    private normalizeTraceData(obj: any, fallbackId?: string): TraceData {
        // Normalize ID
        const id = obj.id || obj.runId || obj.run_id || fallbackId || `unknown-${Date.now().toString(16)}`;

        // Normalize events array
        let events: TraceEvent[] = [];
        if (Array.isArray(obj.events)) {
            events = obj.events.map((e: any, idx: number) => this.normalizeTraceEvent(e, idx));
        } else if (Array.isArray(obj.traces)) {
            // Alternative format where events are in 'traces' field
            events = obj.traces.map((e: any, idx: number) => this.normalizeTraceEvent(e, idx));
        }

        // Build normalized trace data
        return {
            id,
            workflowId: obj.workflow_id || obj.workflowId || obj.workflowId || '',
            runtime: obj.runtime || 'swarmgraph',
            status: obj.status || 'unknown',
            startedAt: obj.started_at || obj.startedAt || new Date().toISOString(),
            endedAt: obj.ended_at || obj.endedAt || undefined,
            events,
            metadata: obj.metadata || this.extractMetadata(obj)
        };
    }

    /**
     * Normalize a single trace event.
     */
    private normalizeTraceEvent(obj: any, fallbackIndex: number): TraceEvent {
        return {
            type: obj.type || 'MESSAGE',
            timestamp: obj.timestamp || new Date().toISOString(),
            runId: obj.run_id || obj.runId || '',
            sequence: obj.sequence ?? fallbackIndex,
            data: obj.data || this.extractEventData(obj)
        };
    }

    /**
     * Extract metadata from a trace object, excluding standard fields.
     */
    private extractMetadata(obj: any): Record<string, any> {
        const standardFields = [
            'id', 'run_id', 'runId', 'workflow_id', 'workflowId', 'runtime',
            'status', 'started_at', 'startedAt', 'ended_at', 'endedAt',
            'events', 'traces', 'metadata'
        ];
        const metadata: Record<string, any> = {};
        for (const [key, value] of Object.entries(obj)) {
            if (!standardFields.includes(key)) {
                metadata[key] = value;
            }
        }
        return metadata;
    }

    /**
     * Extract event data from a raw event object.
     */
    private extractEventData(obj: any): Record<string, any> {
        const standardFields = ['type', 'timestamp', 'run_id', 'runId', 'sequence', 'data'];
        const data: Record<string, any> = {};
        for (const [key, value] of Object.entries(obj)) {
            if (!standardFields.includes(key)) {
                data[key] = value;
            }
        }
        return data;
    }

    /**
     * Parse LangGraph-style JSONL where each line is a separate event.
     * Reconstructs the trace header from the first event's run ID.
     */
    private parseLangGraphStyleJsonl(lines: string[], fallbackId?: string): TraceData {
        const events: TraceEvent[] = [];
        let runId = fallbackId || '';

        for (let i = 0; i < lines.length; i++) {
            try {
                const obj = JSON.parse(lines[i]);
                const event = this.normalizeTraceEvent(obj, i);
                events.push(event);

                // Extract run ID from first event if available
                if (i === 0 && !runId) {
                    runId = event.runId || obj.run_id || obj.runId || fallbackId || `run-${Date.now().toString(16)}`;
                }
            } catch (error) {
                console.warn(`Skipping malformed JSONL line ${i + 1}:`, error);
            }
        }

        if (!runId) {
            runId = fallbackId || `run-${Date.now().toString(16)}`;
        }

        // Determine status from events
        const status = this.deriveStatusFromEvents(events);

        return {
            id: runId,
            workflowId: '',
            runtime: 'langgraph',
            status,
            startedAt: events[0]?.timestamp || new Date().toISOString(),
            endedAt: events[events.length - 1]?.timestamp || undefined,
            events,
            metadata: {}
        };
    }

    /**
     * Stream JSONL events from a file using async iteration.
     *
     * Reads the file line by line to support large trace files
     * without loading the entire file into memory.
     */
    private async *streamJsonlEvents(tracePath: string): AsyncIterable<TraceEvent> {
        const readStream = fs.createReadStream(tracePath, { encoding: 'utf-8' });
        let lineBuffer = '';
        let lineIndex = 0;

        for await (const chunk of readStream) {
            lineBuffer += chunk;
            const lines = lineBuffer.split('\n');
            // Keep the last incomplete line in the buffer
            lineBuffer = lines.pop() || '';

            for (const rawLine of lines) {
                const line = rawLine.trim();
                if (!line) continue;

                try {
                    const obj = JSON.parse(line);
                    yield this.normalizeTraceEvent(obj, lineIndex++);
                } catch (error) {
                    console.warn(`Skipping malformed line in ${tracePath}:`, error);
                }
            }
        }

        // Process any remaining content in buffer
        if (lineBuffer.trim()) {
            try {
                const obj = JSON.parse(lineBuffer.trim());
                yield this.normalizeTraceEvent(obj, lineIndex);
            } catch {
                // Ignore final malformed line
            }
        }
    }

    /**
     * Validate JSONL structure without full parsing.
     * Returns errors for malformed lines and warnings for non-standard content.
     */
    private validateJsonlStructure(lines: string[]): { errors: string[]; warnings: string[] } {
        const errors: string[] = [];
        const warnings: string[] = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            try {
                JSON.parse(line);
            } catch (error) {
                errors.push(`Line ${i + 1}: Invalid JSON - ${strictSanitizeErrorMessage(error)}`);
            }
        }

        return { errors, warnings };
    }

    /**
     * Derive trace status from event types.
     */
    private deriveStatusFromEvents(events: TraceEvent[]): string {
        for (const event of events) {
            if (event.type === 'RUN_COMPLETED') return 'completed';
            if (event.type === 'RUN_FAILED' || event.type === 'ERROR') return 'failed';
        }
        return events.length > 0 ? 'running' : 'unknown';
    }

    /**
     * Read trace file metadata (for getTraces listing).
     */
    private async readTraceFileMetadata(file: string, filePath: string): Promise<TraceFile | null> {
        try {
            const stats = await fs.stat(filePath);
            const content = await fs.readFile(filePath, 'utf-8');
            const traceData = this.parseJsonlTrace(content, file.replace('.jsonl', ''));

            if (traceData) {
                return {
                    id: traceData.id || file.replace('.jsonl', ''),
                    path: filePath,
                    timestamp: traceData.startedAt || stats.mtime.toISOString(),
                    status: this.normalizeStatus(traceData.status),
                    size: stats.size,
                    eventCount: traceData.events?.length || 0
                };
            }
        } catch (error) {
            console.warn(`Failed to read trace file ${file}:`, error);
        }

        // Fallback: include file with minimal info
        try {
            const stats = await fs.stat(filePath);
            return {
                id: file.replace('.jsonl', ''),
                path: filePath,
                timestamp: stats.mtime.toISOString(),
                status: 'unknown',
                size: stats.size
            };
        } catch {
            return null;
        }
    }

    /**
     * Normalize status string to expected enum values.
     */
    private normalizeStatus(status: string): 'completed' | 'failed' | 'unknown' {
        if (!status) return 'unknown';
        const s = status.toLowerCase();
        if (s === 'completed' || s === 'success' || s === 'ok') return 'completed';
        if (s === 'failed' || s === 'error' || s === 'failure') return 'failed';
        return 'unknown';
    }

    // ========== Workflow Detection ==========

    /**
     * Detect SwarmGraph CLI installations.
     */
    private async detectSwarmGraph(): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        // 1. Check workspace-local swarmgraph executable
        const localPath = path.join(this.workspaceRoot, 'swarmgraph');
        if (await fs.pathExists(localPath)) {
            workflows.push({
                type: 'swarmgraph',
                path: localPath,
                name: 'SwarmGraph (local)',
                description: 'SwarmGraph workflow execution engine (workspace-local)'
            });
        }

        // 2. Check for swarmgraph package
        const pkgPath = path.join(this.workspaceRoot, 'node_modules', 'swarmgraph');
        if (await fs.pathExists(pkgPath)) {
            workflows.push({
                type: 'swarmgraph',
                path: pkgPath,
                name: 'SwarmGraph (npm package)',
                description: 'SwarmGraph as npm dependency'
            });
        }

        // 3. Check .venv/Scripts or venv/bin for Python-based SwarmGraph
        const venvPaths = [
            path.join(this.workspaceRoot, '.venv', 'Scripts', 'swarmgraph'),
            path.join(this.workspaceRoot, '.venv', 'bin', 'swarmgraph'),
            path.join(this.workspaceRoot, 'venv', 'Scripts', 'swarmgraph'),
            path.join(this.workspaceRoot, 'venv', 'bin', 'swarmgraph')
        ];
        for (const venvPath of venvPaths) {
            if (await fs.pathExists(venvPath)) {
                workflows.push({
                    type: 'swarmgraph',
                    path: venvPath,
                    name: 'SwarmGraph (Python venv)',
                    description: 'SwarmGraph in Python virtual environment'
                });
                break;
            }
        }

        // 4. Check PATH via `which` (only if we haven't already found one)
        if (workflows.length === 0) {
            const whichPath = await this.whichExecutable('swarmgraph');
            if (whichPath) {
                workflows.push({
                    type: 'swarmgraph',
                    path: whichPath,
                    name: 'SwarmGraph (PATH)',
                    description: 'SwarmGraph CLI in system PATH'
                });
            }
        }

        return workflows;
    }

    /**
     * Detect LangGraph StateGraph workflows by scanning Python files.
     *
     * Scans for:
     * - `from langgraph.graph import StateGraph` imports
     * - `import langgraph` patterns
     * - StateGraph instantiation patterns
     * Returns metadata for each workflow file found.
     */
    private async detectLangGraphWorkflows(): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        try {
            // Scan Python files in the workspace
            const pyFiles = await this.findPythonFiles(this.workspaceRoot);

            for (const pyFile of pyFiles) {
                const workflowInfo = await this.analyzePythonWorkflow(pyFile);
                if (workflowInfo) {
                    workflows.push(workflowInfo);
                }
            }
        } catch (error) {
            console.warn('Failed to scan for LangGraph workflows:', error);
        }

        return workflows;
    }

    /**
     * Find all Python files in the workspace (recursive, excluding common ignore dirs).
     */
    private async findPythonFiles(dir: string): Promise<string[]> {
        const ignoreDirs = new Set(['node_modules', '.git', '__pycache__', '.venv', 'venv', '.arc', 'docs', 'scripts']);
        const results: string[] = [];

        const entries = await fs.readdir(dir, { withFileTypes: true });

        for (const entry of entries) {
            if (!entry.isDirectory()) {
                if (entry.name.endsWith('.py')) {
                    results.push(path.join(dir, entry.name));
                }
                continue;
            }

            // Skip ignored directories
            if (ignoreDirs.has(entry.name)) continue;

            const subResults = await this.findPythonFiles(path.join(dir, entry.name));
            results.push(...subResults);
        }

        return results;
    }

    /**
     * Analyze a Python file to detect if it's a LangGraph workflow.
     *
     * Uses content-based pattern matching (no AST parsing to avoid dependency on Python parser).
     * Detects:
     * - Import statements for langgraph components
     * - StateGraph, CompiledStateGraph instantiation
     * - Workflow compilation patterns
     */
    private async analyzePythonWorkflow(filePath: string): Promise<WorkflowInfo | null> {
        try {
            const content = await fs.readFile(filePath, 'utf-8');

            // Quick check: does the file mention langgraph?
            if (!content.includes('langgraph')) {
                return null;
            }

            // Check for StateGraph import (the key indicator)
            const hasStateGraphImport = this.matchPattern(content, [
                /from\s+langgraph\.graph\s+import\s+[\s\S]*StateGraph/,
                /from\s+langgraph\s+import\s+[\s\S]*StateGraph/,
                /import\s+langgraph\.graph[\s\S]*StateGraph/,
            ]);

            if (!hasStateGraphImport) {
                return null;
            }

            // Extract workflow name from file
            const name = this.extractWorkflowName(filePath, content);

            // Detect if workflow is compiled (has .compile() call = executable)
            const isCompiled = this.matchPattern(content, [
                /\.compile\s*\(/,
            ]);

            // Detect checkpointer/persistence usage
            const hasPersistence = this.matchPattern(content, [
                /checkpointer/i,
                /MemorySaver/i,
                /SqliteSaver/i,
                /PostgresSaver/i,
            ]);

            // Detect multi-agent patterns
            const hasMultiAgent = this.matchPattern(content, [
                /agent.*node/i,
                /swarm.*node/i,
                /multi.*agent/i,
            ]);

            return {
                type: 'langgraph',
                path: filePath,
                name,
                description: this.buildWorkflowDescription(isCompiled, hasPersistence, hasMultiAgent)
            };
        } catch (error) {
            return null;
        }
    }

    /**
     * Check if any pattern matches in content.
     */
    private matchPattern(content: string, patterns: RegExp[]): boolean {
        return patterns.some(pattern => pattern.test(content));
    }

    /**
     * Extract a human-readable workflow name from file path and content.
     */
    private extractWorkflowName(filePath: string, content: string): string {
        // Try to find a variable name assigned to StateGraph(...)
        const classMatch = content.match(/(\w+)\s*=\s*StateGraph\s*\(/);
        if (classMatch) {
            return classMatch[1];
        }

        // Try to find __name__ variable
        const nameMatch = content.match(/__name__\s*=\s*['"]([^'"]+)['"]/);
        if (nameMatch) {
            return nameMatch[1];
        }

        // Fall back to file name without extension
        return path.basename(filePath, '.py');
    }

    /**
     * Build a description string based on detected workflow features.
     */
    private buildWorkflowDescription(isCompiled: boolean, hasPersistence: boolean, hasMultiAgent: boolean): string {
        const parts: string[] = [];
        parts.push('LangGraph StateGraph workflow');

        if (!isCompiled) {
            parts.push('(not compiled)');
        }
        if (hasPersistence) {
            parts.push('with persistence');
        }
        if (hasMultiAgent) {
            parts.push('multi-agent');
        }

        return parts.join(' ');
    }

    /**
     * Find an executable in PATH.
     */
    private async whichExecutable(name: string): Promise<string | null> {
        try {
            const { stdout } = await this.executeCommandWithTimeout(
                'which',
                [name],
                5000,
                this.workspaceRoot,
                'which'
            );
            const execPath = stdout.trim();
            if (execPath && await fs.pathExists(execPath)) {
                return execPath;
            }
        } catch {
            // Not found
        }
        return null;
    }

    // ========== General Utilities ==========

    /**
     * Find executable in workspace or PATH.
     */
    private async findExecutable(name: string): Promise<string | null> {
        // Check in workspace
        const localPath = path.join(this.workspaceRoot, name);
        if (await fs.pathExists(localPath)) {
            return localPath;
        }

        return this.whichExecutable(name);
    }

    /**
     * Extract run ID from command output.
     */
    private extractRunId(output: string): string | null {
        // Try JSON fields first
        try {
            const lines = output.split('\n').filter(line => line.trim());
            for (const line of lines) {
                if (line.startsWith('{')) {
                    const jsonData = JSON.parse(line);
                    if (jsonData.id) return String(jsonData.id);
                    if (jsonData.run_id) return String(jsonData.run_id);
                    if (jsonData.runId) return String(jsonData.runId);
                }
            }
        } catch {
            // Fall through to regex
        }

        // Fallback to regex
        const runIdMatch = output.match(/run-sg-([a-f0-9]+)/);
        if (runIdMatch) {
            return `run-sg-${runIdMatch[1]}`;
        }

        return null;
    }
}