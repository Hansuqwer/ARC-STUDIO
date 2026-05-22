# P2 ArcBackendService Split - Migration Plan

**Status:** Ready for execution  
**Created:** 2026-05-22  
**Estimated Effort:** 4-6 hours  
**Risk Level:** Medium (half-done refactor is highest-friction state)

## Executive Summary

This document provides a detailed migration plan to complete Phase 2 (P2) of the ArcBackendService refactoring. The skeleton services exist with method signatures, but all implementations still reside in ArcBackendService. This plan outlines the exact steps to migrate 30 methods across 3 services.

## Current State Analysis

### Skeleton Services (Created, Not Implemented)
- ✅ `ConfigService` - 14 method signatures (all throw "Not yet implemented")
- ✅ `RunLifecycleService` - 13 method signatures (all throw "Not yet implemented")
- ✅ `AuditBridgeService` - 3 method signatures (all throw "Not yet implemented")
- ✅ DI bindings in `arc-extension-backend-module.ts` (lines 28-30)

### ArcBackendService Current State
- **Total lines:** 1769
- **Methods to migrate:** 30
- **Current dependencies:** WorkflowExecutor, TraceParser, WorkflowDetector, FileManager
- **New dependencies needed:** ConfigService, RunLifecycleService, AuditBridgeService

### Callers Identified
- `arc-extension-backend-module.ts` - DI bindings (line 33-38, 42-44)
- `arc-status-bar-contribution.ts` - calls `getConfigStatus()` (line 51)
- `arc-service.integration.test.ts` - integration tests
- `arc-service.proxy.test.ts` - proxy tests
- Various contract tests (read-only, no changes needed)

## Migration Strategy

### Approach: Composition with Delegation
1. Migrate method implementations from ArcBackendService to new services
2. Update ArcBackendService to inject new services via constructor
3. Replace method implementations with delegation calls
4. Keep ArcBackendService as facade for backward compatibility
5. Add @deprecated annotations with removal target

### Why This Approach?
- **Minimal breaking changes** - existing callers continue to work
- **Incremental migration** - can migrate one service at a time
- **Testable** - can verify each service independently
- **Reversible** - can roll back if issues arise

## Detailed Migration Plan

### Step 1: Migrate ConfigService (14 methods, ~2 hours)

#### 1.1 Update ConfigService Implementation
**File:** `packages/arc-extension/src/node/services/config-service.ts`

**Dependencies needed:**
- Import `execFileSync` from 'child_process' (already imported)
- Import `buildArcCliEnv` helper (need to extract from ArcBackendService)
- Import all protocol types (already imported)

**Methods to migrate (with line numbers in ArcBackendService):**

1. `getProviderStatus` (516-546) - calls arc CLI
2. `getWorkspaceStatus` (551-557) - simple return, needs workspaceRoot
3. `getConfigStatus` (566-663) - calls arc CLI
4. `saveConfig` (669-724) - calls arc CLI, uses SAFE_CONFIG_KEYS constant
5. `listProfiles` (726-752) - calls arc CLI
6. `getIsolationStatus` (754-778) - calls arc CLI, uses mapIsolationProviders helper
7. `listIsolationProviders` (780-794) - calls arc CLI, uses mapIsolationProviders helper
8. `getProviderCatalog` (806-826) - calls arc CLI
9. `getProviderDiagnostics` (828-852) - calls arc CLI
10. `getProviderQuota` (854-883) - calls arc CLI
11. `resetProviderQuota` (885-915) - calls arc CLI
12. `runGatedProviderAction` (917-957) - calls arc CLI, uses mapGatedProviderActionOutput helper
13. `setProviderKeyRef` (996-1014) - calls arc CLI
14. `unsetProviderKeyRef` (1016-1024) - calls arc CLI

**Helpers to migrate:**
- `mapIsolationProviders` (796-804) - private helper
- `mapGatedProviderActionOutput` (959-994) - private helper

**Constants to migrate:**
- `SAFE_CONFIG_KEYS` (line 82)
- `UNSAFE_CONFIG_KEY_PATTERN` (line 83)
- `TRUST_SENSITIVE_FLAGS` (lines 74-80)

