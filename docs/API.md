# ARC Studio API Documentation

**Version:** 0.1.0  
**Last Updated:** 2026-05-13  
**Status:** Phase 6 - Alpha Acceptance

---

## Overview

ARC Studio provides two API layers for interacting with agent workflows:

1. **JSON-RPC Protocol** — Frontend-to-backend communication within Theia
2. **REST API** — HTTP endpoints for external tools, the daemon, and testing

Both APIs provide the same core functionality: executing workflows, managing traces, and detecting workflow definitions.

---

## JSON-RPC Protocol

The JSON-RPC protocol is used for communication between the Theia frontend and backend.

### Service Path

```
/services/arc
```

### Interface: `ArcService`

Location: `packages/arc-extension/src/common/arc-protocol.ts`

The `ArcService` interface defines **7 methods**:

| # | Method | Description |
|---|--------|-------------|
| 1 | `executeWorkflow()` | Execute a SwarmGraph workflow |
| 2 | `cancelWorkflow()` | Cancel a running workflow |
| 3 | `getTraces()` | List all trace files |
| 4 | `readTrace()` | Read a complete trace file |
| 5 | `streamTrace()` | Stream trace events one at a time |
| 6 | `validateTrace()` | Validate trace file format |
| 7 | `detectWorkflows()` | Detect workflow definitions in workspace |

---

### Method: `executeWorkflow`

```typescript
executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult>
```

Execute a SwarmGraph workflow with the given prompt.

**Parameters:**
- `prompt` (string) — The user prompt to execute
- `options` (ExecutionOptions, optional) — Execution configuration
  - `backend` ('gateway' | 'stub') — Backend type (default: 'gateway')
  - `costAllowed` (boolean) — Allow operations with API costs (default: true)
  - `timeout` (number) — Timeout in milliseconds (default: 300000)
  - `workspaceRoot` (string) — Workspace directory (default: cwd)

**Returns:** `Promise<ExecutionResult>`
- `runId` (string) — Unique run identifier (format: 'run-sg-{hash}')
- `status` ('completed' | 'failed' | 'running') — Execution status
- `output` (string, optional) — Standard output if successful
- `error` (string, optional) — Error message if failed
- `tracePath` (string) — Path to trace file
- `duration` (number, optional) — Execution duration in ms

**Throws:**
- `ArcError(INVALID_INPUT)` — Prompt is empty or exceeds 10,000 characters
- `ArcError(EXECUTION_FAILED)` — SwarmGraph CLI not available
- `ArcError(TIMEOUT)` — Execution exceeded configured timeout

**Example:**
```typescript
const result = await arcService.executeWorkflow(
  "What is the weather in Paris?",
  { backend: 'gateway', costAllowed: true }
);
console.log(`Run ID: ${result.runId}`);
console.log(`Trace: ${result.tracePath}`);
```

---

### Method: `cancelWorkflow`

```typescript
cancelWorkflow(runId: string): Promise<CancelResult>
```

Cancel a running workflow by sending SIGTERM to the subprocess.

**Parameters:**
- `runId` (string) — The run ID returned by `executeWorkflow`

**Returns:** `Promise<CancelResult>`
- `success` (boolean) — Whether cancellation succeeded
- `runId` (string) — The run ID that was cancelled
- `message` (string) — Human-readable status message

**Example:**
```typescript
const cancelResult = await arcService.cancelWorkflow('run-sg-abc123');
if (cancelResult.success) {
  console.log('Workflow cancelled');
}
```

---

### Method: `getTraces`

```typescript
getTraces(): Promise<TraceFile[]>
```

Get list of all trace files from `.arc/traces/` directory.

**Returns:** `Promise<TraceFile[]>` — Array sorted by timestamp (newest first)
- `id` (string) — Trace identifier
- `path` (string) — Absolute path to trace file
- `timestamp` (string) — ISO 8601 timestamp
- `status` ('completed' | 'failed' | 'unknown') — Execution status
- `size` (number, optional) — File size in bytes
- `eventCount` (number, optional) — Number of events in trace

**Throws:**
- `ArcError(UNKNOWN)` — Traces directory cannot be read

**Example:**
```typescript
const traces = await arcService.getTraces();
traces.forEach(trace => {
  console.log(`${trace.id}: ${trace.status} at ${trace.timestamp}`);
});
```

---

### Method: `readTrace`

```typescript
readTrace(traceId: string): Promise<TraceData>
```

Read and parse a complete trace file by ID.

