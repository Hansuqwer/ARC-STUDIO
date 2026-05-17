# Phase 5 - Integration Fixes Execution Prompt

**Date:** 2026-05-12  
**Phase:** 5 - Integration Fixes  
**Status:** Ready to Begin  
**Prerequisite:** Phase 4 Complete ✅

---

## Research Findings (Context7 + Documentation)

### Critical Discovery: Monaco ESM Migration

According to Theia migration documentation:

> **Monaco 1.65.2 - ASM to ESM Migration**
> The Monaco editor has been updated to align with VSCode 1.65.2. The consumption of Monaco code has shifted from ASM modules loaded onto `window.monaco` to ESM modules built into the Webpack bundle. This change may require updates to custom Webpack configurations and how Monaco is referenced in the application.

**This explains our webpack build error!**

The error `resolvePackagePath('@theia/monaco-editor-core', __dirname)` returns `null` because:
- Monaco is now ESM modules bundled by webpack
- `@theia/monaco-editor-core` is NOT meant to be resolved at runtime via `resolvePackagePath`
- The generated webpack config is using an outdated pattern

**Solution:**
1. Import Monaco from `@theia/monaco-editor-core` directly in code
2. Fix webpack alias to handle ESM module resolution
3. Ensure webpack version is `^5.36.2 <5.47.0` (use pnpm overrides if needed)

### Testing Framework

Theia provides a testing framework with:
- `TestController` - Register test controllers
- `TestRunProfile` - Define test execution profiles
- `TestItem` - Individual test items
- `createTheiaReadyPromise()` - Wait for Theia to be ready

### Performance Measurement

Theia provides:
- `bindFrontendStopwatch()` - Measure frontend performance
- Performance measurement utilities for profiling

---

## Current State

### What Works ✅
- arc-extension package builds successfully (0 TypeScript errors)
- Protocol endpoints implemented with streaming, validation, error handling
- Backend service: 1,341 lines with robust JSONL parsing, workflow detection
- Widget: 884 lines with toast notifications, progress bars, accessibility
- Security: 36 tests passing, 5 vulnerabilities fixed
- CSS: 1,045 lines with complete design system

### What's Broken ❌
- arc-browser-app webpack build fails
- Error: `TypeError [ERR_INVALID_ARG_TYPE]: The "path" argument must be of type string. Received null`
- Location: `gen-webpack.config.js:172` - monaco-editor-core path resolution
- Root cause: Monaco ESM migration not reflected in generated webpack config

### What's Missing ⏳
- Integration tests (frontend ↔ backend)
- E2E workflow execution tests
- Performance benchmarks
- Memory leak detection

---

## Phase 5 Tasks

### Task 1: Fix Browser App Webpack Build 🔴 BLOCKER

**Priority:** CRITICAL  
**Estimated Time:** 2-3 hours

#### Problem
```
TypeError [ERR_INVALID_ARG_TYPE]: The "path" argument must be of type string. Received null
    at gen-webpack.config.js:172
    at Object.join (node:path:1339:7)
```

Line 172:
```javascript
[path.join(resolvePackagePath('@theia/monaco-editor-core', __dirname), '..', 'esm', 'vs', 'nls.js')]:
    path.join(resolvePackagePath('@theia/monaco', __dirname), '..', 'lib', 'browser', 'monaco-nls.js')
```

`resolvePackagePath('@theia/monaco-editor-core', __dirname)` returns `null` because:
- `@theia/monaco-editor-core` is a transitive dependency
- Monaco is now ESM, not meant to be resolved this way
- The webpack alias pattern is outdated

#### Solution Steps

**Step 1: Check Webpack Version**
```bash
cd packages/arc-browser-app
pnpm list webpack
```

Ensure webpack is `^5.36.2 <5.47.0`. If not, add to `package.json`:
```json
{
  "pnpm": {
    "overrides": {
      "webpack": "^5.46.0"
    }
  }
}
```

**Step 2: Fix Monaco Webpack Alias**

The generated `gen-webpack.config.js` has two problematic alias sections (lines ~166-174 and ~263-271).

**Option A: Add monaco-editor-core as direct dependency**
```bash
cd packages/arc-browser-app
pnpm add @theia/monaco-editor-core
```

This makes `resolvePackagePath` work by making it a direct dependency.