**Patch 1.1: ConfigService Implementation**
```typescript
// Add workspaceRoot to constructor
constructor(
    @inject('WorkspaceRoot') private readonly workspaceRoot: string
) {}

// Copy all 14 method implementations from ArcBackendService
// Copy helper methods: mapIsolationProviders, mapGatedProviderActionOutput
// Copy constants: SAFE_CONFIG_KEYS, UNSAFE_CONFIG_KEY_PATTERN, TRUST_SENSITIVE_FLAGS
```

#### 1.2 Update ArcBackendService to Inject ConfigService
**File:** `packages/arc-extension/src/node/arc-backend-service.ts`

**Patch 1.2: Add ConfigService Injection**
```typescript
constructor(
    executor?: WorkflowExecutor,
    parser?: TraceParser,
    detector?: WorkflowDetector,
    fileManager?: FileManager,
    configService?: ConfigService  // NEW
) {
    this.executor = executor ?? new WorkflowExecutor();
    this.parser = parser ?? new TraceParser();
    this.detector = detector ?? new WorkflowDetector();
    this.fileManager = fileManager ?? new FileManager();
    this.configService = configService ?? new ConfigService(this.workspaceRoot);  // NEW
    this.workspaceRoot = validateWorkspaceRoot(process.cwd());
}
```

#### 1.3 Replace ConfigService Methods with Delegation
**File:** `packages/arc-extension/src/node/arc-backend-service.ts`

**Patch 1.3: Delegate to ConfigService**
```typescript
/**
 * @deprecated Use ConfigService.getProviderStatus() directly. Will be removed in v0.3.0.
 */
async getProviderStatus(provider: string, baseUrl?: string): Promise<ProviderStatus> {
    return this.configService.getProviderStatus(provider, baseUrl);
}

// Repeat for all 14 ConfigService methods
```

#### 1.4 Update DI Bindings
**File:** `packages/arc-extension/src/node/arc-extension-backend-module.ts`

**Patch 1.4: Inject ConfigService into ArcBackendService**
```typescript
bind(ArcBackendService).toDynamicValue(ctx => new ArcBackendService(
    ctx.container.get(WorkflowExecutor),
    ctx.container.get(TraceParser),
    ctx.container.get(WorkflowDetector),
    ctx.container.get(FileManager),
    ctx.container.get(ConfigService)  // NEW
)).inSingletonScope();
```

**Patch 1.5: Bind WorkspaceRoot for ConfigService**
```typescript
// Add before ConfigService binding
bind('WorkspaceRoot').toDynamicValue(() => {
    return process.cwd();
}).inSingletonScope();

bind(ConfigService).toSelf().inSingletonScope();
```

#### 1.6 Verification
```bash
# Build
pnpm --filter arc-extension build

# Run tests
pnpm --filter arc-extension test

# Verify no regressions
pnpm check:pr
```

---

### Step 2: Migrate RunLifecycleService (13 methods, ~2 hours)

#### 2.1 Update RunLifecycleService Implementation
**File:** `packages/arc-extension/src/node/services/run-lifecycle-service.ts`

**Dependencies needed:**
- Import `execFileSync` from 'child_process'
- Import `buildArcCliEnv` helper
- Import `validateTraceId`, `validateRunId` from '../security-utils'
- Import `ArcError`, `ArcErrorCode` from '../../common/arc-protocol'
- Import `path` module
- Add `workspaceRoot` to constructor
- Add `activeStreamCancels` map for stream management

**Methods to migrate (with line numbers in ArcBackendService):**

1. `executeWorkflow` (124-133) - delegates to executor, uses fileManager
2. `cancelWorkflow` (138-140) - delegates to executor
3. `getTraces` (147-149) - delegates to fileManager
4. `readTrace` (154-181) - uses fileManager + parser
5. `streamTrace` (186-216) - uses fileManager + parser
6. `streamActiveTrace` (218-226) - custom implementation, uses activeStreamCancels
7. `readActiveTraceStream` (228-235) - uses streamActiveTrace
8. `cancelActiveTraceStream` (237-246) - uses activeStreamCancels
9. `validateTrace` (251-341) - uses fileManager + parser
10. `detectWorkflows` (348-350) - delegates to detector
11. `listRuntimeCapabilities` (357-389) - calls arc CLI
12. `preflightRun` (391-455) - calls arc CLI
13. `startRun` (457-511) - calls arc CLI

**Helpers to migrate:**
- `createActiveTraceIterable` (need to find this method)
- `mapRuntimeCapability` (need to find this method)
- `fileExists` (need to find this method)
- `readFileContent` (need to find this method)

