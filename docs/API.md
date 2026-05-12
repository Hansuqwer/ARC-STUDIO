# ARC Studio API Documentation

**Version:** 0.1.0  
**Last Updated:** 2026-05-12  
**Status:** Phase 4 - In Progress

---

## Overview

ARC Studio provides two API layers for interacting with agent workflows:

1. **JSON-RPC Protocol** - Frontend-to-backend communication within Theia
2. **REST API** - HTTP endpoints for external tools and testing

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

#### Methods

##### `executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult>`

Execute a SwarmGraph workflow with the given prompt.

**Parameters:**
- `prompt` (string) - The user prompt to execute
- `options` (ExecutionOptions, optional) - Execution configuration
  - `backend` ('gateway' | 'stub') - Backend type (default: 'gateway')
  - `costAllowed` (boolean) - Allow operations with API costs (default: true)

**Returns:** `Promise<ExecutionResult>`
- `runId` (string) - Unique run identifier (format: 'run-sg-{hash}')
- `status` ('completed' | 'failed') - Execution status
- `output` (string, optional) - Standard output if successful
- `error` (string, optional) - Error message if failed
- `tracePath` (string) - Path to trace file (format: '.arc/traces/{runId}.jsonl')

**Example:**
```typescript
const result = await arcService.executeWorkflow(
  "What is the weather in Paris?",
  { backend: 'gateway', costAllowed: true }
);
console.log(`Run ID: ${result.runId}`);
console.log(`Trace: ${result.tracePath}`);
```

**Errors:**
- Throws if SwarmGraph CLI is not available
- Throws if execution fails or times out

---

##### `getTraces(): Promise<TraceFile[]>`

Get list of all trace files from `.arc/traces/` directory.

**Returns:** `Promise<TraceFile[]>`
- Array of trace file metadata, sorted by timestamp (newest first)
- Each `TraceFile` contains:
  - `id` (string) - Trace identifier (without .jsonl extension)
  - `path` (string) - Absolute path to trace file
  - `timestamp` (string) - ISO 8601 timestamp
  - `status` ('completed' | 'failed') - Execution status

**Example:**
```typescript
const traces = await arcService.getTraces();
traces.forEach(trace => {
  console.log(`${trace.id}: ${trace.status} at ${trace.timestamp}`);
});
```

**Errors:**
- Returns empty array if `.arc/traces/` doesn't exist
- Skips files that cannot be parsed

---

##### `readTrace(traceId: string): Promise<TraceData>`

Read and parse a specific trace file by ID.

**Parameters:**
- `traceId` (string) - The trace ID (without .jsonl extension)

**Returns:** `Promise<TraceData>`
- `id` (string) - Trace identifier
- `workflowId` (string) - Workflow identifier
- `runtime` (string) - Runtime type ('swarmgraph' or 'langgraph')
- `status` (string) - Final execution status
- `startedAt` (string) - ISO 8601 start timestamp
- `endedAt` (string) - ISO 8601 end timestamp
- `events` (TraceEvent[]) - Array of execution events
- `metadata` (object) - Additional execution metadata

**Example:**
```typescript
const trace = await arcService.readTrace('run-sg-abc123');
console.log(`Workflow: ${trace.workflowId}`);
console.log(`Events: ${trace.events.length}`);
trace.events.forEach(event => {
  console.log(`${event.type} at ${event.timestamp}`);
});
```

**Errors:**
- Throws if trace file not found
- Throws if file cannot be parsed

---

##### `detectWorkflows(): Promise<WorkflowInfo[]>`

Detect workflow definitions in the current workspace.

**Returns:** `Promise<WorkflowInfo[]>`
- Array of detected workflows
- Each `WorkflowInfo` contains:
  - `type` ('langgraph' | 'swarmgraph') - Workflow runtime type
  - `path` (string) - Absolute path to workflow file/executable
  - `name` (string) - Human-readable workflow name

**Example:**
```typescript
const workflows = await arcService.detectWorkflows();
workflows.forEach(wf => {
  console.log(`Found ${wf.type} workflow: ${wf.name} at ${wf.path}`);
});
```

**Current Implementation:**
- ✅ Detects SwarmGraph CLI installations
- ⏳ LangGraph detection (planned for Phase 4)

---

## REST API

The REST API provides HTTP endpoints for external tools and testing.

### Base URL

```
http://localhost:8000
```

### Endpoints

#### `GET /`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "ARC Studio Backend"
}
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
- `prompt` (string, required) - The user prompt to execute
- `backend` (string, optional) - Backend type ('gateway' or 'stub', default: 'gateway')
- `cost_allowed` (boolean, optional) - Allow API costs (default: true)

**Response:** `200 OK`
```json
{
  "run_id": "run-sg-abc123",
  "status": "completed",
  "output": "The weather in Paris is...",
  "trace_path": ".arc/traces/run-sg-abc123.jsonl"
}
```

**Error Responses:**
- `408 Request Timeout` - Execution exceeded 5-minute timeout
- `500 Internal Server Error` - Execution failed

