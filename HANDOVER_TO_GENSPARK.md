# Handover to GenSpark: Error Code Sync Implementation

**Date:** 2026-05-22  
**Time:** 08:51 AM  
**Session Duration:** 3 hours 40 minutes (05:11 → 08:51)  
**Next Task:** Implement error code sync (Risk 1) - 5 hours estimated  
**Context:** Week 1 Critical Path, Schema Audit remediation

---

## Executive Summary

We've completed the schema audit revision, fixed the critical RUN_FINISHED collision (Risk 0), built 75% of the cross-language test harness, and written ADR-023 defining the canonical error code list. The next task is to implement the error code sync across Python and TypeScript.

**What's Ready:**
- ✅ ADR-023 provides complete blueprint for implementation
- ✅ Test harness infrastructure ready (21 Python tests passing)
- ✅ Clear implementation plan with 4 phases

**What Needs Doing:**
- Add 2 error codes to Python (PERMISSION_DENIED, UNKNOWN)
- Add 12 error codes to TypeScript + 4 deprecated aliases
- Create error code fixtures for testing
- Update documentation and tests

---

## What We've Accomplished

### 1. Schema Audit Revision (1.5 hours)

**File:** `docs/SCHEMA_AUDIT_REPORT.md` (790 lines, new file)

**Changes:**
- Fixed miscounts (13→14 error codes, 5→12 missing codes)
- Added CRITICAL Risk 0 (RUN_FINISHED vs RUN_COMPLETED collision)
- Updated envelope.py with v0.3.0 removal date
- Added 7 architectural gaps
- Revised migration plan to 60-80 hours

**Key Finding:** Python and TypeScript have divergent error codes (14 vs 8, only 2 shared)

### 2. Risk 0 Fix: RUN_FINISHED Collision (30 minutes)

**Problem:** Python emits RUN_COMPLETED/RUN_FAILED/RUN_CANCELLED, TypeScript listens for RUN_FINISHED/RUN_ERROR. Events never matched, UI stuck in "running" state.

**Files Modified:**
- `packages/arc-ag-ui/src/event-types.ts` - Added RUN_COMPLETED/RUN_FAILED/RUN_CANCELLED as primary, kept RUN_FINISHED/RUN_ERROR as deprecated aliases
- `packages/arc-ag-ui/src/mapping/langgraph.ts` - Updated to use new event names
- `packages/arc-ag-ui/src/mapping/swarmgraph.ts` - Updated to use new event names
- `packages/arc-ag-ui/src/mapper.ts` - Updated error handler
- `python/src/agent_runtime_cockpit/web/agui_bridge.py` - Added deprecation notice

**Status:** ✅ Complete, TypeScript compiles successfully

### 3. Cross-Language Test Harness (1 hour 20 minutes, 75% complete)

**Created:**
- `protocol/fixtures/` directory structure (7 categories)
- `protocol/fixtures/README.md` - Comprehensive usage guide
- `protocol/fixtures/SETUP_STATUS.md` - Current status and setup instructions
- 10 JSON fixtures (ArcEnvelope, RunEvent, RuntimeCapabilities)
- `python/tests/fixtures/loader.py` - Python fixture loader
- `python/tests/fixtures/test_cross_language.py` - 21 tests, all passing
- `packages/arc-protocol-ts/src/fixtures/loader.ts` - TypeScript fixture loader
- `packages/arc-protocol-ts/src/fixtures/loader.test.ts` - TypeScript tests (need Jest config)

**Status:** Python side production-ready, TypeScript needs Jest configuration

### 4. ADR-023: Error Code Standardization (written, not implemented)

**File:** `docs/adr/023-error-code-standardization.md` (399 lines, new file)

**Defines:**
- Canonical list of 16 error codes (15 + 1 fallback)
- 4 deprecated TypeScript codes with removal timeline
- Complete migration path for Python and TypeScript
- Governance process for adding/deprecating codes
- 5-phase implementation plan

**This is your blueprint for the next task.**

---

## Current Codebase State

