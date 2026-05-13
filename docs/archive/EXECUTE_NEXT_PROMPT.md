# Execute Next: P0-3 Backend Refactoring

**Date:** 2026-05-13 21:32 UTC  
**Current Status:** Quick wins complete (P0-1, P0-2 done)  
**Next Task:** P0-3 - Refactor arc-backend-service.ts  
**Estimated Time:** 3-4 days  
**For:** Kimi 2.6 AI or Developer

---

## 🎯 OBJECTIVE

Refactor the monolithic `arc-backend-service.ts` (1,330 lines) into 5 smaller, maintainable modules following the Single Responsibility Principle.

**Current:** 1 file, 1,330 lines  
**Target:** 5 files, each < 500 lines

---

## 📋 PREREQUISITES

Before starting, verify:

```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph

# 1. Check current status
git status
# Should show: python/pyproject.toml and .gitignore modified

# 2. Verify tests pass
pnpm test
# Should show: 159 tests passing

# 3. Check Python build
cd python && uv sync --all-extras --dev
# Should complete without errors

# 4. Review implementation plan
cat IMPLEMENTATION_PLAN_KIMI.md | grep -A 500 "Task 2: Refactor arc-backend-service"
```

---

## 📂 TASK BREAKDOWN

### Step 1: Create Directory Structure (5 minutes)

```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph

# Create services directory
mkdir -p packages/arc-extension/src/node/services

# Verify
ls -la packages/arc-extension/src/node/
# Should show: services/ directory
```

---

### Step 2: Create workflow-executor.ts (1 hour)

**File:** `packages/arc-extension/src/node/services/workflow-executor.ts`

**Instructions:**
1. Open `IMPLEMENTATION_PLAN_KIMI.md`
2. Find section "Step 1: Create workflow-executor.ts"
3. Copy the complete code (lines ~200-350 in the plan)
4. Create the file with the code
5. Verify syntax: `cd packages/arc-extension && pnpm build`

**What it does:**
- Executes SwarmGraph workflows
- Manages running processes
- Handles command execution with security
- Cancels workflows

**Key methods:**
- `executeWorkflow(prompt, options)`
- `cancelWorkflow(runId)`
- `findExecutable(name)`
- `buildSwarmArgs(prompt, backend)`

---

### Step 3: Create trace-parser.ts (1.5 hours)

**File:** `packages/arc-extension/src/node/services/trace-parser.ts`

**Instructions:**
1. Open `IMPLEMENTATION_PLAN_KIMI.md`
2. Find section "Step 2: Create trace-parser.ts"
3. Copy the complete code (lines ~350-550 in the plan)
4. Create the file with the code
5. Verify syntax: `cd packages/arc-extension && pnpm build`

**What it does:**
- Parses JSONL trace files
- Streams large trace files
- Validates trace events
- Extracts trace metadata

**Key methods:**
- `parseTrace(tracePath, options)`
- `parseJsonl(content, options)`
- `streamTrace(tracePath)` - async generator
- `isValidEvent(event)`

---

### Step 4: Create workflow-detector.ts (1 hour)

**File:** `packages/arc-extension/src/node/services/workflow-detector.ts`

**Instructions:**
1. Open `IMPLEMENTATION_PLAN_KIMI.md`
2. Find section "Step 3: Create workflow-detector.ts"
3. Copy the complete code (lines ~550-700 in the plan)
4. Create the file with the code
5. Verify syntax: `cd packages/arc-extension && pnpm build`

**What it does:**
- Detects SwarmGraph CLI
- Finds LangGraph workflows
- Scans workspace for workflows
- Returns workflow metadata

**Key methods:**
- `detectWorkflows(workspaceRoot)`
- `detectSwarmGraphCli()`
- `detectLangGraphWorkflows(workspaceRoot)`
- `findPythonFiles(dir)`

---

### Step 5: Create file-manager.ts (45 minutes)

**File:** `packages/arc-extension/src/node/services/file-manager.ts`

**Instructions:**
1. Open `IMPLEMENTATION_PLAN_KIMI.md`
2. Find section "Step 4: Create file-manager.ts"
3. Copy the complete code (lines ~700-850 in the plan)
4. Create the file with the code
5. Verify syntax: `cd packages/arc-extension && pnpm build`

**What it does:**
- Manages trace files
- Validates file paths
- Ensures directories exist
- Deletes traces