**Parameters:**
- `traceId` (string) — Trace ID (without .jsonl extension)

**Returns:** `Promise<TraceData>`
- `id` (string) — Trace identifier
- `workflowId` (string) — Workflow identifier
- `runtime` (string) — Runtime type ('swarmgraph' or 'langgraph')
- `status` (string) — Final execution status
- `startedAt` (string) — ISO 8601 start timestamp
- `endedAt` (string, optional) — ISO 8601 end timestamp
- `events` (TraceEvent[]) — All execution events
- `metadata` (Record<string, any>) — Additional metadata

**Throws:**
- `ArcError(INVALID_INPUT)` — traceId is malformed
- `ArcError(TRACE_NOT_FOUND)` — File does not exist
- `ArcError(PARSE_ERROR)` — File cannot be parsed

**Example:**
```typescript
const trace = await arcService.readTrace('run-sg-abc123');
console.log(`Workflow: ${trace.workflowId}`);
console.log(`Events: ${trace.events.length}`);
```

---

### Method: `streamTrace`

```typescript
streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>>
```

Stream trace events from a file one at a time. Reads JSONL line-by-line for memory efficiency with large traces.

**Parameters:**
- `traceId` (string) — Trace ID (without .jsonl extension)

**Returns:** `Promise<AsyncIterable<TraceEvent>>` — Async iterable of events

**Throws:**
- `ArcError(INVALID_INPUT)` — traceId is malformed
- `ArcError(TRACE_NOT_FOUND)` — File does not exist
- `ArcError(PARSE_ERROR)` — A line cannot be parsed

**Example:**
```typescript
const events = await arcService.streamTrace('run-sg-abc123');
for await (const event of events) {
  console.log(`${event.type} at ${event.timestamp}`);
}
```

---

### Method: `validateTrace`

```typescript
validateTrace(traceId: string): Promise<ValidationResult>
```

Validate the format and content of a trace file. Checks required fields, event structure, and JSONL compliance.

**Parameters:**
- `traceId` (string) — Trace ID (without .jsonl extension)

**Returns:** `Promise<ValidationResult>`
- `valid` (boolean) — Whether the trace is valid
- `errors` (string[]) — List of validation errors
- `warnings` (string[]) — List of non-fatal warnings
- `format` ('json' | 'jsonl' | 'unknown') — Detected file format

**Example:**
```typescript
const result = await arcService.validateTrace('run-sg-abc123');
if (!result.valid) {
  console.error('Validation errors:', result.errors);
}
```

---

### Method: `detectWorkflows`

```typescript
detectWorkflows(): Promise<WorkflowInfo[]>
```

Detect workflow definitions in the current workspace. Scans for:
- SwarmGraph CLI installations (local, venv, npm, PATH)
- LangGraph StateGraph definitions (via Python file analysis)

**Returns:** `Promise<WorkflowInfo[]>`
- `type` ('langgraph' | 'swarmgraph') — Runtime type
- `path` (string) — Absolute path to workflow
- `name` (string) — Human-readable name
- `description` (string, optional) — Workflow description

**Throws:**
- `ArcError(UNKNOWN)` — Workspace cannot be scanned

**Example:**
```typescript
const workflows = await arcService.detectWorkflows();
workflows.forEach(wf => {
  console.log(`Found ${wf.type} workflow: ${wf.name} at ${wf.path}`);
});
```

---

## Type Definitions

### ExecutionOptions

```typescript
interface ExecutionOptions {
  backend?: 'gateway' | 'stub';
  costAllowed?: boolean;
  timeout?: number;
  workspaceRoot?: string;
}
```

### ExecutionResult

```typescript
interface ExecutionResult {
  runId: string;
  status: 'completed' | 'failed' | 'running';
  output?: string;
  error?: string;
  tracePath: string;
  duration?: number;
}
```

### CancelResult

```typescript
interface CancelResult {
  success: boolean;
  runId: string;
  message: string;
}
```

### TraceFile

```typescript
interface TraceFile {
  id: string;
  path: string;
  timestamp: string;
  status: 'completed' | 'failed' | 'unknown';
  size?: number;
  eventCount?: number;
}
```

### TraceEvent

```typescript
interface TraceEvent {
  type: 'RUN_STARTED' | 'NODE_COMPLETED' | 'MESSAGE' | 'RUN_COMPLETED' | 'RUN_FAILED' | 'ERROR';
  timestamp: string;
  runId: string;
  sequence: number;
  data: Record<string, any>;
}
```

