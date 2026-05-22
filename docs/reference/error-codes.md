# Error Code Reference

**Type:** Reference (Diátaxis)  
**Audience:** Developers, contributors, support engineers  
**Purpose:** Complete inventory of ARC Studio error codes and their usage

---

## Overview

ARC Studio uses stable error codes to identify error conditions across the Python backend, TypeScript extension, and HTTP API. Error codes enable:
- **Programmatic error handling:** Clients can handle specific errors without parsing messages
- **Consistent error reporting:** Same error condition always uses the same code
- **Debugging:** Error codes make it easy to search logs and code for specific failures
- **Documentation:** Each error code has a defined meaning and remediation

---

## Error Code Format

Error codes are:
- **UPPER_SNAKE_CASE** strings (e.g., `RUN_NOT_FOUND`)
- **Stable:** Once defined, error codes never change meaning
- **Unique:** Each error condition has exactly one error code
- **Language-agnostic:** Same codes used in Python, TypeScript, and HTTP responses

---

## Python Error Codes

**Location:** `python/src/agent_runtime_cockpit/protocol/errors.py`

```python
class ArcErrorCode(str, Enum):
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    NO_RUNTIME_DETECTED = "NO_RUNTIME_DETECTED"
    ADAPTER_ERROR = "ADAPTER_ERROR"
    ADAPTER_NOT_SUPPORTED = "ADAPTER_NOT_SUPPORTED"
    SCHEMA_EXPORT_FAILED = "SCHEMA_EXPORT_FAILED"
    WORKFLOW_EXPORT_FAILED = "WORKFLOW_EXPORT_FAILED"
    RUN_FAILED = "RUN_FAILED"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    CONTEXT_PROVIDER_ERROR = "CONTEXT_PROVIDER_ERROR"
    CONFORMANCE_FAILED = "CONFORMANCE_FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
```

**Total:** 14 error codes

---

## TypeScript Error Codes

**Location:** `packages/arc-extension/src/common/arc-protocol.ts`

```typescript
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
```

**Total:** 8 error codes

---

## Error Code Catalog

### WORKSPACE_NOT_FOUND

**Scope:** Python backend  
**HTTP Status:** 404  
**Meaning:** The requested workspace directory does not exist or is not accessible.

**When to use:**
- Workspace path validation fails
- Workspace directory cannot be read
- Workspace is not a valid directory

**Remediation:**
- Check that the workspace path is correct
- Ensure the workspace directory exists
- Verify file system permissions

**Used in:**
- CLI: workspace validation
- HTTP API: workspace path validation

---

### NO_RUNTIME_DETECTED

**Scope:** Python backend  
**HTTP Status:** 404  
**Meaning:** No agent runtime (SwarmGraph, LangGraph, CrewAI) was detected in the workspace.

**When to use:**
- Runtime detection finds no supported frameworks
- Workspace has no workflow files
- Runtime dependencies are missing

**Remediation:**
- Install a supported agent framework (SwarmGraph, LangGraph, CrewAI)
- Add workflow files to the workspace
- Run `arc doctor` to check runtime status

**Used in:**
- CLI: `arc runtimes` command
- HTTP API: `/api/runtimes` endpoint

---

### ADAPTER_ERROR

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** An adapter encountered an error during workflow execution.

**When to use:**
- Adapter raises an exception during execution
- Workflow execution fails due to adapter-specific error
- Adapter cannot communicate with the runtime

**Remediation:**
- Check adapter logs for details
- Verify runtime dependencies are installed
- Run `arc adapter test <adapter-id>` to test the adapter

**Used in:**
- Adapter execution paths
- Runtime router error handling

---

### ADAPTER_NOT_SUPPORTED

**Scope:** Python backend  
**HTTP Status:** 501  
**Meaning:** The requested adapter is not supported or not available.

**When to use:**
- User requests an unknown adapter
- Adapter is not installed
- Adapter is disabled

**Remediation:**
- Check available adapters with `arc adapter list`
- Install the required adapter
- Verify adapter is enabled in configuration

**Used in:**
- CLI: `arc adapter test` command
- Runtime router: adapter resolution

---

### SCHEMA_EXPORT_FAILED

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** Schema export operation failed.

**When to use:**
- Schema serialization fails
- Schema file cannot be written
- Schema validation fails during export

**Remediation:**
- Check file system permissions
- Verify schema is valid
- Check disk space

**Used in:**
- Schema export operations
- Workflow schema generation

---

### WORKFLOW_EXPORT_FAILED

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** Workflow export operation failed.

**When to use:**
- Workflow serialization fails
- Workflow file cannot be written
- Workflow validation fails during export

**Remediation:**
- Check file system permissions
- Verify workflow is valid
- Check disk space

**Used in:**
- Workflow export operations
- Workflow file generation

---