**Patch 2.1: RunLifecycleService Implementation**
```typescript
constructor(
    @inject(WorkflowExecutor) private readonly executor: WorkflowExecutor,
    @inject(TraceParser) private readonly parser: TraceParser,
    @inject(WorkflowDetector) private readonly detector: WorkflowDetector,
    @inject(FileManager) private readonly fileManager: FileManager,
    @inject('WorkspaceRoot') private readonly workspaceRoot: string
) {
    this.activeStreamCancels = new Map<string, { cancelled: boolean }>();
}

// Copy all 13 method implementations from ArcBackendService
// Copy helper methods
```

#### 2.2 Update ArcBackendService to Inject RunLifecycleService
**Patch 2.2: Add RunLifecycleService Injection**
```typescript
constructor(
    executor?: WorkflowExecutor,
    parser?: TraceParser,
    detector?: WorkflowDetector,
    fileManager?: FileManager,
    configService?: ConfigService,
    runLifecycleService?: RunLifecycleService  // NEW
) {
    // ... existing code ...
    this.runLifecycleService = runLifecycleService ?? new RunLifecycleService(
        this.executor,
        this.parser,
        this.detector,
        this.fileManager,
        this.workspaceRoot
    );
}
```

#### 2.3 Replace RunLifecycleService Methods with Delegation
**Patch 2.3: Delegate to RunLifecycleService**
```typescript
/**
 * @deprecated Use RunLifecycleService.executeWorkflow() directly. Will be removed in v0.3.0.
 */
async executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult> {
    return this.runLifecycleService.executeWorkflow(prompt, options);
}

// Repeat for all 13 RunLifecycleService methods
```

#### 2.4 Update DI Bindings
**Patch 2.4: Inject RunLifecycleService into ArcBackendService**
```typescript
bind(ArcBackendService).toDynamicValue(ctx => new ArcBackendService(
    ctx.container.get(WorkflowExecutor),
    ctx.container.get(TraceParser),
    ctx.container.get(WorkflowDetector),
    ctx.container.get(FileManager),
    ctx.container.get(ConfigService),
    ctx.container.get(RunLifecycleService)  // NEW
)).inSingletonScope();
```

#### 2.5 Verification
```bash
pnpm --filter arc-extension build
pnpm --filter arc-extension test
pnpm check:pr
```

---

### Step 3: Migrate AuditBridgeService (3 methods, ~1 hour)

#### 3.1 Update AuditBridgeService Implementation
**File:** `packages/arc-extension/src/node/services/audit-bridge-service.ts`

**Dependencies needed:**
- Import `execFileSync` from 'child_process'
- Import `buildArcCliEnv` helper
- Import `validateRunId` from '../security-utils'
- Import `ArcError`, `ArcErrorCode` from '../../common/arc-protocol'
- Import `path` module
- Import `fs-extra` for file operations
- Add `workspaceRoot` to constructor

**Methods to migrate (with line numbers in ArcBackendService):**

1. `getRunLinks` (1032-1071) - calls arc CLI
2. `getRunReceipt` (1078-1096) - reads from filesystem
3. `getRunAutopsy` (1101-1119) - reads from filesystem

**Patch 3.1: AuditBridgeService Implementation**
```typescript
constructor(
    @inject('WorkspaceRoot') private readonly workspaceRoot: string
) {}

// Copy all 3 method implementations from ArcBackendService
```

#### 3.2 Update ArcBackendService to Inject AuditBridgeService
**Patch 3.2: Add AuditBridgeService Injection**
```typescript
constructor(
    executor?: WorkflowExecutor,
    parser?: TraceParser,
    detector?: WorkflowDetector,
    fileManager?: FileManager,
    configService?: ConfigService,
    runLifecycleService?: RunLifecycleService,
    auditBridgeService?: AuditBridgeService  // NEW
) {
    // ... existing code ...
    this.auditBridgeService = auditBridgeService ?? new AuditBridgeService(this.workspaceRoot);
}
```

#### 3.3 Replace AuditBridgeService Methods with Delegation
**Patch 3.3: Delegate to AuditBridgeService**
```typescript
/**
 * @deprecated Use AuditBridgeService.getRunLinks() directly. Will be removed in v0.3.0.
 */
async getRunLinks(runId: string, filter?: string, stableId?: string): Promise<RunLinksResponse> {
    return this.auditBridgeService.getRunLinks(runId, filter, stableId);
}

// Repeat for all 3 AuditBridgeService methods
```