### TraceData

```typescript
interface TraceData {
  id: string;
  workflowId: string;
  runtime: string;
  status: string;
  startedAt: string;
  endedAt?: string;
  events: TraceEvent[];
  metadata: Record<string, any>;
}
```

### ValidationResult

```typescript
interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  format: 'json' | 'jsonl' | 'unknown';
}
```

### WorkflowInfo

```typescript
interface WorkflowInfo {
  type: 'langgraph' | 'swarmgraph';
  path: string;
  name: string;
  description?: string;
}
```

---

## ArcError Codes

### TypeScript (`ArcErrorCode` enum)

Location: `packages/arc-extension/src/common/arc-protocol.ts`

| Code | Description |
|------|-------------|
| `INVALID_INPUT` | Invalid or malformed user input |
| `TRACE_NOT_FOUND` | Requested trace file does not exist |
| `EXECUTION_FAILED` | Workflow execution failed |
| `PARSE_ERROR` | Failed to parse trace file or JSON |
| `WORKFLOW_NOT_FOUND` | Requested workflow not found |
| `PERMISSION_DENIED` | Insufficient permissions |
| `TIMEOUT` | Operation exceeded timeout |
| `UNKNOWN` | Unexpected error |

### Python (`ArcErrorCode` enum)

Location: `python/src/agent_runtime_cockpit/protocol/errors.py`

| Code | Description |
|------|-------------|
| `WORKSPACE_NOT_FOUND` | Workspace directory does not exist |
| `NO_RUNTIME_DETECTED` | No agent runtime detected in workspace |
| `ADAPTER_ERROR` | Adapter operation failed |
| `ADAPTER_NOT_SUPPORTED` | Adapter does not support requested operation |
| `SCHEMA_EXPORT_FAILED` | Schema export failed |
| `WORKFLOW_EXPORT_FAILED` | Workflow export failed |
| `RUN_FAILED` | Workflow run failed |
| `RUN_NOT_FOUND` | Requested run not found |
| `CONTEXT_PROVIDER_ERROR` | Context provider failed |
| `CONFORMANCE_FAILED` | Conformance test failed |
| `INVALID_INPUT` | Invalid or malformed input |
| `INTERNAL_ERROR` | Internal server error |
| `TIMEOUT` | Operation timed out |
| `NOT_IMPLEMENTED` | Feature not implemented |

### ArcError Class

```typescript
class ArcError extends Error {
  constructor(
    public readonly code: ArcErrorCode,
    message: string,
    public readonly details?: Record<string, any>
  );
}
```

---

## REST API

### Legacy FastAPI Server (Port 8000)

Location: `python/src/routes.py`

Base URL: `http://localhost:8000`

#### `GET /`

Health check.

**Response 200:**
```json
{ "status": "ok", "service": "ARC Studio Backend" }
```

---

#### `POST /api/execute`

Execute a SwarmGraph workflow.

**Request Body:**
```json
{
  "prompt": "What is the weather in Paris?",
  "backend": "gateway",
  "cost_allowed": true
}
```

**Parameters:**
- `prompt` (string, required) — User prompt
- `backend` (string, optional) — 'gateway' or 'stub' (default: 'gateway')
- `cost_allowed` (boolean, optional) — Allow API costs (default: true)

**Response 200:**
```json
{
  "run_id": "run-sg-abc123",
  "status": "completed",
  "output": "...",
  "trace_path": ".arc/traces/run-sg-abc123.jsonl"
}
```

**Errors:**
- `400` — Invalid input (SecurityError)
- `408` — Execution timeout (5 minutes)
- `500` — Execution failed

**Example:**
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "backend": "stub"}'
```

---

#### `GET /api/traces`

List all trace files.

**Response 200:**
```json
[
  {
    "id": "run-sg-abc123",
    "path": "/workspace/.arc/traces/run-sg-abc123.jsonl",
    "timestamp": "2026-05-12T20:30:00Z",
    "status": "completed"
  }
]
```

---

#### `GET /api/traces/{trace_id}`

Get a specific trace.

**Response 200:** Full trace JSON object

**Errors:**
- `400` — Invalid trace ID
- `404` — Trace not found
- `500` — Parse error

---

### Daemon Server (Port 7777)

Location: `python/src/agent_runtime_cockpit/web/routes.py`

Base URL: `http://localhost:7777`

CORS is restricted to `http://localhost:3000`.

#### `GET /health`

Health check.

