/**
 * ARC Studio Protocol
 * 
 * Defines the RPC protocol between frontend and backend.
 */

export const ArcServicePath = '/services/arc';

/**
 * Symbol for ArcService dependency injection token
 */
export const ArcService = Symbol('ArcService');

// ========== Enums ==========

/**
 * Error codes for ARC protocol operations.
 */
export enum ArcErrorCode {
    INVALID_INPUT       = 'INVALID_INPUT',
    TRACE_NOT_FOUND     = 'TRACE_NOT_FOUND',
    EXECUTION_FAILED    = 'EXECUTION_FAILED',
    PARSE_ERROR         = 'PARSE_ERROR',
    WORKFLOW_NOT_FOUND  = 'WORKFLOW_NOT_FOUND',
    PERMISSION_DENIED   = 'PERMISSION_DENIED',
    TIMEOUT             = 'TIMEOUT',
    UNKNOWN             = 'UNKNOWN'
}

// ========== Error Class ==========

/**
 * Structured error for ARC operations.
 */
export class ArcError extends Error {
    constructor(
        public readonly code: ArcErrorCode,
        message: string,
        public readonly details?: Record<string, any>
    ) {
        super(message);
        this.name = 'ArcError';
        // Restore prototype chain for instanceof checks
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

// ========== Execution ==========

/**
 * Options for workflow execution.
 */
export interface ExecutionOptions {
    /**
     * Backend to use for execution.
     * - 'gateway': Use SwarmGraph gateway with real LLM providers
     * - 'stub': Use stub backend for testing without API calls
     * @default 'gateway'
     */
    backend?: 'gateway' | 'stub';

    /**
     * Whether to allow operations that incur API costs.
     * When false, execution will fail if it would make paid API calls.
     * @default true
     */
    costAllowed?: boolean;

    /**
     * Timeout for execution in milliseconds.
     * @default 300000 (5 minutes)
     */
    timeout?: number;

    /**
     * Workspace root directory for execution.
     * If not provided, uses current working directory.
     */
    workspaceRoot?: string;
}

/**
 * Result of a workflow execution.
 */
export interface ExecutionResult {
    /**
     * Unique identifier for this execution run.
     * Format: 'run-sg-{hash}' for SwarmGraph runs.
     */
    runId: string;

    /**
     * Final execution status.
     */
    status: 'completed' | 'failed' | 'running';

    /**
     * Standard output from the execution (if successful).
     */
    output?: string;

    /**
     * Error message (if failed).
     */
    error?: string;

    /**
     * Path to the trace file relative to workspace root.
     * Format: '.arc/traces/{runId}.jsonl'
     */
    tracePath: string;

    /**
     * Execution duration in milliseconds.
     */
    duration?: number;
}

/**
 * Result of workflow cancellation.
 */
export interface CancelResult {
    success: boolean;
    runId: string;
    message: string;
}

// ========== Traces ==========

/**
 * Metadata for a trace file.
 */
export interface TraceFile {
    /**
     * Unique trace identifier (without .jsonl extension).
     */
    id: string;

    /**
     * Absolute path to the trace file.
     */
    path: string;

    /**
     * ISO 8601 timestamp of when the trace was created.
     */
    timestamp: string;

    /**
     * Execution status from the trace file.
     */
    status: 'completed' | 'failed' | 'unknown';

    /**
     * File size in bytes.
     */
    size?: number;

    /**
     * Number of events in the trace.
     */
    eventCount?: number;
}

/**
 * A single event in a trace file.
 *
 * Events follow the AG-UI event format defined in Phase 2 architectural decisions.
 * Each event represents a discrete action during workflow execution.
 * Trace files are JSONL: one TraceEvent JSON object per line.
 */
export interface TraceEvent {
    /**
     * Type of event.
     * - RUN_STARTED:    Workflow execution began
     * - NODE_COMPLETED: A graph node finished execution
     * - MESSAGE:        A message was sent/received
     * - RUN_COMPLETED:  Workflow execution succeeded
     * - RUN_FAILED:     Workflow execution failed
     * - ERROR:          An error occurred during execution
     */
    type: 'RUN_STARTED' | 'NODE_COMPLETED' | 'MESSAGE' | 'RUN_COMPLETED' | 'RUN_FAILED' | 'ERROR';

    /**
     * ISO 8601 timestamp when the event occurred.
     */
    timestamp: string;

    /**
     * Run ID this event belongs to.
     */
    runId: string;

    /**
     * Sequence number for ordering events (0-indexed).
     */
    sequence: number;

    /**
     * Event-specific data. Structure varies by event type.
     */
    data: Record<string, any>;
}

/**
 * Complete trace data including all events and metadata.
 *
 * Trace files use JSONL format where each line is a TraceEvent.
 * This interface represents the parsed and aggregated trace data.
 */
export interface TraceData {
    /**
     * Unique trace identifier.
     */
    id: string;

    /**
     * Identifier of the workflow that was executed.
     */
    workflowId: string;

    /**
     * Runtime that executed the workflow ('swarmgraph' or 'langgraph').
     */
    runtime: string;

    /**
     * Final execution status.
     */
    status: string;

    /**
     * ISO 8601 timestamp when execution started.
     */
    startedAt: string;

    /**
     * ISO 8601 timestamp when execution ended.
     */
    endedAt?: string;

    /**
     * Array of all events that occurred during execution.
     * Events are ordered by sequence number.
     */
    events: TraceEvent[];

    /**
     * Additional metadata about the execution.
     * May include: model names, token counts, costs, etc.
     */
    metadata: Record<string, any>;
}

/**
 * Result of validating a trace file.
 */
export interface ValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
    /** Detected file format. */
    format: 'json' | 'jsonl' | 'unknown';
}

// ========== Workflows ==========

/**
 * Information about a detected workflow in the workspace.
 */
export interface WorkflowInfo {
    /**
     * Type of workflow runtime.
     */
    type: 'langgraph' | 'swarmgraph';