**Key methods:**
- `getTraceFiles(workspaceRoot)`
- `getTracePath(workspaceRoot, traceId)`
- `ensureTracesDir(workspaceRoot)`
- `deleteTrace(workspaceRoot, traceId)`

---

### Step 6: Refactor arc-backend-service.ts (2 hours)

**File:** `packages/arc-extension/src/node/arc-backend-service.ts`

**Instructions:**
1. Open `IMPLEMENTATION_PLAN_KIMI.md`
2. Find section "Step 5: Refactor arc-backend-service.ts (Orchestration)"
3. Copy the complete code (lines ~850-950 in the plan)
4. **BACKUP CURRENT FILE FIRST:**
   ```bash
   cp packages/arc-extension/src/node/arc-backend-service.ts \
      packages/arc-extension/src/node/arc-backend-service.ts.original
   ```
5. Replace the file content with the orchestration code
6. Verify syntax: `cd packages/arc-extension && pnpm build`

**What it does:**
- Orchestrates all services
- Implements ArcService interface
- Delegates to specialized services
- Minimal business logic (just coordination)

**Key changes:**
- Inject 4 service dependencies
- Delegate all operations to services
- Keep only orchestration logic
- Target: ~200 lines

---

### Step 7: Update Dependency Injection (30 minutes)

**File:** `packages/arc-extension/src/node/arc-extension-backend-module.ts`

**Instructions:**
1. Open `IMPLEMENTATION_PLAN_KIMI.md`
2. Find section "Step 6: Update Dependency Injection"
3. Copy the complete code (lines ~950-1000 in the plan)
4. Replace the file content
5. Verify syntax: `cd packages/arc-extension && pnpm build`

**What it does:**
- Binds all services to DI container
- Configures singleton scope
- Sets up RPC connection handler

**Key changes:**
- Bind WorkflowExecutor
- Bind TraceParser
- Bind WorkflowDetector
- Bind FileManager
- Bind ArcBackendService with dependencies

---

### Step 8: Verify and Test (1 hour)

**Run all verification steps:**

```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph

# 1. Build TypeScript
cd packages/arc-extension
pnpm build
# Should complete without errors

# 2. Run tests
pnpm test
# Should show: 159 tests passing (same as before)

# 3. Check file sizes
wc -l src/node/arc-backend-service.ts
# Should be ~200 lines (down from 1,330)

wc -l src/node/services/*.ts
# Each should be < 500 lines

# 4. Build entire project
cd ../..
pnpm build
# Should complete without errors

# 5. Start application (manual test)
pnpm start:browser
# Should start on http://localhost:3000
# Open ARC widget and test workflow execution
```

---

## ✅ SUCCESS CRITERIA

### File Structure
```
packages/arc-extension/src/node/
├── arc-backend-service.ts (~200 lines) ✓
├── arc-extension-backend-module.ts (updated) ✓
├── security-utils.ts (unchanged)
└── services/
    ├── workflow-executor.ts (~300 lines) ✓
    ├── trace-parser.ts (~400 lines) ✓
    ├── workflow-detector.ts (~300 lines) ✓
    └── file-manager.ts (~200 lines) ✓
```

### Tests
- ✅ All 159 tests passing
- ✅ No new test failures
- ✅ Build completes without errors

### Application
- ✅ Application starts without errors
- ✅ Workflow execution works
- ✅ Trace viewing works
- ✅ Workspace scanning works

---

## 🔍 VERIFICATION CHECKLIST

After completing all steps:

- [ ] 5 new service files created
- [ ] arc-backend-service.ts reduced to ~200 lines
- [ ] Dependency injection updated
- [ ] TypeScript builds without errors
- [ ] All 159 tests passing
- [ ] No console errors in build
- [ ] Application starts successfully
- [ ] Workflow execution works (manual test)
- [ ] Trace viewing works (manual test)
- [ ] Git status shows only intended changes

---

## 🚨 TROUBLESHOOTING

### Issue: TypeScript compilation errors

**Solution:**
```bash
# Clean and rebuild
cd packages/arc-extension
rm -rf lib
pnpm build

# Check for import errors
# Make sure all imports use correct paths
```

### Issue: Tests fail after refactoring

**Solution:**
```bash
# Check which tests fail
pnpm test --verbose

# Common issues:
# 1. Missing imports in test files
# 2. Mock setup needs updating
# 3. Service not properly injected

# Restore original if needed:
cp arc-backend-service.ts.original arc-backend-service.ts
```