**Response 200:**
```json
{ "status": "ok", "version": "0.1.0a0", "arc": true }
```

---

#### `GET /api/inspect`

Inspect workspace and detect runtimes.

**Query Parameters:**
- `workspace` (string, optional) — Workspace path (default: daemon workspace)

**Response 200:** ArcEnvelope with `WorkspaceInfo`

---

#### `GET /api/runtimes`

List detected runtimes.

**Response 200:** ArcEnvelope with array of runtime info

---

#### `GET /api/workflows`

List detected workflows.

**Query Parameters:**
- `runtime` (string, optional) — Filter by runtime ID

**Response 200:** ArcEnvelope with array of `WorkflowInfo`

---

#### `GET /api/schemas`

List exported schemas.

**Query Parameters:**
- `runtime` (string, optional) — Filter by runtime ID

**Response 200:** ArcEnvelope with array of `SchemaInfo`

---

#### `GET /api/runs`

List all runs.

**Response 200:** ArcEnvelope with array of run records

---

#### `GET /api/runs/start`

Start a workflow run.

**Query Parameters:**
- `workflow_id` (string, optional) — Workflow to run (default: 'wf-swarmgraph-fixture')

**Response 200:** ArcEnvelope with run result  
**Response 501:** No adapter supports execution

---

#### `GET /api/runs/{run_id}`

Get a specific run.

**Response 200:** ArcEnvelope with run record  
**Response 404:** Run not found

---

#### `GET /api/runs/{run_id}/events`

AG-UI-compatible SSE stream for run events.

**Response:** `text/event-stream` stream of events, ending with `STREAM_END`

---

#### `GET /api/context/pack`

Generate context pack for a task.

**Query Parameters:**
- `task` (string, optional) — Task description (default: 'agent runtime inspection')

**Response 200:** ArcEnvelope with redacted context entries

---

## Event Types

Trace files use JSONL format. Each line is a `TraceEvent`:

### `RUN_STARTED`

Workflow execution began.

**Data Fields:**
- `workflowId` (string) — Workflow identifier
- `runtime` (string) — Runtime type

### `NODE_COMPLETED`

A graph node finished execution.

**Data Fields:**
- `nodeId` (string) — Node identifier
- `nodeName` (string, optional) — Human-readable name
- `output` (any, optional) — Node output
- `duration` (number, optional) — Execution time in ms

### `MESSAGE`

A message was sent or received.

**Data Fields:**
- `role` (string) — 'user', 'assistant', or 'system'
- `content` (string) — Message content
- `nodeId` (string, optional) — Source node

### `RUN_COMPLETED`

Workflow execution succeeded.

**Data Fields:**
- `result` (any, optional) — Final result
- `duration` (number, optional) — Total execution time

### `RUN_FAILED`

Workflow execution failed.

**Data Fields:**
- `error` (string) — Error message
- `stackTrace` (string, optional) — Stack trace

### `ERROR`

An error occurred during execution.

**Data Fields:** Varies by error type

---

## Error Response Format

All REST API errors use FastAPI's standard format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input parameters |
| 404 | Not Found | Resource not found |
| 408 | Request Timeout | Execution exceeded timeout |
| 500 | Internal Server Error | Server-side error |
| 501 | Not Implemented | Feature not yet available |

---

## Security

### Input Validation

All endpoints validate inputs:
- Prompts sanitized (no shell metacharacters, max 10,000 chars)
- Trace IDs validated (`run-{prefix}-{hex}` pattern)
- Backend types validated against whitelist (`stub`, `local`, `gateway`)
- Paths validated within workspace boundaries

### Workspace Isolation

All file operations restricted to workspace root. Path traversal is blocked.

### Subprocess Security

Commands executed with `shell: false` and environment allow-list. See `docs/SECURITY.md` for details.

### CORS

Daemon server restricts CORS to `http://localhost:3000` only.

---

## Testing

### Manual Testing

```bash
# Start daemon
cd python && uv run arc serve

# Health check
curl http://localhost:7777/health

# Inspect workspace
curl "http://localhost:7777/api/inspect?workspace=$(pwd)"

# List runs
curl http://localhost:7777/api/runs
```

### Automated Testing

```bash
cd python
uv run pytest -v
```

---

## See Also

- [Architecture Documentation](ARCHITECTURE.md)
- [Development Guide](DEVELOPMENT.md)
- [Security Implementation](SECURITY.md)
- [Implementation Decisions](IMPLEMENTATION_DECISIONS.md)
