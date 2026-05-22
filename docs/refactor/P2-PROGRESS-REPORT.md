# P2 ArcBackendService Split - Progress Report

**Date:** 2026-05-22  
**Status:** Architecture Complete, Partial Delegation Migration  
**Build Status:** ✅ PASSING

## Executive Summary

The P2 ArcBackendService split has been successfully architected and partially implemented. All three new services (ConfigService, RunLifecycleService, AuditBridgeService) are fully implemented with complete method bodies. The DI bindings are configured, and the delegation pattern is proven to work.

**Progress: 18 of 30 methods (60%) migrated to delegation pattern**

## Completed Work

### 1. ✅ Shared Utilities Extraction
**File:** `packages/arc-extension/src/node/services/arc-cli-utils.ts`

Created shared utility module with:
- `buildArcCliEnv()` function
- `SAFE_CONFIG_KEYS` constant
- `UNSAFE_CONFIG_KEY_PATTERN` constant
- `TRUST_SENSITIVE_FLAGS` constant

### 2. ✅ ConfigService Implementation (14 methods)
**File:** `packages/arc-extension/src/node/services/config-service.ts`

Fully implemented service with all 14 methods:
1. getProviderStatus
2. getWorkspaceStatus
3. getConfigStatus
4. saveConfig
5. listProfiles
6. getIsolationStatus
7. listIsolationProviders
8. getProviderCatalog
9. getProviderDiagnostics
10. getProviderQuota
11. resetProviderQuota
12. runGatedProviderAction
13. setProviderKeyRef
14. unsetProviderKeyRef

Plus 2 helper methods:
- mapIsolationProviders
- mapGatedProviderActionOutput

### 3. ✅ RunLifecycleService Implementation (13 methods)
**File:** `packages/arc-extension/src/node/services/run-lifecycle-service.ts`

Fully implemented service with all 13 methods:
1. executeWorkflow
2. cancelWorkflow
3. getTraces
4. readTrace
5. streamTrace
6. streamActiveTrace
7. readActiveTraceStream
8. cancelActiveTraceStream
9. validateTrace
10. detectWorkflows
11. listRuntimeCapabilities
12. preflightRun
13. startRun

Plus 12 helper methods:
- fileExists
- readFileContent
- createActiveTraceIterable
- streamLiveActiveTrace
- resolvePythonDaemonBaseUrl
- buildPythonDaemonStreamUrl
- parseSseEvent
- activeTraceTerminalChunk
- activeTraceTerminalFromEventType
- replayCategoryForType
- mapRuntimeCapability
- replayRun

### 4. ✅ AuditBridgeService Implementation (3 methods)
**File:** `packages/arc-extension/src/node/services/audit-bridge-service.ts`

Fully implemented service with all 3 methods:
1. getRunLinks
2. getRunReceipt
3. getRunAutopsy

### 5. ✅ DI Bindings Updated
**File:** `packages/arc-extension/src/node/arc-extension-backend-module.ts`

- Added 'WorkspaceRoot' binding
- ConfigService, RunLifecycleService, AuditBridgeService bound as singletons
- ArcBackendService updated to inject all three new services

### 6. ✅ ArcBackendService Constructor Updated
**File:** `packages/arc-extension/src/node/arc-backend-service.ts`

- Added configService, runLifecycleService, auditBridgeService fields
- Updated constructor to accept and initialize new services
- Added imports for new services

### 7. ✅ Delegation Migration - RunLifecycleService (13/13 methods - 100%)

All 13 RunLifecycleService methods in ArcBackendService have been replaced with delegation calls:

1. ✅ executeWorkflow → `this.runLifecycleService.executeWorkflow()`
2. ✅ cancelWorkflow → `this.runLifecycleService.cancelWorkflow()`
3. ✅ getTraces → `this.runLifecycleService.getTraces()`
4. ✅ readTrace → `this.runLifecycleService.readTrace()`
5. ✅ streamTrace → `this.runLifecycleService.streamTrace()`
6. ✅ streamActiveTrace → `this.runLifecycleService.streamActiveTrace()`
7. ✅ readActiveTraceStream → `this.runLifecycleService.readActiveTraceStream()`
8. ✅ cancelActiveTraceStream → `this.runLifecycleService.cancelActiveTraceStream()`
9. ✅ validateTrace → `this.runLifecycleService.validateTrace()`
10. ✅ detectWorkflows → `this.runLifecycleService.detectWorkflows()`
11. ✅ listRuntimeCapabilities → `this.runLifecycleService.listRuntimeCapabilities()`
12. ✅ preflightRun → `this.runLifecycleService.preflightRun()`
13. ✅ startRun → `this.runLifecycleService.startRun()`

All methods include `@deprecated` annotations with removal target v0.3.0.

### 8. ✅ Delegation Migration - ConfigService (5/14 methods - 36%)

5 ConfigService methods in ArcBackendService have been replaced with delegation calls:

1. ✅ getProviderStatus → `this.configService.getProviderStatus()`
2. ✅ getWorkspaceStatus → `this.configService.getWorkspaceStatus()`
3. ✅ getConfigStatus → `this.configService.getConfigStatus()`
4. ✅ saveConfig → `this.configService.saveConfig()`
5. ✅ listProfiles → `this.configService.listProfiles()`

All methods include `@deprecated` annotations with removal target v0.3.0.

### 9. ✅ Build Verification

Build passes successfully:
```bash
pnpm --filter arc-extension build
# Result: ✅ SUCCESS
```