### Issue: Dependency injection errors

**Solution:**
```bash
# Verify all services are bound in backend module
# Check that @injectable() decorator is present
# Ensure @inject() parameters match bound services
```

### Issue: Application won't start

**Solution:**
```bash
# Check for runtime errors
pnpm start:browser 2>&1 | grep -i error

# Verify all services are properly exported
# Check that RPC connection handler is configured
```

---

## 📊 PROGRESS TRACKING

**Before:**
- arc-backend-service.ts: 1,330 lines
- Monolithic architecture
- Hard to test and maintain

**After:**
- arc-backend-service.ts: ~200 lines
- 4 service modules: ~1,200 lines total
- Clean separation of concerns
- Easy to test and maintain

**Reduction:** 1 file → 5 files (better maintainability)

---

## 🎯 NEXT STEPS AFTER COMPLETION

Once P0-3 is complete:

1. **Commit changes:**
   ```bash
   git add packages/arc-extension/src/node/
   git commit -m "refactor(backend): split arc-backend-service into 5 modules

   - Create WorkflowExecutor service (300 lines)
   - Create TraceParser service (400 lines)
   - Create WorkflowDetector service (300 lines)
   - Create FileManager service (200 lines)
   - Refactor ArcBackendService to orchestration only (200 lines)
   - Update dependency injection configuration
   
   Reduces main service from 1,330 to 200 lines.
   All 159 tests passing."
   ```

2. **Move to P0-4:**
   - Read `IMPLEMENTATION_PLAN_KIMI.md` section for P0-4
   - Refactor arc-widget.tsx (974 lines → 6 components)
   - Estimated time: 3-4 days

3. **Update status:**
   - Update `IMPLEMENTATION_STATUS.md`
   - Mark P0-3 as complete
   - Document any issues encountered

---

## 📚 REFERENCE DOCUMENTS

**Primary Reference:**
- `IMPLEMENTATION_PLAN_KIMI.md` - Complete code examples (lines 200-1000)

**Supporting Documents:**
- `CRITICAL_REVIEW_GENSPARK.md` - Why this refactoring is needed
- `IMPLEMENTATION_COMPLETE.md` - What's been done so far
- `README_HANDOVER.md` - Quick start guide

**Code Location:**
- All code examples are in `IMPLEMENTATION_PLAN_KIMI.md`
- Search for "Step 1: Create workflow-executor.ts"
- Copy-paste ready, no modifications needed

---

## ⏱️ TIME ESTIMATE

**Total Time:** 3-4 days (or 8-10 hours focused work)

**Breakdown:**
- Step 1: Directory structure (5 min)
- Step 2: workflow-executor.ts (1 hour)
- Step 3: trace-parser.ts (1.5 hours)
- Step 4: workflow-detector.ts (1 hour)
- Step 5: file-manager.ts (45 min)
- Step 6: Refactor main service (2 hours)
- Step 7: Update DI (30 min)
- Step 8: Verify and test (1 hour)
- Buffer for issues (1-2 hours)

**Total:** ~8-10 hours

---

## 🚀 READY TO EXECUTE

**Status:** ✅ Ready to start  
**Prerequisites:** ✅ Complete  
**Documentation:** ✅ Available  
**Code Examples:** ✅ Ready

**Command to start:**
```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph
cat IMPLEMENTATION_PLAN_KIMI.md | grep -A 500 "Task 2: Refactor arc-backend-service"
mkdir -p packages/arc-extension/src/node/services
```

---

## 💡 TIPS FOR SUCCESS

1. **Work incrementally** - Create one service at a time
2. **Build after each file** - Catch errors early
3. **Use the code examples** - They're complete and tested
4. **Don't modify the examples** - Copy-paste as-is first
5. **Test frequently** - Run `pnpm test` after each service
6. **Keep original file** - Backup before refactoring main service
7. **Verify manually** - Start the app and test workflow execution

---

**EXECUTE THIS PROMPT TO START P0-3 BACKEND REFACTORING**

Copy this entire prompt and provide it to Kimi 2.6 or the development team to execute the next phase of implementation.

**Estimated completion:** 3-4 days  
**All code ready in:** IMPLEMENTATION_PLAN_KIMI.md  
**Current status:** Quick wins complete, ready for major refactoring

Good luck! 🚀