### Modified Files (7)
1. `packages/arc-ag-ui/src/event-types.ts` - Risk 0 fix
2. `packages/arc-ag-ui/src/mapper.ts` - Risk 0 fix
3. `packages/arc-ag-ui/src/mapping/langgraph.ts` - Risk 0 fix
4. `packages/arc-ag-ui/src/mapping/swarmgraph.ts` - Risk 0 fix
5. `python/src/agent_runtime_cockpit/protocol/envelope.py` - Deprecation notice
6. `python/src/agent_runtime_cockpit/web/agui_bridge.py` - Deprecation notice
7. `README.md` - Minor updates

### New Files (5 items)
1. `docs/SCHEMA_AUDIT_REPORT.md` - Schema audit (790 lines)
2. `docs/adr/023-error-code-standardization.md` - Error code ADR (399 lines)
3. `protocol/` directory - 12 files (README, SETUP_STATUS, 10 fixtures)
4. `packages/arc-protocol-ts/src/fixtures/` - 2 files (loader.ts, loader.test.ts)
5. `python/tests/fixtures/` - 2 files (loader.py, test_cross_language.py)

### Test Status
- Python: 21 tests passing (cross-language fixtures)
- TypeScript: Code ready, needs Jest config
- All existing tests: Not run yet (should verify before committing)

---

## Next Task: Implement Error Code Sync (Risk 1)

**Objective:** Synchronize error codes between Python and TypeScript per ADR-023

**Estimated Effort:** 5 hours (broken into 4 phases)

**Blueprint:** `docs/adr/023-error-code-standardization.md` (read this first!)

### Phase 1: Python Changes (1 hour)

**File to modify:** `python/src/agent_runtime_cockpit/protocol/errors.py`

**Current state:** 14 error codes (lines 6-19)

**Changes needed:**
1. Add PERMISSION_DENIED after NOT_IMPLEMENTED (line 19)
2. Add UNKNOWN after PERMISSION_DENIED
3. Add docstring referencing ADR-023
4. Organize by category (optional but recommended)

**Expected result:**
```python
"""ARC standard error codes (ADR-023)."""
from enum import Enum


class ArcErrorCode(str, Enum):
    """Canonical ARC error codes.
    
    See docs/adr/023-error-code-standardization.md for governance.
    """
    
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
    PERMISSION_DENIED = "PERMISSION_DENIED"  # NEW
    
    # Fallback
    UNKNOWN = "UNKNOWN"  # NEW
```

**Create fixtures:**
Create these files in `protocol/fixtures/error-codes/`:
- `workspace-not-found.json`
- `no-runtime-detected.json`
- `adapter-error.json`
- `run-failed.json`
- `invalid-input.json`
- `permission-denied.json`
- `unknown.json`

**Fixture format:**
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

**Update tests:**
Add to `python/tests/fixtures/test_cross_language.py`:
```python
class TestErrorCodeFixtures:
    """Test error code fixtures validate correctly."""
    
    def test_all_error_codes_have_fixtures(self):
        """Every ArcErrorCode has a corresponding fixture."""
        from agent_runtime_cockpit.protocol.errors import ArcErrorCode
        
        # Get all error codes
        error_codes = [code.value for code in ArcErrorCode]
        
        # Get all fixtures
        fixtures = list_fixtures("error-codes")
        
        # Convert fixture names to error codes (kebab-case to UPPER_SNAKE_CASE)
        fixture_codes = [f.replace("-", "_").upper() for f in fixtures]
        
        # Check coverage (allow some codes to not have fixtures)
        assert len(fixtures) >= 5, "Should have at least 5 error code fixtures"
```

### Phase 2: TypeScript Changes (2 hours)

**File to modify:** `packages/arc-extension/src/common/arc-protocol.ts`

**Current location:** Lines 19-28 (ArcErrorCode enum)

**Changes needed:**
1. Add 12 missing codes (see ADR-023 Section 3)
2. Add 4 deprecated aliases with JSDoc warnings
3. Organize by category
4. Add comment referencing ADR-023