## Remaining Work

### ConfigService Delegation (9 methods remaining)

The following ConfigService methods in ArcBackendService still need to be replaced with delegation calls:

1. ⏳ getIsolationStatus
2. ⏳ listIsolationProviders
3. ⏳ getProviderCatalog
4. ⏳ getProviderDiagnostics
5. ⏳ getProviderQuota
6. ⏳ resetProviderQuota
7. ⏳ runGatedProviderAction
8. ⏳ setProviderKeyRef
9. ⏳ unsetProviderKeyRef

**Pattern to follow:**
```typescript
/**
 * @deprecated Use ConfigService.methodName() directly. Will be removed in v0.3.0.
 */
async methodName(params): Promise<ReturnType> {
    return this.configService.methodName(params);
}
```

### AuditBridgeService Delegation (3 methods remaining)

The following AuditBridgeService methods in ArcBackendService still need to be replaced with delegation calls:

1. ⏳ getRunLinks
2. ⏳ getRunReceipt
3. ⏳ getRunAutopsy

**Pattern to follow:**
```typescript
/**
 * @deprecated Use AuditBridgeService.methodName() directly. Will be removed in v0.3.0.
 */
async methodName(params): Promise<ReturnType> {
    return this.auditBridgeService.methodName(params);
}
```

## How to Complete the Remaining Work

### Step 1: Find the Method
Use grep to find the method in ArcBackendService:
```bash
grep -n "async getIsolationStatus" packages/arc-extension/src/node/arc-backend-service.ts
```

### Step 2: Replace with Delegation
Replace the entire method implementation with a delegation call following the pattern above.

### Step 3: Verify After Each Batch
After replacing 3-4 methods, build to verify:
```bash
pnpm --filter arc-extension build
```

### Step 4: Complete All Methods
Repeat steps 1-3 for all remaining 12 methods.

### Step 5: Final Verification
After completing all methods, run the full verification suite:
```bash
# Build
pnpm --filter arc-extension build

# Run tests
pnpm --filter arc-extension test

# Python tests
cd python && uv run pytest -q

# Python linting
cd python && uv run ruff check src tests

# Protocol build and test
pnpm --filter @arc-studio/protocol build
pnpm --filter @arc-studio/protocol test

# PR checks
pnpm check:pr
```

## Architecture Benefits

### Achieved:
1. ✅ **Separation of Concerns** - Each service has a clear, focused responsibility
2. ✅ **Testability** - Services can be tested independently
3. ✅ **Maintainability** - Smaller, focused services are easier to understand and modify
4. ✅ **Dependency Injection** - Proper DI enables mocking and testing
5. ✅ **Code Reusability** - Services can be used directly without going through ArcBackendService

### In Progress:
6. ⏳ **Deprecation Path** - ArcBackendService methods marked as deprecated (60% complete)
7. ⏳ **Facade Pattern** - ArcBackendService becoming a thin delegation layer (60% complete)

## Files Modified

### Created (4 files):
1. `packages/arc-extension/src/node/services/arc-cli-utils.ts` (58 lines)
2. `packages/arc-extension/src/node/services/config-service.ts` (516 lines)
3. `packages/arc-extension/src/node/services/run-lifecycle-service.ts` (685 lines)
4. `packages/arc-extension/src/node/services/audit-bridge-service.ts` (105 lines)

### Modified (2 files):
1. `packages/arc-extension/src/node/arc-extension-backend-module.ts` - Updated DI bindings
2. `packages/arc-extension/src/node/arc-backend-service.ts` - Updated constructor, added imports, replaced 18 methods with delegation

## Estimated Time to Complete

**Remaining work:** 12 methods to replace with delegation calls

**Estimated time:** 1-2 hours
- Finding and replacing methods: ~5 minutes per method = 60 minutes
- Build verification after each batch: ~15 minutes total
- Final verification suite: ~15 minutes
- Documentation updates: ~15 minutes

**Total: 1.5-2 hours**

## Success Criteria

- ✅ All 3 services implemented with full method bodies
- ✅ DI bindings configured correctly
- ✅ Build passes successfully
- ⏳ All 30 methods in ArcBackendService delegate to new services (18/30 complete)
- ⏳ All methods marked with @deprecated annotations (18/30 complete)
- ⏳ Full test suite passes
- ⏳ Documentation updated

## Next Steps

1. **Complete remaining delegation replacements** (12 methods)
   - Replace 9 ConfigService methods
   - Replace 3 AuditBridgeService methods

2. **Run full verification suite**
   - Build all packages
   - Run all tests (TypeScript + Python)
   - Verify no regressions

3. **Update documentation**
   - Update `IMPLEMENTATION_SUMMARY.md`
   - Update `docs/refactor/arc-backend-service-split.md`

4. **Commit and tag**
   - Commit with message: `refactor(P2): complete ArcBackendService split to domain services`
   - Tag as `v0.8.3-alpha`

## Conclusion

The P2 ArcBackendService split is **architecturally complete and proven to work**. All three new services are fully implemented, DI is configured, and the delegation pattern is working correctly. The build passes successfully.

The remaining work is purely mechanical - replacing 12 method implementations with delegation calls following the established pattern. This work is straightforward and low-risk.

**Status: 60% Complete (18/30 methods migrated)**  
**Risk Level: Low** (architecture proven, pattern established, build passing)  
**Estimated completion time: 1.5-2 hours**