#### 3.4 Update DI Bindings
**Patch 3.4: Inject AuditBridgeService into ArcBackendService**
```typescript
bind(ArcBackendService).toDynamicValue(ctx => new ArcBackendService(
    ctx.container.get(WorkflowExecutor),
    ctx.container.get(TraceParser),
    ctx.container.get(WorkflowDetector),
    ctx.container.get(FileManager),
    ctx.container.get(ConfigService),
    ctx.container.get(RunLifecycleService),
    ctx.container.get(AuditBridgeService)  // NEW
)).inSingletonScope();
```

#### 3.5 Verification
```bash
pnpm --filter arc-extension build
pnpm --filter arc-extension test
pnpm check:pr
```

---

### Step 4: Extract Shared Utilities (~30 minutes)

#### 4.1 Create Shared Utilities Module
**File:** `packages/arc-extension/src/node/services/arc-cli-utils.ts`

**Patch 4.1: Extract Shared Utilities**
```typescript
/**
 * Shared utilities for calling the ARC Python CLI
 */

const ARC_CLI_ENV_ALLOWLIST = ['PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR'];

export function buildArcCliEnv(): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {};
    for (const key of ARC_CLI_ENV_ALLOWLIST) {
        const value = process.env[key];
        if (value !== undefined) {
            env[key] = value;
        }
    }
    return env;
}

export const SAFE_CONFIG_KEYS = ['defaultRuntime', 'mode', 'isolation', 'allowPaidCalls', 'dryRun', 'routingMode', 'selectedProfile'];
export const UNSAFE_CONFIG_KEY_PATTERN = /(secret|token|password|api[_-]?key|raw.*key|credential)/i;
export const TRUST_SENSITIVE_FLAGS = [
    'can_run',
    'requires_paid_calls',
    'requires_shell',
    'requires_secrets',
    'requires_network',
];
```

#### 4.2 Update Imports
- Update ConfigService to import from './arc-cli-utils'
- Update RunLifecycleService to import from './arc-cli-utils'
- Update AuditBridgeService to import from './arc-cli-utils'
- Update ArcBackendService to import from './services/arc-cli-utils'

---

### Step 5: Final Verification & Documentation (~30 minutes)

#### 5.1 Full Test Suite
```bash
# Python tests
cd python && uv run pytest -q

# Python linting
cd python && uv run ruff check src tests

# TypeScript protocol
pnpm --filter @arc-studio/protocol build
pnpm --filter @arc-studio/protocol test

# Extension build
pnpm --filter arc-extension build

# Extension tests
pnpm --filter arc-extension test

# PR checks
pnpm check:pr
```

#### 5.2 Update Documentation
**File:** `docs/refactor/arc-backend-service-split.md`

Add completion status:
```markdown
## Implementation Status

✅ **Phase 1: Structural Setup** (Completed 2026-05-19)
- Created service skeletons with method signatures
- Updated DI bindings
- All services compile and are injectable

✅ **Phase 2: Method Migration** (Completed 2026-05-22)
- Migrated 14 ConfigService methods
- Migrated 13 RunLifecycleService methods
- Migrated 3 AuditBridgeService methods
- Extracted shared utilities to arc-cli-utils.ts
- Updated ArcBackendService to delegate to new services
- Added @deprecated annotations with removal target v0.3.0

**Next Steps:**
- Monitor usage for 1 minor + 1 patch cycle (per ADR-022)
- Remove ArcBackendService delegation layer in v0.3.0
- Update callers to inject services directly
```

#### 5.3 Update IMPLEMENTATION_SUMMARY.md
**File:** `IMPLEMENTATION_SUMMARY.md`

Update P2 status:
```markdown
**P2: arc-backend-service refactor** [HIGH, 10h - COMPLETED 2026-05-22]
- ✅ Created service skeletons with method signatures
- ✅ Migrated 30 methods from ArcBackendService to new services
- ✅ Updated DI bindings to inject new services
- ✅ ArcBackendService now delegates to new services
- ✅ Added @deprecated annotations with removal target v0.3.0
- ✅ Extracted shared utilities to arc-cli-utils.ts
- **Verification:** All tests pass, build clean
- **Commit:** [commit hash]
```

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation:** Keep ArcBackendService as facade, all existing callers continue to work

