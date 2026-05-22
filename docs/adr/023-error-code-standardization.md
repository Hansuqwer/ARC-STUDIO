# ADR-023: Error Code Standardization

**Status:** Proposed (draft 2026-05-22)  
**Context:** Schema audit (Risk 1), Week 1 Critical Path  
**Related:** ADR-022 (Deprecation Policy), docs/SCHEMA_AUDIT_REPORT.md

## Context

The 2026-05-22 schema audit revealed a critical inconsistency: Python has 14 error codes while TypeScript has 8, with only 2 codes shared between them (TIMEOUT and INVALID_INPUT). This creates several problems:

1. **Silent failures:** Python emits error codes (e.g., `WORKSPACE_NOT_FOUND`) that TypeScript cannot recognize, forcing fallback to generic error handling.

2. **Vocabulary divergence:** TypeScript uses codes like `TRACE_NOT_FOUND` and `EXECUTION_FAILED` that Python doesn't emit, creating dead code paths.

3. **No governance:** There's no documented process for adding new error codes or deprecating old ones.

4. **Breaking change risk:** Syncing the codes requires deprecating 4 TypeScript codes and adding 12 codes to TypeScript, which is a breaking change without proper migration.

The audit identified this as Risk 1 (MEDIUM-HIGH severity) because it degrades error handling quality and could cause runtime failures if TypeScript uses strict enum matching.

## Decision

ARC Studio adopts a canonical error code list shared between Python and TypeScript, with a defined deprecation path for divergent codes.

### 1. Canonical Error Code List

The following 15 error codes are the canonical set for ARC Studio v0.2.0+:

#### Workspace & Runtime Detection
- **WORKSPACE_NOT_FOUND** - Workspace directory not found or not accessible
- **NO_RUNTIME_DETECTED** - No compatible runtime detected in workspace

#### Adapter Layer
- **ADAPTER_ERROR** - Generic adapter execution error
- **ADAPTER_NOT_SUPPORTED** - Requested adapter not available or not supported

#### Schema & Workflow Export
- **SCHEMA_EXPORT_FAILED** - Schema export operation failed
- **WORKFLOW_EXPORT_FAILED** - Workflow export operation failed

#### Run Execution
- **RUN_FAILED** - Run execution failed (generic)
- **RUN_NOT_FOUND** - Requested run ID not found in storage

#### Context & Conformance
- **CONTEXT_PROVIDER_ERROR** - Context provider (Context7, web search, etc.) error
- **CONFORMANCE_FAILED** - Conformance check failed

#### Generic Errors
- **INVALID_INPUT** - Invalid input parameters or malformed request
- **INTERNAL_ERROR** - Internal server error (unhandled exception)
- **TIMEOUT** - Operation exceeded timeout limit
- **NOT_IMPLEMENTED** - Feature not yet implemented
- **PERMISSION_DENIED** - Operation denied due to permissions or trust boundaries

#### Fallback
- **UNKNOWN** - Unknown error (fallback for unrecognized errors)

**Total:** 16 codes (15 canonical + 1 fallback)

Migration guide: `docs/guides/error-code-migration.md`.

### 2. Deprecated Error Codes

The following TypeScript-only codes are deprecated in v0.2.0 and will be removed in v0.3.0:

| Deprecated Code | Replacement | Rationale |
|----------------|-------------|-----------|
| `TRACE_NOT_FOUND` | `RUN_NOT_FOUND` | "Trace" is internal terminology; "run" is user-facing |
| `EXECUTION_FAILED` | `RUN_FAILED` | Redundant; `RUN_FAILED` is more specific |
| `PARSE_ERROR` | `INVALID_INPUT` | Parse errors are a subset of invalid input |
| `WORKFLOW_NOT_FOUND` | `WORKSPACE_NOT_FOUND` | Workflow detection is part of workspace detection |

**Deprecation Timeline (per ADR-022):**
- **v0.2.0:** Deprecated codes kept as aliases, emit deprecation warnings
- **v0.3.0:** Deprecated codes removed