### RUN_FAILED

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** Workflow execution failed.

**When to use:**
- Workflow execution raises an exception
- Adapter reports execution failure
- Runtime crashes during execution

**Remediation:**
- Check run logs for error details
- Run `arc runs autopsy <run-id>` for failure analysis
- Verify workflow is valid
- Check runtime dependencies

**Used in:**
- CLI: `arc run` command
- HTTP API: `/api/runs/start` endpoint
- Workflow execution paths

---

### RUN_NOT_FOUND

**Scope:** Python backend, TypeScript extension (as TRACE_NOT_FOUND)  
**HTTP Status:** 404  
**Meaning:** The requested run ID does not exist.

**When to use:**
- Run ID is not in the trace store
- Trace file does not exist
- Run was deleted

**Remediation:**
- Check run ID is correct
- List available runs with `arc runs search`
- Verify run was not deleted

**Used in:**
- CLI: `arc runs export`, `arc runs delete`, `arc runs status`, etc.
- HTTP API: `/api/runs/{run_id}` endpoint
- Trace store operations

---

### CONTEXT_PROVIDER_ERROR

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** Context provider encountered an error.

**When to use:**
- Context pack generation fails
- Context provider raises an exception
- Context retrieval fails

**Remediation:**
- Check context provider logs
- Verify workspace files are accessible
- Run `arc context pack` to test context generation

**Used in:**
- CLI: `arc context pack` command
- Context provider operations

---

### CONFORMANCE_FAILED

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** Adapter conformance test failed.

**When to use:**
- Adapter does not implement required methods
- Adapter output does not match expected schema
- Adapter fails conformance checks

**Remediation:**
- Run `arc adapter test <adapter-id>` for details
- Check adapter implementation
- Verify adapter follows protocol

**Used in:**
- CLI: `arc adapter test` command
- Adapter conformance testing

---

### INVALID_INPUT

**Scope:** Python backend, TypeScript extension  
**HTTP Status:** 400  
**Meaning:** Request contains invalid input.

**When to use:**
- Request parameters are invalid
- JSON parsing fails
- Input validation fails
- Required parameters are missing

**Remediation:**
- Check request parameters
- Verify JSON is valid
- Ensure required parameters are provided
- Check parameter types and formats

**Used in:**
- CLI: parameter validation
- HTTP API: request validation
- TypeScript extension: input validation

**Examples:**
- Invalid run ID format
- Missing required parameter
- Invalid JSON body
- Out-of-range parameter value

---

### INTERNAL_ERROR

**Scope:** Python backend  
**HTTP Status:** 500  
**Meaning:** An unexpected internal error occurred.

**When to use:**
- Unhandled exception
- Unexpected state
- System error (file I/O, database, etc.)

**Remediation:**
- Check logs for stack trace
- Report bug with reproduction steps
- Check system resources (disk, memory)

**Used in:**
- Generic error handler
- Unexpected exceptions
- System-level errors

---

### TIMEOUT

**Scope:** Python backend, TypeScript extension  
**HTTP Status:** 504  
**Meaning:** Operation timed out.

**When to use:**
- Workflow execution exceeds timeout
- HTTP request times out
- Long-running operation is cancelled

**Remediation:**
- Increase timeout limit
- Optimize workflow for faster execution
- Check for infinite loops or blocking operations

**Used in:**
- Workflow execution timeout
- HTTP request timeout
- Long-running operations

---

### NOT_IMPLEMENTED

**Scope:** Python backend  
**HTTP Status:** 501  
**Meaning:** Feature is not implemented yet.

**When to use:**
- Feature is planned but not yet implemented
- Endpoint exists but is not functional
- Adapter method is not implemented

**Remediation:**
- Check roadmap for implementation timeline
- Use alternative feature if available
- Contribute implementation if possible

**Used in:**
- Placeholder endpoints
- Unimplemented adapter methods
- Future features

---

### TRACE_NOT_FOUND

**Scope:** TypeScript extension  
**HTTP Status:** 404  
**Meaning:** The requested trace file does not exist.

**When to use:**
- Trace file path is invalid
- Trace file was deleted
- Trace file cannot be read

**Remediation:**
- Check trace file path
- Verify trace file exists
- Check file system permissions

**Used in:**
- TypeScript extension: trace file operations
- File manager service

**Note:** This is equivalent to `RUN_NOT_FOUND` in the Python backend. Consider consolidating.

---

### EXECUTION_FAILED

**Scope:** TypeScript extension  
**HTTP Status:** 500  
**Meaning:** Workflow execution failed in the TypeScript extension.

**When to use:**
- Workflow executor service fails
- Process spawn fails
- Execution process crashes

**Remediation:**
- Check execution logs
- Verify Python backend is running
- Check process permissions

**Used in:**
- TypeScript extension: workflow executor service
- Process management