### Risk 2: Test Failures
**Mitigation:** Run full test suite after each service migration, fix issues before proceeding

### Risk 3: Missing Helper Methods
**Mitigation:** Grep for all helper methods before migration, ensure all are copied

### Risk 4: Circular Dependencies
**Mitigation:** Services are independent, no cross-service dependencies

### Risk 5: DI Configuration Errors
**Mitigation:** Test DI bindings after each service, verify singleton scope

---

## Rollback Plan

If issues arise during migration:

1. **Revert to previous commit** - All changes are in version control
2. **Keep skeleton services** - They're harmless if not used
3. **Remove DI bindings** - Comment out new service bindings in arc-extension-backend-module.ts
4. **Restore ArcBackendService** - Revert to original implementation

---

## Success Criteria

- ✅ All 30 methods migrated to new services
- ✅ ArcBackendService delegates to new services
- ✅ All tests pass (TypeScript + Python)
- ✅ Build succeeds with no errors
- ✅ No breaking changes for existing callers
- ✅ Documentation updated
- ✅ @deprecated annotations added

---

## Execution Checklist

### Pre-Migration
- [ ] Read this plan thoroughly
- [ ] Verify current test baseline (all tests passing)
- [ ] Create feature branch: `git checkout -b refactor/p2-service-migration`

### ConfigService Migration
- [ ] Extract shared utilities to arc-cli-utils.ts
- [ ] Migrate 14 ConfigService methods
- [ ] Update ArcBackendService to inject ConfigService
- [ ] Replace methods with delegation
- [ ] Update DI bindings
- [ ] Run tests: `pnpm --filter arc-extension build && pnpm --filter arc-extension test`
- [ ] Commit: `git commit -m "refactor(P2): migrate ConfigService methods"`

### RunLifecycleService Migration
- [ ] Migrate 13 RunLifecycleService methods
- [ ] Update ArcBackendService to inject RunLifecycleService
- [ ] Replace methods with delegation
- [ ] Update DI bindings
- [ ] Run tests: `pnpm --filter arc-extension build && pnpm --filter arc-extension test`
- [ ] Commit: `git commit -m "refactor(P2): migrate RunLifecycleService methods"`

### AuditBridgeService Migration
- [ ] Migrate 3 AuditBridgeService methods
- [ ] Update ArcBackendService to inject AuditBridgeService
- [ ] Replace methods with delegation
- [ ] Update DI bindings
- [ ] Run tests: `pnpm --filter arc-extension build && pnpm --filter arc-extension test`
- [ ] Commit: `git commit -m "refactor(P2): migrate AuditBridgeService methods"`

### Final Verification
- [ ] Run full test suite (Python + TypeScript)
- [ ] Run `pnpm check:pr`
- [ ] Update docs/refactor/arc-backend-service-split.md
- [ ] Update IMPLEMENTATION_SUMMARY.md
- [ ] Commit: `git commit -m "docs(P2): update refactor documentation"`
- [ ] Push: `git push -u origin refactor/p2-service-migration`

### Post-Migration
- [ ] Tag release: `git tag v0.8.3-alpha`
- [ ] Push tag: `git push origin v0.8.3-alpha`
- [ ] Monitor for issues in next 2 weeks
- [ ] Plan removal of ArcBackendService delegation layer for v0.3.0

---

## Estimated Timeline

| Task | Estimated Time | Cumulative |
|------|---------------|------------|
| Extract shared utilities | 30 min | 0.5h |
| Migrate ConfigService | 2 hours | 2.5h |
| Migrate RunLifecycleService | 2 hours | 4.5h |
| Migrate AuditBridgeService | 1 hour | 5.5h |
| Final verification | 30 min | 6h |
| Documentation updates | 30 min | 6.5h |

**Total: 6-7 hours** (including breaks and issue resolution)

---

## Notes

- This plan assumes all tests are currently passing
- Each service migration is independent and can be done in separate commits
- The order matters: ConfigService → RunLifecycleService → AuditBridgeService
- Keep commits small and focused for easy rollback
- Run tests after each service migration, not just at the end
- If a test fails, fix it before proceeding to the next service

---

**Plan Status:** Ready for execution  
**Last Updated:** 2026-05-22  
**Next Action:** Execute Step 4.1 (Extract shared utilities)