### 3. Migration Path

#### Python Changes (v0.2.0)

**Add:**
```python
# python/src/agent_runtime_cockpit/protocol/errors.py
class ArcErrorCode(str, Enum):
    # ... existing codes ...
    PERMISSION_DENIED = "PERMISSION_DENIED"  # NEW
    UNKNOWN = "UNKNOWN"  # NEW (fallback)
```

**No removals:** All 14 existing Python codes are in the canonical list.

#### TypeScript Changes (v0.2.0)

**Add 12 missing codes:**
```typescript
// packages/arc-extension/src/common/arc-protocol.ts
export enum ArcErrorCode {
  // Workspace & runtime detection
  WORKSPACE_NOT_FOUND = 'WORKSPACE_NOT_FOUND',      // NEW
  NO_RUNTIME_DETECTED = 'NO_RUNTIME_DETECTED',      // NEW
  
  // Adapter layer
  ADAPTER_ERROR = 'ADAPTER_ERROR',                  // NEW
  ADAPTER_NOT_SUPPORTED = 'ADAPTER_NOT_SUPPORTED',  // NEW
  
  // Schema & workflow export
  SCHEMA_EXPORT_FAILED = 'SCHEMA_EXPORT_FAILED',    // NEW
  WORKFLOW_EXPORT_FAILED = 'WORKFLOW_EXPORT_FAILED', // NEW
  
  // Run execution
  RUN_FAILED = 'RUN_FAILED',                        // NEW
  RUN_NOT_FOUND = 'RUN_NOT_FOUND',                  // NEW
  
  // Context & conformance
  CONTEXT_PROVIDER_ERROR = 'CONTEXT_PROVIDER_ERROR', // NEW
  CONFORMANCE_FAILED = 'CONFORMANCE_FAILED',        // NEW
  
  // Generic
  INTERNAL_ERROR = 'INTERNAL_ERROR',                // NEW
  NOT_IMPLEMENTED = 'NOT_IMPLEMENTED',              // NEW
  
  // Existing codes (keep)
  INVALID_INPUT = 'INVALID_INPUT',
  TIMEOUT = 'TIMEOUT',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  UNKNOWN = 'UNKNOWN',
  
  // Deprecated codes (remove in v0.3.0; original wire strings preserved in v0.2.x)
  /** @deprecated Use RUN_NOT_FOUND - removed in v0.3.0 */
  TRACE_NOT_FOUND = 'TRACE_NOT_FOUND',
  /** @deprecated Use RUN_FAILED - removed in v0.3.0 */
  EXECUTION_FAILED = 'EXECUTION_FAILED',
  /** @deprecated Use INVALID_INPUT - removed in v0.3.0 */
  PARSE_ERROR = 'PARSE_ERROR',
  /** @deprecated Use WORKSPACE_NOT_FOUND - removed in v0.3.0 */
  WORKFLOW_NOT_FOUND = 'WORKFLOW_NOT_FOUND',
}
```

**Backwards Compatibility:**
Deprecated codes keep their original wire strings for v0.2.x. This preserves recorded trace compatibility; read paths normalize with `canonicalErrorCode()` / `ArcErrorCode.from_legacy()`:

```typescript
canonicalErrorCode(ArcErrorCode.TRACE_NOT_FOUND) === ArcErrorCode.RUN_NOT_FOUND  // true
canonicalErrorCode(ArcErrorCode.EXECUTION_FAILED) === ArcErrorCode.RUN_FAILED    // true
```

### 4. Error Code Governance

#### Adding New Error Codes

New error codes require:

1. **Justification:** Why existing codes don't cover the case
2. **Naming:** Follow `NOUN_VERB` or `NOUN_ADJECTIVE` pattern (e.g., `RUN_FAILED`, `ADAPTER_NOT_SUPPORTED`)
3. **Documentation:** Add to this ADR's canonical list
4. **Implementation:** Add to both Python and TypeScript simultaneously
5. **Tests:** Add fixture to `protocol/fixtures/error-codes/`