**Example:**
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is 2+2?",
    "backend": "gateway",
    "cost_allowed": true
  }'
```

---

#### `GET /api/traces`

Get list of all trace files.

**Response:** `200 OK`
```json
[
  {
    "id": "run-sg-abc123",
    "path": "/workspace/.arc/traces/run-sg-abc123.jsonl",
    "timestamp": "2026-05-12T20:30:00Z",
    "status": "completed"
  },
  {
    "id": "run-sg-def456",
    "path": "/workspace/.arc/traces/run-sg-def456.jsonl",
    "timestamp": "2026-05-12T20:25:00Z",
    "status": "failed"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/traces
```

---

#### `GET /api/traces/{trace_id}`

Get a specific trace file.

**Parameters:**
- `trace_id` (string, path) - The trace ID (without .jsonl extension)

**Response:** `200 OK`
```json
{
  "id": "run-sg-abc123",
  "workflowId": "swarmgraph-default",
  "runtime": "swarmgraph",
  "status": "completed",
  "startedAt": "2026-05-12T20:30:00Z",
  "endedAt": "2026-05-12T20:30:15Z",
  "events": [
    {
      "type": "RUN_STARTED",
      "timestamp": "2026-05-12T20:30:00Z",
      "runId": "run-sg-abc123",
      "sequence": 0,
      "data": {}
    },
    {
      "type": "NODE_COMPLETED",
      "timestamp": "2026-05-12T20:30:10Z",
      "runId": "run-sg-abc123",
      "sequence": 1,
      "data": {
        "nodeId": "agent-1",
        "output": "..."
      }
    },
    {
      "type": "RUN_COMPLETED",
      "timestamp": "2026-05-12T20:30:15Z",
      "runId": "run-sg-abc123",
      "sequence": 2,
      "data": {}
    }
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens": 150
  }
}
```

**Error Responses:**
- `404 Not Found` - Trace file doesn't exist
- `500 Internal Server Error` - Failed to parse trace file

**Example:**
```bash
curl http://localhost:8000/api/traces/run-sg-abc123
```

---

## Event Types

Trace files contain events in JSONL format. Each event has a `type` field:

### `RUN_STARTED`

Workflow execution began.

**Data Fields:**
- `workflowId` (string) - Identifier of the workflow
- `runtime` (string) - Runtime type ('swarmgraph' or 'langgraph')

---

### `NODE_COMPLETED`

A graph node finished execution.

**Data Fields:**
- `nodeId` (string) - Identifier of the node
- `nodeName` (string) - Human-readable node name
- `output` (any) - Node output data
- `duration` (number) - Execution time in milliseconds

---

### `MESSAGE`

A message was sent or received.

**Data Fields:**
- `role` (string) - Message role ('user', 'assistant', 'system')
- `content` (string) - Message content
- `nodeId` (string) - Node that generated the message

---

### `RUN_COMPLETED`

Workflow execution succeeded.

**Data Fields:**
- `result` (any) - Final workflow result
- `duration` (number) - Total execution time in milliseconds

---

### `RUN_FAILED`

Workflow execution failed.

**Data Fields:**
- `error` (string) - Error message
- `stackTrace` (string, optional) - Stack trace if available

---

## Security

### Input Validation

All API endpoints validate inputs to prevent:
- Command injection in prompts
- Path traversal in trace IDs
- Invalid backend types

See `python/src/security_utils.py` for implementation details.

### Workspace Isolation

All file operations are restricted to the workspace root:
- Trace files must be in `.arc/traces/`
- Workflow detection scans only workspace directories
- No access to files outside workspace boundaries

### Rate Limiting

**Status:** Not yet implemented (planned for Phase 5)

Future implementation will include:
- Request rate limiting per client
- Concurrent execution limits
- Resource usage monitoring

---

## Error Handling

### Common Error Codes

- `400 Bad Request` - Invalid input parameters
- `404 Not Found` - Resource not found
- `408 Request Timeout` - Operation exceeded timeout
- `500 Internal Server Error` - Server-side error

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Testing

### Manual Testing

Start the REST API server:
```bash
cd python
uvicorn src.routes:app --host 0.0.0.0 --port 8000
```

Test health check:
```bash
curl http://localhost:8000/
```

Test workflow execution:
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "backend": "stub"}'
```

### Automated Testing

**Status:** Not yet implemented (planned for Phase 5)

Future test coverage will include:
- Unit tests for each endpoint
- Integration tests for workflow execution
- Security tests for input validation

---

## Future Enhancements

### Planned for Phase 5

- [ ] WebSocket support for real-time event streaming
- [ ] Workflow cancellation endpoint
- [ ] Trace validation endpoint
- [ ] Workflow status polling endpoint

### Planned for Phase 6

- [ ] Authentication and authorization
- [ ] API rate limiting
- [ ] Request logging and metrics
- [ ] OpenAPI/Swagger documentation

---

## See Also

- [Architecture Documentation](ARCHITECTURE.md)
- [Development Guide](DEVELOPMENT.md)
- [Implementation Decisions](IMPLEMENTATION_DECISIONS.md)