**Note:** This is similar to `RUN_FAILED` in the Python backend. Consider consolidating.

---

### PARSE_ERROR

**Scope:** TypeScript extension  
**HTTP Status:** 500  
**Meaning:** Trace parsing failed.

**When to use:**
- Trace file is not valid JSONL
- Event schema validation fails
- Trace file is corrupted

**Remediation:**
- Check trace file format
- Verify trace file is not corrupted
- Run `arc runs export <run-id>` to re-export

**Used in:**
- TypeScript extension: trace parser service
- Trace file parsing

---

### WORKFLOW_NOT_FOUND

**Scope:** TypeScript extension  
**HTTP Status:** 404  
**Meaning:** The requested workflow does not exist.

**When to use:**
- Workflow ID is not found
- Workflow file does not exist
- Workflow detection fails

**Remediation:**
- Check workflow ID is correct
- List available workflows with `arc workflows`
- Verify workflow file exists

**Used in:**
- TypeScript extension: workflow detection
- Workflow executor service

---

### PERMISSION_DENIED

**Scope:** TypeScript extension  
**HTTP Status:** 403  
**Meaning:** Operation is not permitted.

**When to use:**
- Workspace is not trusted
- File system permissions deny access
- Security policy blocks operation

**Remediation:**
- Trust the workspace with `arc workspace trust`
- Check file system permissions
- Review security policy

**Used in:**
- TypeScript extension: security checks
- File operations

---

### UNKNOWN

**Scope:** TypeScript extension  
**HTTP Status:** 500  
**Meaning:** An unknown error occurred.

**When to use:**
- Error type cannot be determined
- Fallback for unhandled errors
- Error from external system

**Remediation:**
- Check logs for details
- Report bug with reproduction steps

**Used in:**
- TypeScript extension: generic error handler
- Fallback error code

---

## Error Code Consistency

### Shared Codes

These codes exist in both Python and TypeScript:

| Code | Python | TypeScript | Consistent? |
|------|--------|------------|-------------|
| `INVALID_INPUT` | ✅ | ✅ | ✅ Yes |
| `TIMEOUT` | ✅ | ✅ | ✅ Yes |

### Python-Only Codes

These codes exist only in Python:

- `WORKSPACE_NOT_FOUND`
- `NO_RUNTIME_DETECTED`
- `ADAPTER_ERROR`
- `ADAPTER_NOT_SUPPORTED`
- `SCHEMA_EXPORT_FAILED`
- `WORKFLOW_EXPORT_FAILED`
- `RUN_FAILED`
- `RUN_NOT_FOUND`
- `CONTEXT_PROVIDER_ERROR`
- `CONFORMANCE_FAILED`
- `INTERNAL_ERROR`
- `NOT_IMPLEMENTED`

### TypeScript-Only Codes

These codes exist only in TypeScript:

- `TRACE_NOT_FOUND` (similar to `RUN_NOT_FOUND`)
- `EXECUTION_FAILED` (similar to `RUN_FAILED`)
- `PARSE_ERROR`
- `WORKFLOW_NOT_FOUND`
- `PERMISSION_DENIED`
- `UNKNOWN`

### Inconsistencies

**Issue 1: Duplicate semantics**
- `TRACE_NOT_FOUND` (TypeScript) vs `RUN_NOT_FOUND` (Python) — same meaning, different names
- `EXECUTION_FAILED` (TypeScript) vs `RUN_FAILED` (Python) — same meaning, different names

**Recommendation:** Consolidate to use the same error codes across languages.

**Issue 2: Missing codes in TypeScript**
TypeScript extension lacks codes for:
- Workspace errors (`WORKSPACE_NOT_FOUND`)
- Runtime detection errors (`NO_RUNTIME_DETECTED`)
- Adapter errors (`ADAPTER_ERROR`, `ADAPTER_NOT_SUPPORTED`)
- Internal errors (`INTERNAL_ERROR`)
- Not implemented features (`NOT_IMPLEMENTED`)

**Recommendation:** Add missing codes to TypeScript enum for consistency.

**Issue 3: Missing codes in Python**
Python backend lacks codes for:
- Permission errors (`PERMISSION_DENIED`)
- Parse errors (`PARSE_ERROR`)
- Unknown errors (`UNKNOWN`)

**Recommendation:** Add missing codes to Python enum for consistency.

---

## Gaps Identified

### Gap 1: No error codes for exceptions

Many exception classes in the codebase do not use error codes:

**Examples:**
- `GatingError` — should use `INVALID_INPUT` or new `GATING_ERROR` code
- `ProfileNotFound` — should use `INVALID_INPUT` or new `PROFILE_NOT_FOUND` code
- `UnknownRuntime` — should use `NO_RUNTIME_DETECTED` or `ADAPTER_NOT_SUPPORTED`
- `RuntimeRouterError` — should use `ADAPTER_ERROR` or specific code