**Approval:** Requires review from at least one maintainer familiar with error handling.

#### Deprecating Error Codes

Error code deprecation follows ADR-022:

1. **Notice Period:** One minor version + one patch cycle
2. **Alias:** Keep deprecated code as alias to replacement
3. **Warning:** Emit deprecation warning when used
4. **Documentation:** Update this ADR and CHANGELOG
5. **Removal:** Remove in specified version

**Example:**
- v0.2.0: Deprecate `TRACE_NOT_FOUND`, alias to `RUN_NOT_FOUND`, emit warning
- v0.3.0: Remove `TRACE_NOT_FOUND` entirely

### 5. Error Code Categories

Error codes are organized by domain for maintainability:

| Category | Codes | Purpose |
|----------|-------|---------|
| **Workspace & Runtime** | WORKSPACE_NOT_FOUND, NO_RUNTIME_DETECTED | Workspace detection and runtime discovery |
| **Adapter** | ADAPTER_ERROR, ADAPTER_NOT_SUPPORTED | Adapter execution and availability |
| **Export** | SCHEMA_EXPORT_FAILED, WORKFLOW_EXPORT_FAILED | Schema and workflow export operations |
| **Run Execution** | RUN_FAILED, RUN_NOT_FOUND | Run lifecycle and storage |
| **Context** | CONTEXT_PROVIDER_ERROR, CONFORMANCE_FAILED | Context providers and conformance checks |
| **Generic** | INVALID_INPUT, INTERNAL_ERROR, TIMEOUT, NOT_IMPLEMENTED, PERMISSION_DENIED | Cross-cutting errors |
| **Fallback** | UNKNOWN | Unrecognized errors |

**Naming Conventions:**
- Use `_NOT_FOUND` for missing resources
- Use `_FAILED` for operation failures
- Use `_ERROR` for generic domain errors
- Use `_DENIED` for permission/authorization failures
- Use `_NOT_SUPPORTED` for unavailable features

### 6. Error Response Format

All ARC errors use the `ArcError` schema:

```typescript
interface ArcError {
  code: ArcErrorCode;      // Canonical error code
  message: string;         // Human-readable message
  details?: Record<string, unknown>;  // Optional structured details
}
```

**Best Practices:**
- **code:** Always use canonical error code from this ADR
- **message:** Provide actionable error message (what went wrong, how to fix)
- **details:** Include relevant context (file paths, IDs, parameters) but redact secrets

**Example:**
```json
{
  "code": "WORKSPACE_NOT_FOUND",
  "message": "Workspace not found at path: /nonexistent/path",
  "details": {
    "path": "/nonexistent/path",
    "searched_locations": [
      "/nonexistent/path",
      "/nonexistent/path/.arc"
    ]
  }
}
```

## Consequences

### Positive

1. **Consistent error handling:** Python and TypeScript use the same error vocabulary
2. **Better UX:** TypeScript can provide specific error messages instead of generic fallbacks
3. **Maintainability:** Clear governance process for adding/deprecating codes
4. **Documentation:** Canonical list serves as reference for all error handling
5. **Type safety:** TypeScript enum provides compile-time checking

### Negative

1. **Breaking change:** Adding 12 codes to TypeScript is a breaking change (mitigated by deprecation aliases)
2. **Migration burden:** Existing TypeScript code using deprecated codes must be updated
3. **Coordination required:** New codes must be added to both languages simultaneously

### Risks

1. **Incomplete migration:** If TypeScript code doesn't update deprecated codes, they'll break in v0.3.0
   - **Mitigation:** Deprecation warnings, CHANGELOG entries, migration guide
2. **Code divergence:** Future additions might only go to one language
   - **Mitigation:** Governance process requires both languages, CI check (future)

## Implementation Plan

### Phase 1: Python Changes (v0.2.0)

1. Add `PERMISSION_DENIED` and `UNKNOWN` to `protocol/errors.py`
2. Add error code fixtures to `protocol/fixtures/error-codes/`
3. Update tests to validate new codes