**Option B: Modify webpack.config.js to patch the generated config**

Edit `packages/arc-browser-app/webpack.config.js`:
```javascript
const path = require('path');
const configs = require('./gen-webpack.config.js');
const nodeConfig = require('./gen-webpack.node.config.js');

// Fix Monaco ESM alias resolution
for (const config of configs) {
    if (config.resolve && config.resolve.alias) {
        const alias = config.resolve.alias;
        const keysToDelete = [];
        
        for (const key in alias) {
            // Delete aliases with null paths
            if (alias[key] === null || key.includes('null')) {
                keysToDelete.push(key);
            }
        }
        
        keysToDelete.forEach(key => delete alias[key]);
        
        // Add correct Monaco NLS alias if both packages are resolvable
        const resolvePackagePath = require('resolve-package-path');
        const monacoEditorCore = resolvePackagePath('@theia/monaco-editor-core', __dirname);
        const monaco = resolvePackagePath('@theia/monaco', __dirname);
        
        if (monacoEditorCore && monaco) {
            const nlsKey = path.join(monacoEditorCore, '..', 'esm', 'vs', 'nls.js');
            const nlsValue = path.join(monaco, '..', 'lib', 'browser', 'monaco-nls.js');
            alias[nlsKey] = nlsValue;
        }
    }
}

module.exports = [
    ...configs,
    nodeConfig.config
];
```

**Option C: Regenerate webpack config**
```bash
cd packages/arc-browser-app
rm -rf lib src-gen gen-webpack.config.js gen-webpack.node.config.js webpack.config.js
pnpm theia clean
pnpm build
```

This regenerates all configs. If the issue persists, the root cause is in Theia's config generation.

**Step 3: Verify Build**
```bash
cd packages/arc-browser-app
pnpm build
```

Expected: Build completes without errors.

**Step 4: Test Application**
```bash
pnpm start:browser
```

Expected: Application starts on http://localhost:3000

#### Acceptance Criteria
- [ ] `pnpm build` completes with 0 errors
- [ ] `pnpm start:browser` starts successfully
- [ ] Application loads at http://localhost:3000
- [ ] ARC widget is visible and functional
- [ ] No console errors on load

---

### Task 2: Integration Testing 🟡 IMPORTANT

**Priority:** HIGH  
**Estimated Time:** 3-4 hours

#### Goal
Verify frontend ↔ backend communication works correctly.

#### Test Plan

**2.1: RPC Connection Test**

Create `packages/arc-extension/src/node/__tests__/arc-service.integration.test.ts`:

```typescript
import { ArcBackendService } from '../arc-backend-service';
import { ArcError, ArcErrorCode } from '../../common/arc-protocol';

describe('ArcBackendService Integration', () => {
    let service: ArcBackendService;

    beforeEach(() => {
        service = new ArcBackendService();
    });

    describe('executeWorkflow', () => {
        it('should reject empty prompts', async () => {
            await expect(service.executeWorkflow('')).rejects.toThrow(ArcError);
            await expect(service.executeWorkflow('   ')).rejects.toThrow(ArcError);
        });

        it('should reject prompts exceeding max length', async () => {
            const longPrompt = 'a'.repeat(10001);
            await expect(service.executeWorkflow(longPrompt)).rejects.toThrow(ArcError);
        });

        it('should execute valid workflow', async () => {
            // This test requires swarmgraph to be installed
            const result = await service.executeWorkflow('test prompt');
            expect(result).toHaveProperty('runId');
            expect(result).toHaveProperty('status');
            expect(result).toHaveProperty('tracePath');
        });
    });

    describe('getTraces', () => {
        it('should return empty array when no traces exist', async () => {
            const traces = await service.getTraces();
            expect(Array.isArray(traces)).toBe(true);
        });

        it('should return traces sorted by timestamp', async () => {
            const traces = await service.getTraces();
            for (let i = 1; i < traces.length; i++) {
                expect(traces[i - 1].timestamp >= traces[i].timestamp).toBe(true);
            }
        });
    });

    describe('readTrace', () => {
        it('should throw ArcError for non-existent trace', async () => {
            await expect(service.readTrace('non-existent-id')).rejects.toThrow(ArcError);
        });

        it('should return trace data for valid trace ID', async () => {
            // Requires a trace file to exist in .arc/traces/
            // Skip if no traces exist
        });
    });

    describe('detectWorkflows', () => {
        it('should detect SwarmGraph CLI if installed', async () => {
            const workflows = await service.detectWorkflows();
            const swarmgraph = workflows.find(w => w.type === 'swarmgraph');
            // May or may not exist depending on environment
        });
    });

    describe('validateTrace', () => {
        it('should validate trace file format', async () => {
            // Test with existing trace file
        });
    });

    describe('cancelWorkflow', () => {
        it('should return failure for non-running workflow', async () => {
            const result = await service.cancelWorkflow('non-existent-run');
            expect(result.success).toBe(false);
        });
    });
});
```