    /**
     * Absolute path to the workflow file or executable.
     */
    path: string;

    /**
     * Human-readable name of the workflow.
     */
    name: string;

    /**
     * Optional description of the workflow.
     */
    description?: string;
}

// ========== Streaming ==========

/**
 * A streaming trace event chunk delivered during live execution.
 * Used by the frontend to update the graph view in real time.
 */
export interface TraceEventChunk {
    /** The event payload. */
    event: TraceEvent;
    /** True when this is the last event in the stream. */
    done: boolean;
}

// ========== Service Interface ==========

/**
 * Main service interface for ARC Studio backend operations.
 *
 * Implementations handle:
 * - Executing SwarmGraph and LangGraph workflows
 * - Managing trace files in .arc/traces/
 * - Detecting workflow definitions in the workspace
 * - Streaming execution events to the frontend
 */
export interface ArcService {
    /**
     * Execute a SwarmGraph workflow with the given prompt.
     *
     * Spawns a subprocess to run the SwarmGraph CLI and captures
     * the execution trace in JSONL format. The trace file is written to
     * .arc/traces/ and can be retrieved later for visualization.
     *
     * @param prompt   - The user prompt to execute
     * @param options  - Optional execution configuration
     * @returns Promise resolving to execution result with run ID and trace path
     * @throws {ArcError} INVALID_INPUT if prompt is empty or too long
     * @throws {ArcError} EXECUTION_FAILED if the CLI is unavailable
     * @throws {ArcError} TIMEOUT if execution exceeds the configured timeout
     *
     * @example
     * ```typescript
     * const result = await arcService.executeWorkflow(
     *   "What is the weather?",
     *   { backend: 'gateway', costAllowed: true }
     * );
     * console.log(`Run ID: ${result.runId}`);
     * console.log(`Trace: ${result.tracePath}`);
     * ```
     */
    executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult>;

    /**
     * Cancel a running workflow execution.
     *
     * Sends SIGTERM to the subprocess identified by runId.
     *
     * @param runId - The run ID returned by executeWorkflow
     * @returns Promise resolving to cancellation result
     */
    cancelWorkflow(runId: string): Promise<CancelResult>;

    /**
     * Get list of all trace files from .arc/traces/ directory.
     *
     * Returns metadata for each trace file including ID, timestamp, and status.
     * Files are sorted by timestamp (most recent first).
     *
     * @returns Promise resolving to array of trace file metadata
     * @throws {ArcError} UNKNOWN if the traces directory cannot be read
     *
     * @example
     * ```typescript
     * const traces = await arcService.getTraces();
     * traces.forEach(trace => {
     *   console.log(`${trace.id}: ${trace.status} at ${trace.timestamp}`);
     * });
     * ```
     */
    getTraces(): Promise<TraceFile[]>;

    /**
     * Read and parse a specific trace file by ID.
     *
     * Loads the complete trace data including all events, metadata, and
     * execution results. The trace file must exist in .arc/traces/.
     *
     * @param traceId - The trace ID (without .jsonl extension)
     * @returns Promise resolving to complete trace data
     * @throws {ArcError} INVALID_INPUT if traceId is malformed
     * @throws {ArcError} TRACE_NOT_FOUND if the file does not exist
     * @throws {ArcError} PARSE_ERROR if the file cannot be parsed
     *
     * @example
     * ```typescript
     * const trace = await arcService.readTrace('run-sg-abc123');
     * console.log(`Workflow: ${trace.workflowId}`);
     * console.log(`Events: ${trace.events.length}`);
     * ```
     */
    readTrace(traceId: string): Promise<TraceData>;

    /**
     * Stream trace events from a trace file one event at a time.
     *
     * Reads the JSONL file line-by-line and yields each parsed TraceEvent.
     * Useful for large traces where loading all events at once is expensive.
     *
     * @param traceId - The trace ID (without .jsonl extension)
     * @returns Async iterable of TraceEvent objects
     * @throws {ArcError} INVALID_INPUT if traceId is malformed
     * @throws {ArcError} TRACE_NOT_FOUND if the file does not exist
     * @throws {ArcError} PARSE_ERROR if a line cannot be parsed
     */
    streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>>;

    /**
     * Validate the format and content of a trace file.
     *
     * Checks required fields, event structure, and JSONL format compliance.
     *
     * @param traceId - The trace ID (without .jsonl extension)
     * @returns Promise resolving to validation result with errors and warnings
     */
    validateTrace(traceId: string): Promise<ValidationResult>;

    /**
     * Detect workflow definitions in the current workspace.
     *
     * Scans the workspace for:
     * - SwarmGraph CLI installations
     * - LangGraph StateGraph definitions (via AST analysis)
     * - Other supported workflow types
     *
     * @returns Promise resolving to array of detected workflows
     * @throws {ArcError} UNKNOWN if the workspace cannot be scanned
     *
     * @example
     * ```typescript
     * const workflows = await arcService.detectWorkflows();
     * workflows.forEach(wf => {
     *   console.log(`Found ${wf.type} workflow: ${wf.name} at ${wf.path}`);
     * });
     * ```
     */
    detectWorkflows(): Promise<WorkflowInfo[]>;
}