**Estimated Effort:** 1 hour

### Phase 2: TypeScript Changes (v0.2.0)

1. Add 12 missing codes to `arc-extension/src/common/arc-protocol.ts`
2. Add deprecated aliases with JSDoc warnings
3. Update error handling code to use new codes
4. Add error code fixtures (shared with Python)
5. Update tests to validate all codes

**Estimated Effort:** 2 hours

### Phase 3: Documentation (v0.2.0)

1. Update CHANGELOG with breaking changes and deprecations
2. Create migration guide for deprecated codes
3. Update error handling documentation
4. Add this ADR to docs/adr/

**Estimated Effort:** 1 hour

### Phase 4: Validation (v0.2.0)

1. Run cross-language fixture tests
2. Verify all error codes round-trip correctly
3. Test deprecated code aliases work
4. Verify deprecation warnings emit

**Estimated Effort:** 1 hour

### Phase 5: Cleanup (v0.3.0)

1. Remove deprecated code aliases from TypeScript
2. Update CHANGELOG
3. Verify no code uses deprecated codes

**Estimated Effort:** 30 minutes

**Total Effort:** ~5.5 hours (4 hours for v0.2.0, 1.5 hours for v0.3.0)

## Acceptance Criteria

This ADR is considered implemented when:

1. ✅ Python has all 16 canonical error codes
2. ✅ TypeScript has all 16 canonical error codes
3. ✅ Deprecated TypeScript codes exist as aliases with warnings
4. ✅ Cross-language fixture tests pass for all error codes
5. ✅ CHANGELOG documents breaking changes and migration path
6. ✅ Error handling documentation updated

## Related Work

- **docs/SCHEMA_AUDIT_REPORT.md Risk 1:** Error code mismatch analysis
- **ADR-022:** Deprecation policy that governs error code lifecycle
- **protocol/fixtures/error-codes/:** Shared error code fixtures for testing

## Future Considerations

### CI Enforcement (v0.3.0+)

Add CI check to ensure error codes stay synchronized:

```bash
# Compare Python and TypeScript error code lists
python scripts/check-error-codes.py
```

This script would:
1. Extract error codes from both languages
2. Compare canonical lists
3. Fail if codes diverge
4. Suggest which codes to add/remove

### Error Code Metrics (v0.4.0+)

Track error code usage in production:
- Which codes are most common?
- Which codes are never used? (candidates for deprecation)
- Which error messages are most helpful?

### Localization (v1.0+)

Error messages are currently English-only. Future work:
- Separate error code from message
- Support multiple languages
- Maintain message catalog

## Appendix: Complete Error Code Reference

### Python Implementation

```python
# python/src/agent_runtime_cockpit/protocol/errors.py
from enum import Enum

class ArcErrorCode(str, Enum):
    """Canonical ARC error codes (ADR-023)."""
    
    # Workspace & runtime detection
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    NO_RUNTIME_DETECTED = "NO_RUNTIME_DETECTED"
    
    # Adapter layer
    ADAPTER_ERROR = "ADAPTER_ERROR"
    ADAPTER_NOT_SUPPORTED = "ADAPTER_NOT_SUPPORTED"
    
    # Schema & workflow export
    SCHEMA_EXPORT_FAILED = "SCHEMA_EXPORT_FAILED"
    WORKFLOW_EXPORT_FAILED = "WORKFLOW_EXPORT_FAILED"
    
    # Run execution
    RUN_FAILED = "RUN_FAILED"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    
    # Context & conformance
    CONTEXT_PROVIDER_ERROR = "CONTEXT_PROVIDER_ERROR"
    CONFORMANCE_FAILED = "CONFORMANCE_FAILED"
    
    # Generic errors
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # Fallback
    UNKNOWN = "UNKNOWN"
```

### TypeScript Implementation

See Section 3 (Migration Path) for complete TypeScript implementation including deprecated aliases.

---

**Status:** Proposed  
**Next Review:** After implementation in v0.2.0  
**Owner:** Engineering team  
**Approver:** Technical lead