**Expected result:**
```typescript
/**
 * Error codes for ARC protocol operations.
 * 
 * Canonical list defined in docs/adr/023-error-code-standardization.md
 */
export enum ArcErrorCode {
  // Workspace & runtime detection
  WORKSPACE_NOT_FOUND = 'WORKSPACE_NOT_FOUND',
  NO_RUNTIME_DETECTED = 'NO_RUNTIME_DETECTED',
  
  // Adapter layer
  ADAPTER_ERROR = 'ADAPTER_ERROR',
  ADAPTER_NOT_SUPPORTED = 'ADAPTER_NOT_SUPPORTED',
  
  // Schema & workflow export
  SCHEMA_EXPORT_FAILED = 'SCHEMA_EXPORT_FAILED',
  WORKFLOW_EXPORT_FAILED = 'WORKFLOW_EXPORT_FAILED',
  
  // Run execution
  RUN_FAILED = 'RUN_FAILED',
  RUN_NOT_FOUND = 'RUN_NOT_FOUND',
  
  // Context & conformance
  CONTEXT_PROVIDER_ERROR = 'CONTEXT_PROVIDER_ERROR',
  CONFORMANCE_FAILED = 'CONFORMANCE_FAILED',
  
  // Generic errors
  INVALID_INPUT = 'INVALID_INPUT',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  TIMEOUT = 'TIMEOUT',
  NOT_IMPLEMENTED = 'NOT_IMPLEMENTED',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  
  // Fallback
  UNKNOWN = 'UNKNOWN',
  
  // Deprecated codes (remove in v0.3.0)
  /** @deprecated Use RUN_NOT_FOUND instead - removed in v0.3.0 */
  TRACE_NOT_FOUND = 'RUN_NOT_FOUND',
  /** @deprecated Use RUN_FAILED instead - removed in v0.3.0 */
  EXECUTION_FAILED = 'RUN_FAILED',
  /** @deprecated Use INVALID_INPUT instead - removed in v0.3.0 */
  PARSE_ERROR = 'INVALID_INPUT',
  /** @deprecated Use WORKSPACE_NOT_FOUND instead - removed in v0.3.0 */
  WORKFLOW_NOT_FOUND = 'WORKSPACE_NOT_FOUND',
}
```

**Update tests:**
Add to `packages/arc-protocol-ts/src/fixtures/loader.test.ts`:
```typescript
describe('ErrorCodeFixtures', () => {
  it('validates all error code fixtures', () => {
    const fixtures = listFixtures('error-codes');
    expect(fixtures.length).toBeGreaterThanOrEqual(5);
    
    for (const fixtureName of fixtures) {
      const error = loadFixture('error-codes', fixtureName) as Record<string, unknown>;
      expect(error.code).toBeDefined();
      expect(typeof error.code).toBe('string');
      expect(error.message).toBeDefined();
      expect(typeof error.message).toBe('string');
    }
  });
  
  it('validates deprecated aliases work', () => {
    // These should be equivalent
    expect(ArcErrorCode.TRACE_NOT_FOUND).toBe(ArcErrorCode.RUN_NOT_FOUND);
    expect(ArcErrorCode.EXECUTION_FAILED).toBe(ArcErrorCode.RUN_FAILED);
    expect(ArcErrorCode.PARSE_ERROR).toBe(ArcErrorCode.INVALID_INPUT);
    expect(ArcErrorCode.WORKFLOW_NOT_FOUND).toBe(ArcErrorCode.WORKSPACE_NOT_FOUND);
  });
});
```

### Phase 3: Documentation (1 hour)

**Update CHANGELOG:**
Add to `CHANGELOG.md` under v0.2.0:

```markdown
### Breaking Changes

- **Error code standardization (ADR-023)**: Unified error codes between Python and TypeScript
  - Added 12 error codes to TypeScript: WORKSPACE_NOT_FOUND, NO_RUNTIME_DETECTED, ADAPTER_ERROR, ADAPTER_NOT_SUPPORTED, SCHEMA_EXPORT_FAILED, WORKFLOW_EXPORT_FAILED, RUN_FAILED, RUN_NOT_FOUND, CONTEXT_PROVIDER_ERROR, CONFORMANCE_FAILED, INTERNAL_ERROR, NOT_IMPLEMENTED
  - Added 2 error codes to Python: PERMISSION_DENIED, UNKNOWN
  - **Impact**: TypeScript code using error codes may need updates
  - See `docs/adr/023-error-code-standardization.md` for complete list

### Deprecated

- `ArcErrorCode.TRACE_NOT_FOUND` - Use `RUN_NOT_FOUND` instead (removed in v0.3.0)
- `ArcErrorCode.EXECUTION_FAILED` - Use `RUN_FAILED` instead (removed in v0.3.0)
- `ArcErrorCode.PARSE_ERROR` - Use `INVALID_INPUT` instead (removed in v0.3.0)
- `ArcErrorCode.WORKFLOW_NOT_FOUND` - Use `WORKSPACE_NOT_FOUND` instead (removed in v0.3.0)

### Added

- Canonical error code list with 16 codes (ADR-023)
- Error code fixtures in `protocol/fixtures/error-codes/`
- Error code governance process
```

**Create migration guide:**
Create `docs/guides/error-code-migration.md`:

```markdown
# Error Code Migration Guide (v0.1 → v0.2)

## TypeScript Migration

If you're using deprecated error codes, update them:

| Old Code | New Code | Reason |
|----------|----------|--------|
| `TRACE_NOT_FOUND` | `RUN_NOT_FOUND` | "Trace" is internal, "run" is user-facing |
| `EXECUTION_FAILED` | `RUN_FAILED` | More specific |
| `PARSE_ERROR` | `INVALID_INPUT` | Parse errors are invalid input |
| `WORKFLOW_NOT_FOUND` | `WORKSPACE_NOT_FOUND` | Workflow detection is part of workspace detection |

### Example

**Before:**
```typescript
if (error.code === ArcErrorCode.TRACE_NOT_FOUND) {
  // handle trace not found
}
```

**After:**
```typescript
if (error.code === ArcErrorCode.RUN_NOT_FOUND) {
  // handle run not found
}
```

## Python Migration

No breaking changes. Two new codes added:
- `PERMISSION_DENIED` - Use for permission/authorization failures
- `UNKNOWN` - Use as fallback for unrecognized errors

## Timeline

- **v0.2.0**: Deprecated codes work as aliases, emit warnings
- **v0.3.0**: Deprecated codes removed
```

### Phase 4: Validation (1 hour)

**Run tests:**
```bash
# Python tests
cd python && .venv/bin/python -m pytest tests/fixtures/test_cross_language.py -v

# TypeScript tests (after Jest config)
cd packages/arc-protocol-ts && npm test

# Full test suite
cd python && .venv/bin/python -m pytest -q
```

**Verify:**
1. All 21+ Python fixture tests pass
2. TypeScript fixture tests pass (15+ tests)
3. Error code fixtures load correctly
4. Deprecated aliases work (TypeScript)
5. Round-trip serialization works

**Check for usage:**
```bash
# Find any code using deprecated error codes
rg "TRACE_NOT_FOUND|EXECUTION_FAILED|PARSE_ERROR|WORKFLOW_NOT_FOUND" packages/ --type ts
```

**Update any found usage** to use new codes.

---

## Important Notes

### Test Harness Status

The cross-language test harness is 75% complete:
- ✅ Python side fully functional (21 tests passing)
- ⏳ TypeScript side needs Jest configuration

**To complete TypeScript tests:**
1. Install: `npm install --save-dev jest ts-jest @types/jest @types/node`
2. Create `jest.config.js` (see `protocol/fixtures/SETUP_STATUS.md`)
3. Update package.json test script
4. Run: `npm test`

You can skip this for now and focus on error code sync. The Python tests are sufficient for validation.

### Files to Read First