**Recommendation:** Add error codes to all exception classes.

### Gap 2: No error codes for validation errors

Input validation errors often use generic messages without error codes:

**Examples:**
- Invalid workspace path — should use `WORKSPACE_NOT_FOUND` or `INVALID_INPUT`
- Invalid run ID format — should use `INVALID_INPUT`
- Invalid JSON body — should use `INVALID_INPUT` (already used in some places)

**Recommendation:** Ensure all validation errors use `INVALID_INPUT` with specific details.

### Gap 3: No error codes for HTTP status codes

Some HTTP responses use status codes without error codes:

**Examples:**
- 400 Bad Request — should always include `INVALID_INPUT`
- 404 Not Found — should include specific code (`RUN_NOT_FOUND`, `WORKSPACE_NOT_FOUND`, etc.)
- 500 Internal Server Error — should include specific code (`INTERNAL_ERROR`, `RUN_FAILED`, etc.)

**Recommendation:** Ensure all HTTP error responses include error codes.

### Gap 4: No error codes for async operations

Async operations (SSE, WebSocket) may fail without error codes:

**Examples:**
- SSE connection failure
- Event stream error
- Cancellation

**Recommendation:** Add error codes for async operation failures.

---

## Usage Guidelines

### When to Add a New Error Code

Add a new error code when:
1. **New error condition:** A new type of error that doesn't fit existing codes
2. **Specific handling needed:** Clients need to handle this error differently
3. **Distinct remediation:** The fix for this error is different from others

### When to Use an Existing Error Code

Use an existing error code when:
1. **Same error condition:** The error is the same as an existing code
2. **Same remediation:** The fix is the same as an existing code
3. **Same HTTP status:** The HTTP status code is the same

### Error Code Naming Conventions

- **UPPER_SNAKE_CASE:** All error codes use uppercase with underscores
- **Descriptive:** Code name describes the error condition (e.g., `RUN_NOT_FOUND`)
- **Specific:** Avoid generic names like `ERROR` or `FAILURE`
- **Stable:** Once defined, never change the meaning

### Error Response Format

**Python (HTTP API):**
```python
from agent_runtime_cockpit.protocol.event_envelope import err
from agent_runtime_cockpit.protocol.errors import ArcErrorCode

return err(
    ArcErrorCode.RUN_NOT_FOUND,
    f"Run {run_id} not found",
    details={"run_id": run_id}
)
```

**TypeScript (Extension):**
```typescript
import { ArcErrorCode } from './arc-protocol';

throw new Error(JSON.stringify({
    code: ArcErrorCode.TRACE_NOT_FOUND,
    message: `Trace ${traceId} not found`,
    details: { traceId }
}));
```

---

## Recommendations

### Short-term (Phase 1)

1. **Consolidate duplicate codes:**
   - Use `RUN_NOT_FOUND` in both Python and TypeScript (remove `TRACE_NOT_FOUND`)
   - Use `RUN_FAILED` in both Python and TypeScript (remove `EXECUTION_FAILED`)

2. **Add missing codes to TypeScript:**
   - `WORKSPACE_NOT_FOUND`
   - `NO_RUNTIME_DETECTED`
   - `ADAPTER_ERROR`
   - `ADAPTER_NOT_SUPPORTED`
   - `INTERNAL_ERROR`
   - `NOT_IMPLEMENTED`

3. **Add missing codes to Python:**
   - `PERMISSION_DENIED`
   - `PARSE_ERROR`
   - `UNKNOWN`

4. **Add error codes to exceptions:**
   - Add `error_code` attribute to all exception classes
   - Use error codes in exception messages

### Long-term (Phase 2+)

1. **Error code registry:**
   - Create a single source of truth for error codes (shared schema)
   - Generate Python and TypeScript enums from schema
   - Validate error code usage in CI

2. **Error code documentation:**
   - Add error code to all error messages
   - Include remediation steps in error responses
   - Link to documentation from error messages

3. **Error code telemetry:**
   - Track error code frequency
   - Alert on new error codes
   - Monitor error code trends

---

## Related Documentation

- **[Architecture Overview](../explanation/architecture.md)** — Three-layer architecture
- **[HTTP API Reference](../api/http-api.md)** — HTTP endpoints and error responses
- **[CLI Reference](../reference/cli-commands.md)** — CLI commands and exit codes

---

## Appendix: Error Code Usage Count

**Python backend:** 14 error codes defined, ~150+ usages across CLI and HTTP API  
**TypeScript extension:** 8 error codes defined, ~30+ usages across services

**Total unique error codes:** 20 (14 Python + 8 TypeScript - 2 shared)

**Coverage:** ~80% of error paths use error codes (estimated)

**Gaps:** ~20% of error paths need error codes added (exceptions, validation, async operations)