**2.2: Frontend Service Proxy Test**

Create `packages/arc-extension/src/browser/__tests__/arc-service.proxy.test.ts`:

```typescript
import { Container } from '@theia/core/shared/inversify';
import { WebSocketConnectionProvider } from '@theia/core/lib/browser';
import { ArcServicePath, ArcService } from '../../common/arc-protocol';

describe('ArcService Proxy', () => {
    it('should create proxy with correct path', () => {
        expect(ArcServicePath).toBe('/services/arc');
    });

    it('should have all required methods', () => {
        const methods = [
            'executeWorkflow',
            'getTraces',
            'readTrace',
            'detectWorkflows',
            'streamTrace',
            'validateTrace',
            'cancelWorkflow'
        ];
        
        // Verify interface has all methods
        // (TypeScript compile-time check)
    });
});
```

**2.3: Widget Integration Test**

Create `packages/arc-extension/src/browser/__tests__/arc-widget.integration.test.ts`:

```typescript
import { ArcWidget } from '../arc-widget';

describe('ArcWidget Integration', () => {
    it('should have correct ID and label', () => {
        expect(ArcWidget.ID).toBe('arc-widget');
        expect(ArcWidget.LABEL).toBe('ARC Studio');
    });

    it('should initialize with default state', () => {
        // Test widget state initialization
    });

    it('should render without errors', () => {
        // Test widget rendering
    });
});
```

**2.4: Run Integration Tests**

```bash
cd packages/arc-extension
pnpm test
```

#### Acceptance Criteria
- [ ] Integration test suite created
- [ ] All tests pass (or skip with valid reason)
- [ ] Test coverage > 60% for backend service
- [ ] Frontend ↔ backend RPC verified
- [ ] Error handling tested

---

### Task 3: End-to-End Workflow Testing 🟡 IMPORTANT

**Priority:** HIGH  
**Estimated Time:** 2-3 hours

#### Goal
Verify complete workflow execution from UI to trace output.

#### Test Plan

**3.1: Manual E2E Test**

1. Start the application:
```bash
pnpm start:browser
```

2. Open http://localhost:3000

3. Verify ARC widget appears in sidebar

4. Test workflow execution:
   - Enter a prompt in the input field
   - Click "Execute Workflow"
   - Verify execution progress appears
   - Verify result displays run ID and trace path
   - Check `.arc/traces/` for generated trace file

5. Test trace loading:
   - Click "Load Traces"
   - Verify traces appear in list
   - Verify trace metadata (ID, timestamp, status)
   - Select a trace and verify details

6. Test workspace scanning:
   - Click "Scan Workspace"
   - Verify detected workflows appear
   - Verify SwarmGraph CLI is detected (if installed)

7. Test error handling:
   - Enter empty prompt and try to execute
   - Verify error message appears
   - Verify "Try Again" button works

8. Test keyboard shortcuts:
   - Ctrl+E: Execute workflow
   - Ctrl+L: Load traces
   - Ctrl+S: Scan workspace
   - Ctrl+H: Show shortcuts help

**3.2: Automated E2E Test (Optional)**

Create `tests/e2e/workflow-execution.test.ts`:

```typescript
import { chromium, Browser, Page } from 'playwright';

describe('E2E: Workflow Execution', () => {
    let browser: Browser;
    let page: Page;

    beforeAll(async () => {
        browser = await chromium.launch();
        page = await browser.newPage();
        await page.goto('http://localhost:3000');
        // Wait for Theia to be ready
        await page.waitForSelector('.theia-ApplicationShell');
    });

    afterAll(async () => {
        await browser.close();
    });

    it('should load ARC widget', async () => {
        // Open ARC widget
        await page.click('[aria-label="ARC Studio"]');
        await page.waitForSelector('.arc-widget-container');
    });

    it('should execute workflow', async () => {
        // Enter prompt
        await page.fill('#prompt-input', 'test workflow execution');
        
        // Execute
        await page.click('button:has-text("Execute Workflow")');
        
        // Wait for completion
        await page.waitForSelector('.arc-status-completed', { timeout: 30000 });
        
        // Verify result
        const resultText = await page.textContent('.arc-result');
        expect(resultText).toContain('Run ID:');
    });

    it('should load traces', async () => {
        await page.click('button:has-text("Load Traces")');
        await page.waitForSelector('.arc-trace-list');
        
        const traceCount = await page.locator('.arc-trace-item').count();
        expect(traceCount).toBeGreaterThan(0);
    });
});
```

#### Acceptance Criteria
- [ ] Application starts and loads successfully
- [ ] ARC widget is visible and functional
- [ ] Workflow execution completes end-to-end
- [ ] Trace files are generated and loadable
- [ ] Workspace scanning detects SwarmGraph
- [ ] Error handling works correctly
- [ ] Keyboard shortcuts function properly
- [ ] No console errors during normal usage

---

### Task 4: Performance Optimization 🟢 NICE TO HAVE

**Priority:** MEDIUM  
**Estimated Time:** 2-3 hours

#### Goal
Ensure the application performs well under normal usage.

#### Optimization Areas

**4.1: Webpack Bundle Analysis**

```bash
cd packages/arc-browser-app
pnpm theia build --mode production --stats
```

Analyze bundle:
```bash
npx webpack-bundle-analyzer lib/frontend/stats.json
```

Identify:
- Large dependencies that can be optimized
- Duplicate modules
- Unused code

**4.2: Frontend Performance**

Use Theia's `bindFrontendStopwatch()` to measure:
- Widget load time
- Trace list rendering time
- Workflow execution response time

Add performance markers in `arc-widget.tsx`:

```typescript
private async handleExecuteWorkflow(): Promise<void> {
    const startTime = performance.now();
    
    // ... execution logic ...
    
    const duration = performance.now() - startTime;
    console.log(`Workflow execution UI: ${duration.toFixed(2)}ms`);
}
```

**4.3: Backend Performance**

Measure:
- Trace file parsing time (large files)
- Workflow detection scan time
- JSONL streaming performance

Add benchmarks in `arc-backend-service.ts`:

```typescript
async getTraces(): Promise<TraceFile[]> {
    const startTime = Date.now();
    
    // ... trace loading logic ...
    
    const duration = Date.now() - startTime;
    console.log(`Loaded ${traces.length} traces in ${duration}ms`);
    
    return traces;
}
```

**4.4: Memory Leak Detection**

Test for memory leaks:
1. Open application
2. Execute multiple workflows
3. Load/unload traces repeatedly
4. Monitor memory usage in browser DevTools
5. Check for detached DOM nodes
6. Verify event listeners are cleaned up

**4.5: Lazy Loading**

Implement lazy loading for:
- Large trace files (load events on demand)
- Monaco editor (load only when needed)
- Widget sections (load content when expanded)

#### Acceptance Criteria
- [ ] Bundle size analyzed and optimized
- [ ] Widget load time < 500ms
- [ ] Trace list renders < 100ms for 100 traces
- [ ] No memory leaks detected after 10 workflow executions
- [ ] Large trace files (>1MB) handled efficiently
- [ ] Lazy loading implemented where appropriate

---

## Execution Order

### Phase 5.1: Critical Fixes (Day 1)
1. **Fix webpack build** (Task 1) - BLOCKER
2. **Verify application starts** (Task 1 acceptance criteria)
3. **Manual smoke test** (basic functionality check)

### Phase 5.2: Integration Testing (Day 2)
1. **Create integration test suite** (Task 2)
2. **Run and fix failing tests** (Task 2)
3. **Verify RPC communication** (Task 2.1)

### Phase 5.3: E2E Testing (Day 2-3)
1. **Manual E2E test** (Task 3.1)
2. **Document any issues found** (Task 3)
3. **Fix E2E issues** (Task 3)
4. **Optional: Automated E2E tests** (Task 3.2)