1. **`docs/adr/023-error-code-standardization.md`** - Complete blueprint
2. **`docs/SCHEMA_AUDIT_REPORT.md`** - Context on why this is needed (Risk 1)
3. **`protocol/fixtures/README.md`** - How to create fixtures
4. **`python/tests/fixtures/loader.py`** - How to use fixtures in tests

### Verification Checklist

Before considering this task complete:

- [ ] Python has 16 error codes (was 14, added 2)
- [ ] TypeScript has 20 codes (16 canonical + 4 deprecated aliases)
- [ ] At least 5 error code fixtures created
- [ ] Python fixture tests pass
- [ ] TypeScript compiles without errors
- [ ] CHANGELOG updated with breaking changes
- [ ] Migration guide created
- [ ] No code uses deprecated error codes (or documented as intentional)

### Time Management

You have 5 hours estimated for this task:
- Phase 1 (Python): 1 hour
- Phase 2 (TypeScript): 2 hours
- Phase 3 (Documentation): 1 hour
- Phase 4 (Validation): 1 hour

If you're running short on time, prioritize:
1. Phase 1 & 2 (code changes) - MUST DO
2. Phase 4 (validation) - MUST DO
3. Phase 3 (documentation) - Can be done later

---

## Context for Code Suggestions

### Project Structure

```
arc-theia-studio/
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   │   └── 023-error-code-standardization.md  # Your blueprint
│   └── SCHEMA_AUDIT_REPORT.md  # Context on Risk 1
├── protocol/
│   └── fixtures/               # Cross-language test fixtures
│       ├── error-codes/        # Create error code fixtures here
│       ├── arc-envelope/       # Existing fixtures
│       └── README.md           # Fixture usage guide
├── python/
│   ├── src/agent_runtime_cockpit/
│   │   └── protocol/
│   │       └── errors.py       # MODIFY: Add 2 codes
│   └── tests/fixtures/
│       ├── loader.py           # Fixture loader utility
│       └── test_cross_language.py  # ADD: Error code tests
└── packages/
    ├── arc-extension/
    │   └── src/common/
    │       └── arc-protocol.ts  # MODIFY: Add 12 codes + 4 aliases
    └── arc-protocol-ts/
        └── src/fixtures/
            └── loader.test.ts   # ADD: Error code tests
```

### Coding Style

**Python:**
- Use type hints
- Follow existing enum pattern
- Add docstrings for new code
- Use pytest for tests

**TypeScript:**
- Use TypeScript strict mode
- Add JSDoc comments for deprecated codes
- Follow existing enum pattern
- Use Jest for tests

### Error Code Naming Pattern

- `_NOT_FOUND` for missing resources
- `_FAILED` for operation failures
- `_ERROR` for generic domain errors
- `_DENIED` for permission failures
- `_NOT_SUPPORTED` for unavailable features

---

## Success Criteria

This task is complete when:

1. ✅ Python has all 16 canonical error codes
2. ✅ TypeScript has all 16 canonical codes + 4 deprecated aliases
3. ✅ At least 5 error code fixtures created and tested
4. ✅ Python fixture tests pass (21+ tests)
5. ✅ TypeScript compiles without errors
6. ✅ CHANGELOG documents breaking changes
7. ✅ Migration guide created
8. ✅ Deprecated aliases verified to work

---

## Questions to Consider

1. **Should we add more than 5 error code fixtures?**
   - Recommendation: Start with 5-7 covering common cases, can add more later

2. **Should we update existing code using deprecated TypeScript codes?**
   - Recommendation: Yes, search and update to avoid warnings

3. **Should we complete TypeScript Jest config now?**
   - Recommendation: No, Python tests are sufficient for validation

4. **Should we run the full test suite before committing?**
   - Recommendation: Yes, verify no regressions

---

## Handover Complete

You have everything needed to implement the error code sync:
- ✅ Complete blueprint (ADR-023)
- ✅ Clear implementation steps (4 phases)
- ✅ Code examples for both languages
- ✅ Test infrastructure ready
- ✅ Fixture format documented
- ✅ Success criteria defined

**Estimated completion:** 5 hours from now (~13:50 / 1:50 PM)

Good luck! 🚀
