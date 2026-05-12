/**
 * ARC Studio Protocol
 * 
 * Defines the RPC protocol between frontend and backend.
 */

export const ArcServicePath = '/services/arc';

export interface ArcService {
    /**
     * Execute a SwarmGraph workflow
     */
    executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult>;

    /**
     * Get trace files from .arc/traces/
     */
    getTraces(): Promise<TraceFile[]>;

    /**
     * Read a specific trace file
     */
    readTrace(traceId: string): Promise<TraceData>;

    /**
     * Detect workflows in the workspace
     */
    detectWorkflows(): Promise<WorkflowInfo[]>;
}

export interface ExecutionOptions {
    backend?: 'gateway' | 'stub';
    costAllowed?: boolean;
}

export interface ExecutionResult {
    runId: string;
    status: 'completed' | 'failed';
    output?: string;
    error?: string;
    tracePath: string;
}

export interface TraceFile {
    id: string;
    path: string;
    timestamp: string;
    status: 'completed' | 'failed';
}

export interface TraceData {
    id: string;
    workflowId: string;
    runtime: string;
    status: string;
    startedAt: string;
    endedAt: string;
    events: TraceEvent[];
    metadata: Record<string, any>;
}

export interface TraceEvent {
    type: 'RUN_STARTED' | 'NODE_COMPLETED' | 'MESSAGE' | 'RUN_COMPLETED' | 'RUN_FAILED';
    timestamp: string;
    runId: string;
    sequence: number;
    data: Record<string, any>;
}

export interface WorkflowInfo {
    type: 'langgraph' | 'swarmgraph';
    path: string;
    name: string;
}