### Phase 5.4: Performance (Day 3)
1. **Bundle analysis** (Task 4.1)
2. **Performance measurement** (Task 4.2, 4.3)
3. **Memory leak check** (Task 4.4)
4. **Optimize as needed** (Task 4.5)

---

## Parallel Agent Strategy

Launch 4 parallel agents for Phase 5:

### Agent 1: Webpack Build Fix
- Fix monaco-editor-core path resolution
- Verify webpack version
- Ensure build completes
- Test application startup

### Agent 2: Integration Tests
- Create integration test suite
- Test RPC communication
- Test error handling
- Verify test coverage

### Agent 3: E2E Testing
- Manual E2E workflow test
- Document issues
- Fix UI/UX problems
- Create automated E2E tests (optional)

### Agent 4: Performance Optimization
- Bundle analysis
- Performance measurement
- Memory leak detection
- Lazy loading implementation

---

## Known Risks

### High Risk
1. **Monaco ESM migration complexity**
   - May require significant webpack config changes
   - Theia's generated config may need manual patching
   - Fallback: Add monaco-editor-core as direct dependency

2. **Integration test infrastructure**
   - Theia testing framework may require setup
   - Mocking WebSocket connections is complex
   - Fallback: Focus on manual testing first

### Medium Risk
1. **E2E test flakiness**
   - Playwright tests may be flaky with Theia
   - Timing issues with widget loading
   - Fallback: Manual testing with detailed documentation

2. **Performance bottlenecks**
   - Large trace files may cause UI lag
   - Workflow detection may be slow on large workspaces
   - Fallback: Implement pagination/virtual scrolling

---

## Success Criteria

Phase 5 is complete when:

### Must Have
- [ ] Browser app builds without errors
- [ ] Application starts and loads successfully
- [ ] ARC widget is functional
- [ ] Workflow execution works end-to-end
- [ ] Trace files are generated and viewable
- [ ] Integration tests pass (>60% coverage)

### Should Have
- [ ] E2E tests created (manual or automated)
- [ ] Performance benchmarks documented
- [ ] Memory leaks identified and fixed
- [ ] Bundle size optimized

### Nice to Have
- [ ] Automated E2E test suite
- [ ] Lazy loading implemented
- [ ] Performance monitoring in place
- [ ] CI/CD pipeline with integration tests

---

## Commands Reference

```bash
# Build
pnpm install                    # Install dependencies
pnpm build                      # Build all packages
cd packages/arc-extension && pnpm build    # Build extension only
cd packages/arc-browser-app && pnpm build  # Build browser app

# Run
pnpm start:browser              # Start browser app (port 3000)

# Test
cd packages/arc-extension && pnpm test     # Run extension tests
cd python && uv run pytest -q              # Run Python tests

# Analyze
cd packages/arc-browser-app
pnpm theia build --mode production --stats # Generate webpack stats
npx webpack-bundle-analyzer lib/frontend/stats.json

# Clean
pnpm clean                      # Clean all build artifacts
cd packages/arc-browser-app && pnpm theia clean  # Clean browser app
```

---

## Documentation References

- **Theia Migration Guide:** https://eclipse-theia.github.io/theia/docs/next/documents/Migration.html
- **Monaco ESM Migration:** Import from `@theia/monaco-editor-core` instead of `window.monaco`
- **Webpack Version:** Use `^5.36.2 <5.47.0`
- **Phase 4 Report:** `docs/PHASE_4_COMPLETE.md`
- **Protocol:** `packages/arc-extension/src/common/arc-protocol.ts`
- **Backend:** `packages/arc-extension/src/node/arc-backend-service.ts`
- **Widget:** `packages/arc-extension/src/browser/arc-widget.tsx`

---

## Next Phase

After Phase 5 completes:
- **Phase 6:** Alpha Acceptance (user testing, bug bash, documentation review)
- **Phase 7:** Final Handover (production deployment, monitoring, training)

---

**Status:** Ready to execute Phase 5  
**Estimated Duration:** 2-3 days  
**Agents Required:** 4 parallel agents  
**Blocking Issues:** Webpack build (Task 1 must be completed first)
