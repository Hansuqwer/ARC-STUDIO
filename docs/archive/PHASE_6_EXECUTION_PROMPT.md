# Phase 6 - Alpha Acceptance Execution Prompt

**Date:** 2026-05-13  
**Phase:** 6 - Alpha Acceptance  
**Status:** Ready to Begin  
**Prerequisite:** Phase 4 ✅, Phase 5 ✅, P0+P1 fixes ✅  
**Branch:** `build/no-mockups-handoff`  
**Current Score:** 6.5/10 (Security: 7.0)

---

## Research Findings (Context7 + Theia Docs)

### Production Build Optimization

From Theia migration guide:
- Webpack 5 requires `^5.36.2 <5.47.0` for production builds
- Source maps: Use `webRoot` instead of `sourceMapPathOverrides`
- For production: configure `devtool: 'hidden-source-map'` or `false` to exclude 70 MB of source maps
- Use `yarn resolutions` (or `pnpm overrides`) for webpack version pinning

### Testing Framework

Theia provides:
- `TestRun` interface for reporting test state
- `TestRunProfile` for defining test execution profiles
- `TestItem` for individual test cases
- Run tests: `npx lerna run test --scope @theia/extension-name`
- Watch mode: add `"test:watch"` script to package.json

### Alpha Release Criteria

Standard alpha readiness:
- Test coverage ≥80% for critical paths
- Zero critical/high severity bugs
- Production build succeeds
- Performance benchmarks documented
- User documentation complete
- Security audit verified

---

## Current State

### What's Done ✅
- Phase 4: Protocol, backend, widget, security, UX, docs (7 agents)
- Phase 5: Webpack build fix, 75 integration tests, E2E, performance (4 agents)
- P0 fixes: Security-utils wired, enums unified, routes.py backend flags
- P1 fixes: Env allow-list, gated launcher, skiplist, unique opIds
- Typo fix: `_ALLOW_ENV` → `_ALLOWED_ENV` + smoke test

### What's Blocking Alpha ⚠️
1. **Test coverage: 45-52%** (target: ≥80%)
2. **Production build: not configured** (devtool includes 70 MB source maps)
3. **Bug bash: not done** (known issues not triaged)
4. **User acceptance: not tested** (no external validation)
5. **Documentation review: partial** (API docs incomplete)

### Known Issues (from Phase 5)
- `@theia/file-search` missing (ripgrep Node.js v25 compatibility)
- Keyboard shortcuts need global registration (Theia KeybindingContribution)
- No automated E2E tests (Playwright not set up)
- Toast timeout cleanup (minor)
- Monaco bundle size (29 MB, ~50% of total)

---

## Phase 6 Tasks

### Task 1: Test Coverage Boost 🔴 CRITICAL

**Priority:** CRITICAL  
**Target:** ≥80% backend, ≥70% overall  
**Estimated Time:** 4-5 hours

#### Current Coverage
```
arc-protocol.ts:          100%
arc-backend-service.ts:   52.89%
security-utils.ts:        0% (not tested!)
Overall:                  45.51%
```

#### Coverage Gaps to Fill

**1. security-utils.ts (0% → 100%)**

Create `packages/arc-extension/src/node/__tests__/security-utils.test.ts`:

```typescript
import {
    sanitizePrompt,
    validateTraceId,
    validateFilePath,
    validateBackend,
    sanitizeErrorMessage,
    validateWorkspaceRoot,
} from '../security-utils';

describe('security-utils', () => {
    describe('sanitizePrompt', () => {
        it('should reject empty prompt', () => {
            expect(() => sanitizePrompt('')).toThrow('Invalid prompt');
            expect(() => sanitizePrompt(null as any)).toThrow('Invalid prompt');
            expect(() => sanitizePrompt(undefined as any)).toThrow('Invalid prompt');
        });

        it('should reject non-string prompt', () => {
            expect(() => sanitizePrompt(123 as any)).toThrow('Invalid prompt');
        });

        it('should reject prompts exceeding max length', () => {
            const longPrompt = 'a'.repeat(10001);
            expect(() => sanitizePrompt(longPrompt)).toThrow('exceeds maximum length');
        });

        it('should remove control characters', () => {
            const result = sanitizePrompt('hello\x00world');
            expect(result).toBe('helloworld');
        });

        it('should reject shell metacharacters', () => {
            expect(() => sanitizePrompt('test; rm -rf /')).toThrow('dangerous characters');
            expect(() => sanitizePrompt('test | cat /etc/passwd')).toThrow('dangerous characters');
            expect(() => sanitizePrompt('test $(whoami)')).toThrow('dangerous characters');
            expect(() => sanitizePrompt('test `id`')).toThrow('dangerous characters');
        });

        it('should allow safe prompts', () => {
            expect(sanitizePrompt('hello world')).toBe('hello world');
            expect(sanitizePrompt('  hello  ')).toBe('hello');
            expect(sanitizePrompt('analyze this code')).toBe('analyze this code');
        });

        it('should trim whitespace', () => {
            expect(sanitizePrompt('  hello  ')).toBe('hello');
        });
    });

    describe('validateTraceId', () => {
        it('should reject empty trace ID', () => {
            expect(() => validateTraceId('')).toThrow('Invalid trace ID');
            expect(() => validateTraceId(null as any)).toThrow('Invalid trace ID');
        });

        it('should accept valid SwarmGraph trace IDs', () => {
            expect(validateTraceId('run-sg-abc123')).toBe('run-sg-abc123');
            expect(validateTraceId('run-sg-00ff00')).toBe('run-sg-00ff00');
        });

        it('should accept valid LangGraph trace IDs', () => {
            expect(validateTraceId('run-lg-abc123')).toBe('run-lg-abc123');
        });

        it('should accept valid Claude trace IDs', () => {
            expect(validateTraceId('run-ca-abc123')).toBe('run-ca-abc123');
        });

        it('should accept valid OpenAI trace IDs', () => {
            expect(validateTraceId('run-openai-abc123')).toBe('run-openai-abc123');
        });

        it('should reject invalid trace ID formats', () => {
            expect(() => validateTraceId('invalid')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-unknown-abc')).toThrow('Invalid trace ID format');
            expect(() => validateTraceId('run-sg-GHIJKL')).toThrow('Invalid trace ID format');
        });

        it('should reject path traversal attempts', () => {
            expect(() => validateTraceId('run-sg-abc/../etc')).toThrow('invalid path characters');
            expect(() => validateTraceId('run-sg-abc/def')).toThrow('invalid path characters');
            expect(() => validateTraceId('run-sg-abc\\def')).toThrow('invalid path characters');
        });
    });

    describe('validateFilePath', () => {
        const workspaceRoot = '/tmp/workspace';

        it('should reject empty file path', () => {
            expect(() => validateFilePath('', workspaceRoot)).toThrow('Invalid file path');
        });

        it('should resolve relative paths within workspace', () => {
            const result = validateFilePath('file.txt', workspaceRoot);
            expect(result).toBe('/tmp/workspace/file.txt');
        });

        it('should reject paths outside workspace', () => {
            expect(() => validateFilePath('../etc/passwd', workspaceRoot))
                .toThrow('outside workspace boundaries');
        });

        it('should reject null bytes', () => {
            expect(() => validateFilePath('file\x00.txt', workspaceRoot))
                .toThrow('null bytes');
        });
    });

    describe('validateBackend', () => {
        it('should accept valid backends', () => {
            expect(validateBackend('stub')).toBe('stub');
            expect(validateBackend('local')).toBe('local');
            expect(validateBackend('gateway')).toBe('gateway');
        });

        it('should normalize to lowercase', () => {
            expect(validateBackend('STUB')).toBe('stub');
            expect(validateBackend('Gateway')).toBe('gateway');
        });

        it('should reject invalid backends', () => {
            expect(() => validateBackend('remote')).toThrow('Invalid backend');
            expect(() => validateBackend('invalid')).toThrow('Invalid backend');
            expect(() => validateBackend('')).toThrow('Invalid backend');
        });
    });

    describe('sanitizeErrorMessage', () => {
        it('should map ENOENT to Resource not found', () => {
            const error = new Error('ENOENT: no such file');
            expect(sanitizeErrorMessage(error)).toBe('Resource not found');
        });

        it('should map EACCES to Permission denied', () => {
            const error = new Error('EACCES: permission denied');
            expect(sanitizeErrorMessage(error)).toBe('Permission denied');
        });

        it('should map timeout errors', () => {
            const error = new Error('Operation timed out');
            expect(sanitizeErrorMessage(error)).toBe('Operation timed out');
        });

        it('should map spawn errors', () => {
            const error = new Error('spawn swarmgraph ENOENT');
            expect(sanitizeErrorMessage(error)).toBe('Failed to execute command');
        });

        it('should expose validation error messages', () => {
            const error = new Error('Invalid trace ID format');
            expect(sanitizeErrorMessage(error)).toBe('Invalid trace ID format');
        });

        it('should return generic message for unknown errors', () => {
            const error = new Error('Something weird happened');
            expect(sanitizeErrorMessage(error)).toBe('An error occurred while processing your request');
        });
    });

    describe('validateWorkspaceRoot', () => {
        it('should reject empty workspace root', () => {
            expect(() => validateWorkspaceRoot('')).toThrow('Invalid workspace root');
        });

        it('should resolve absolute paths', () => {
            const result = validateWorkspaceRoot('/tmp/workspace');
            expect(result).toBe('/tmp/workspace');
        });
    });
});
```

**2. arc-backend-service.ts (52.89% → 80%)**

Add tests for uncovered methods:

```typescript
// In arc-service.integration.test.ts, add:

describe('parseJsonlTrace', () => {
    it('should parse single-line JSON', async () => {
        // Create a temp trace file with single JSON object
        // Call getTraces() and verify parsing
    });

    it('should parse multi-line JSONL', async () => {
        // Create a temp trace file with JSONL format
        // Verify event extraction
    });

    it('should handle malformed lines gracefully', async () => {
        // Create a trace file with some invalid JSON lines
        // Verify malformed lines are skipped
    });

    it('should normalize snake_case to camelCase', async () => {
        // Create trace with workflow_id, started_at
        // Verify normalized to workflowId, startedAt
    });
});

describe('detectWorkflows', () => {
    it('should detect SwarmGraph in PATH', async () => {
        // Mock which to return a path
        // Verify SwarmGraph workflow detected
    });

    it('should detect LangGraph Python files', async () => {
        // Create temp Python file with StateGraph import
        // Verify LangGraph workflow detected
    });

    it('should skip ignored directories', async () => {
        // Verify node_modules, .git, __pycache__ etc. are skipped
    });
});

describe('cancelWorkflow', () => {
    it('should cancel running process', async () => {
        // Start a long-running command
        // Cancel it
        // Verify process killed
    });
});

describe('validateTrace', () => {
    it('should validate trace file format', async () => {
        // Create valid trace file
        // Verify validation passes
    });

    it('should report missing required fields', async () => {
        // Create trace with missing id/status/events
        // Verify validation errors reported
    });
});
```

**3. arc-widget.tsx (0% → 60%)**

Add component tests:

```typescript
// In arc-widget.integration.test.ts, add:

describe('Widget state management', () => {
    it('should update state correctly', () => {
        // Test updateState() method
    });

    it('should handle execution flow', () => {
        // Mock arcService.executeWorkflow
        // Trigger handleExecuteWorkflow
        // Verify state transitions: idle → running → completed
    });

    it('should handle execution errors', () => {
        // Mock arcService.executeWorkflow to throw
        // Verify error state set correctly
    });

    it('should filter traces', () => {
        // Set traces and filter
        // Verify filtered results
    });

    it('should handle retry', () => {
        // Set error state
        // Call handleRetry
        // Verify error cleared
    });
});
```

**4. Python routes (add to test_routes_execute.py)**

```python
def test_execute_with_invalid_backend():
    """Verify backend validation works."""
    response = client.post("/api/execute", json={
        "prompt": "test",
        "backend": "invalid_backend",
        "cost_allowed": True
    })
    assert response.status_code == 400
    assert "Invalid backend" in response.json()["detail"]

def test_execute_with_empty_prompt():
    """Verify prompt validation works."""
    response = client.post("/api/execute", json={
        "prompt": "",
        "backend": "stub",
        "cost_allowed": True
    })
    assert response.status_code == 400

def test_execute_with_dangerous_prompt():
    """Verify command injection prevention."""
    response = client.post("/api/execute", json={
        "prompt": "test; rm -rf /",
        "backend": "stub",
        "cost_allowed": True
    })
    assert response.status_code == 400
    assert "dangerous characters" in response.json()["detail"]

def test_get_traces_empty():
    """Verify traces endpoint returns empty array when no traces."""
    response = client.get("/api/traces")
    assert response.status_code == 200
    assert response.json() == []

def test_get_trace_invalid_id():
    """Verify trace ID validation."""
    response = client.get("/api/traces/invalid-id")
    assert response.status_code == 400
```

**5. Run coverage report**

```bash
cd packages/arc-extension
pnpm test -- --coverage --coverageReporters=text --coverageReporters=lcov

# Save coverage report
cp coverage/lcov.info ../../coverage-arc-extension.lcov
cp coverage/coverage-final.json ../../coverage-arc-extension.json
```

#### Acceptance Criteria
- [ ] security-utils.ts: 100% coverage
- [ ] arc-backend-service.ts: ≥80% coverage
- [ ] arc-widget.tsx: ≥60% coverage
- [ ] Python routes: ≥80% coverage
- [ ] Overall: ≥70% coverage
- [ ] Coverage reports committed to `reports/` directory

---

### Task 2: Production Build Optimization 🟡 HIGH

**Priority:** HIGH  
**Target:** <10 MB gzip bundle, no source maps in production  
**Estimated Time:** 2-3 hours

#### Current Bundle
```
Total frontend: ~57 MB uncompressed / ~6 MB gzip
Source maps: ~70 MB (included in production!)
Main bundle.js: 29 MB (Monaco ~50%)
ARC Extension: 81 KB (well optimized)
```

#### Steps

**Step 1: Configure production source maps**

Edit `packages/arc-browser-app/webpack.config.js`:

```javascript
const configs = require('./gen-webpack.config.js');
const nodeConfig = require('./gen-webpack.node.config.js');

// Production: exclude source maps to save ~70 MB
const isProduction = process.env.NODE_ENV === 'production';

for (const config of configs) {
    if (isProduction) {
        // Option A: No source maps (smallest bundle)
        config.devtool = false;
        
        // Option B: Hidden source maps (for error tracking, not shipped to users)
        // config.devtool = 'hidden-source-map';
    }
    
    // ... existing monaco alias fix ...
}

module.exports = [
    ...configs,
    nodeConfig.config
];
```

**Step 2: Add production build script**

Edit `packages/arc-browser-app/package.json`:

```json
{
  "scripts": {
    "build": "theia build --mode development",
    "build:prod": "NODE_ENV=production theia build --mode production",
    "start": "theia start --hostname=0.0.0.0 --port=3000",
    "start:prod": "NODE_ENV=production theia start --hostname=0.0.0.0 --port=3000"
  }
}
```

**Step 3: Verify production build**

```bash
cd packages/arc-browser-app
NODE_ENV=production pnpm build:prod

# Check bundle size
du -sh lib/frontend/
ls -lh lib/frontend/*.js | head -10

# Should be significantly smaller without source maps
```

**Step 4: Add bundle analysis**

```bash
# Install bundle analyzer
pnpm add -D webpack-bundle-analyzer

# Generate stats
pnpm theia build --mode production --stats

# Analyze
npx webpack-bundle-analyzer lib/frontend/stats.json
```

**Step 5: Document production deployment**

Create `docs/DEPLOYMENT.md`:

```markdown
# Production Deployment Guide

## Build
```bash
NODE_ENV=production pnpm build:prod
```

## Expected bundle sizes
- Frontend: ~6 MB gzip (without source maps)
- Backend: ~2 MB

## Environment variables
- ARC_SWARMGRAPH_CLI: Path to SwarmGraph executable
- ARC_TRUST_WORKSPACE_LAUNCHER: Set to '1' to allow workspace-local executables
- ARC_SWARMGRAPH_GATEWAY_URL: Gateway URL for remote backend
- ARC_SWARMGRAPH_GATEWAY_TOKEN: Auth token for gateway

## Security checklist
- [ ] Set ARC_SWARMGRAPH_GATEWAY_TOKEN
- [ ] Configure HTTPS
- [ ] Set up authentication
- [ ] Enable rate limiting
- [ ] Review env allow-list
```

#### Acceptance Criteria
- [ ] Production build excludes source maps
- [ ] Bundle size <10 MB gzip
- [ ] Production build script works
- [ ] Deployment guide created
- [ ] Bundle analysis documented

---

### Task 3: Bug Bash Session 🟡 HIGH

**Priority:** HIGH  
**Target:** Triage and fix all known issues  
**Estimated Time:** 3-4 hours

#### Known Issues to Triage

| Issue | Severity | Status | Action |
|-------|----------|--------|--------|
| @theia/file-search missing | MEDIUM | Known | Accept or fix |
| Keyboard shortcuts not global | MEDIUM | Known | Fix via KeybindingContribution |
| No automated E2E tests | LOW | Known | Document as future work |
| Toast timeout cleanup | LOW | Known | Quick fix |
| Monaco bundle size | LOW | Known | Document optimization |
| Collapsed section badges | LOW | Known | Quick fix |
| Trace filter UX | LOW | Known | Quick fix |

#### Bug Bash Process

**1. Reproduce all known issues**
- Start application: `pnpm start:browser`
- Test each known issue
- Document reproduction steps
- Assign severity (critical/high/medium/low)

**2. Fix quick wins (≤30 min each)**
- Toast timeout cleanup
- Collapsed section badges
- Trace filter improvements
- Any other simple fixes found

**3. Fix keyboard shortcuts (1-2 hours)**

Create `packages/arc-extension/src/browser/arc-keybinding-contribution.ts`:

```typescript
import { injectable } from '@theia/core/shared/inversify';
import { KeybindingContribution, KeybindingRegistry } from '@theia/core/lib/browser';
import { ArcWidgetContribution } from './arc-widget-contribution';

@injectable()
export class ArcKeybindingContribution implements KeybindingContribution {
    constructor(
        @inject(ArcWidgetContribution)
        protected readonly arcContribution: ArcWidgetContribution
    ) {}

    registerKeybindings(registry: KeybindingRegistry): void {
        registry.registerKeybinding({
            command: 'arc.execute',
            keybinding: 'ctrlcmd+e',
        });
        registry.registerKeybinding({
            command: 'arc.loadTraces',
            keybinding: 'ctrlcmd+l',
        });
        registry.registerKeybinding({
            command: 'arc.scanWorkspace',
            keybinding: 'ctrlcmd+s',
        });
        registry.registerKeybinding({
            command: 'arc.showShortcuts',
            keybinding: 'ctrlcmd+h',
        });
    }
}
```

Register commands in `arc-widget-contribution.ts`:

```typescript
import { CommandContribution, CommandRegistry, Command } from '@theia/core/lib/common';

export namespace ArcCommands {
    export const EXECUTE: Command = { id: 'arc.execute', label: 'ARC: Execute Workflow' };
    export const LOAD_TRACES: Command = { id: 'arc.loadTraces', label: 'ARC: Load Traces' };
    export const SCAN_WORKSPACE: Command = { id: 'arc.scanWorkspace', label: 'ARC: Scan Workspace' };
    export const SHOW_SHORTCUTS: Command = { id: 'arc.showShortcuts', label: 'ARC: Show Shortcuts' };
}

@injectable()
export class ArcWidgetContribution implements CommandContribution {
    registerCommands(registry: CommandRegistry): void {
        registry.registerCommand(ArcCommands.EXECUTE, {
            execute: () => this.openView({ activate: true }).then(widget => widget?.handleExecute()),
        });
        // ... similar for other commands
    }
}
```

**4. Create bug report for remaining issues**

Create `docs/BUG_BASH_REPORT.md`:

```markdown
# Bug Bash Report

**Date:** 2026-05-13
**Phase:** 6 - Alpha Acceptance

## Issues Fixed
- [List each fix with commit hash]

## Issues Accepted
- [List each accepted issue with justification]

## Issues Deferred
- [List each deferred issue with target phase]

## Summary
- Total issues found: X
- Critical: X (all fixed)
- High: X (X fixed, X accepted)
- Medium: X (X fixed, X deferred)
- Low: X (X fixed, X deferred)
```

#### Acceptance Criteria
- [ ] All known issues triaged
- [ ] Quick wins fixed
- [ ] Keyboard shortcuts registered globally
- [ ] Bug bash report created
- [ ] No critical/high severity bugs remaining

---

### Task 4: User Acceptance Testing 🟢 MEDIUM

**Priority:** MEDIUM  
**Target:** Validate core workflows from user perspective  
**Estimated Time:** 2-3 hours

#### UAT Test Plan

**Test 1: First-time setup**
```bash
# Fresh clone
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
git checkout build/no-mockups-handoff

# Install and build
pnpm install
pnpm build

# Start
pnpm start:browser

# Verify:
# - Application loads at http://localhost:3000
# - No console errors
# - ARC widget visible in sidebar
```

**Test 2: Workflow execution**
```
1. Open ARC widget
2. Enter prompt: "hello world"
3. Click "Execute Workflow"
4. Verify:
   - Progress indicator appears
   - Execution completes (or fails gracefully)
   - Result shows run ID and trace path
   - Toast notification appears
   - Trace file created in .arc/traces/
```

**Test 3: Trace viewing**
```
1. Click "Load Traces"
2. Verify:
   - Traces appear in list
   - Each trace shows ID, timestamp, status
   - Clicking a trace selects it
   - Selection highlighting works
```

**Test 4: Workspace scanning**
```
1. Click "Scan Workspace"
2. Verify:
   - Scanning progress shown
   - Detected workflows listed
   - SwarmGraph CLI detected (if installed)
```

**Test 5: Error handling**
```
1. Try to execute with empty prompt
2. Verify:
   - Warning message appears
   - No execution attempted
   - Error can be dismissed
```

**Test 6: Keyboard shortcuts**
```
1. Press Ctrl+E (or Cmd+E on Mac)
2. Verify: Workflow execution triggered
3. Press Ctrl+L
4. Verify: Traces loaded
5. Press Ctrl+S
6. Verify: Workspace scanned
7. Press Ctrl+H
8. Verify: Shortcuts modal shown
```

**Test 7: Accessibility**
```
1. Tab through all interactive elements
2. Verify:
   - Focus indicators visible
   - All elements keyboard-accessible
   - ARIA labels present
   - Screen reader announces status changes
```

**Test 8: Performance**
```
1. Open DevTools > Performance
2. Record widget load
3. Verify:
   - Widget loads <500ms
   - No long tasks (>100ms)
   - Smooth animations
```

#### UAT Report

Create `docs/UAT_REPORT.md`:

```markdown
# User Acceptance Test Report

**Date:** 2026-05-13
**Phase:** 6 - Alpha Acceptance

## Test Results

| Test | Result | Notes |
|------|--------|-------|
| First-time setup | PASS/FAIL | [details] |
| Workflow execution | PASS/FAIL | [details] |
| Trace viewing | PASS/FAIL | [details] |
| Workspace scanning | PASS/FAIL | [details] |
| Error handling | PASS/FAIL | [details] |
| Keyboard shortcuts | PASS/FAIL | [details] |
| Accessibility | PASS/FAIL | [details] |
| Performance | PASS/FAIL | [details] |

## Issues Found
- [List any issues with severity]

## Overall Assessment
- [PASS/FAIL with justification]

## Recommendation
- [Ready for alpha / Needs fixes / Not ready]
```

#### Acceptance Criteria
- [ ] All 8 UAT tests executed
- [ ] ≥6 tests pass
- [ ] No critical issues found
- [ ] UAT report created
- [ ] Recommendation documented

---

### Task 5: Documentation Review 🟢 MEDIUM

**Priority:** MEDIUM  
**Target:** Complete and accurate documentation  
**Estimated Time:** 2-3 hours

#### Documentation Checklist

**1. README.md**
- [x] Phase table updated (Phase 4 & 5 Complete)
- [ ] Installation instructions verified (fresh clone test)
- [ ] Usage examples accurate
- [ ] Known limitations current
- [ ] Links working

**2. API Documentation**
- [ ] `docs/API.md` complete with all endpoints
- [ ] All protocol methods documented
- [ ] Request/response examples
- [ ] Error codes documented

**3. Architecture Documentation**
- [ ] `docs/ARCHITECTURE.md` accurate
- [ ] Diagram up to date
- [ ] Component descriptions correct
- [ ] Security architecture documented

**4. Development Guide**
- [ ] `docs/DEVELOPMENT.md` complete
- [ ] Build instructions work
- [ ] Test instructions work
- [ ] Debugging guide included

**5. Security Documentation**
- [ ] `docs/SECURITY.md` accurate
- [ ] Security audit report updated
- [ ] Threat model documented
- [ ] Security checklist included

**6. Deployment Guide**
- [ ] `docs/DEPLOYMENT.md` created (from Task 2)
- [ ] Production build instructions
- [ ] Environment variables documented
- [ ] Security checklist

**7. Code Documentation**
- [ ] All public APIs have JSDoc
- [ ] Complex logic explained
- [ ] Type definitions complete
- [ ] Examples in JSDoc

#### Documentation Gaps to Fill

**Create `docs/API.md`:**

```markdown
# ARC Studio API Documentation

## REST API (Python Backend)

### POST /api/execute
Execute a SwarmGraph workflow.

**Request:**
```json
{
  "prompt": "string",
  "backend": "stub|local|gateway",
  "cost_allowed": true
}
```

**Response:**
```json
{
  "run_id": "run-sg-abc123",
  "status": "completed|failed",
  "output": "...",
  "error": null,
  "trace_path": ".arc/traces/run-sg-abc123.jsonl"
}
```

**Errors:**
- 400: Invalid input (prompt, backend)
- 408: Execution timeout
- 500: Internal error

### GET /api/traces
List all trace files.

**Response:** Array of TraceInfo

### GET /api/traces/{trace_id}
Get a specific trace.

**Response:** TraceData object

## RPC Protocol (TypeScript Backend)

### ArcService Interface

Methods:
- `executeWorkflow(prompt, options?)` → ExecutionResult
- `getTraces()` → TraceFile[]
- `readTrace(traceId)` → TraceData
- `detectWorkflows()` → WorkflowInfo[]
- `streamTrace(traceId)` → AsyncIterable<TraceEvent>
- `validateTrace(traceId)` → ValidationResult
- `cancelWorkflow(runId)` → CancelResult

### Error Types

ArcError codes:
- INVALID_INPUT
- TRACE_NOT_FOUND
- PARSE_ERROR
- EXECUTION_FAILED
- TIMEOUT
- UNKNOWN
```

#### Acceptance Criteria
- [ ] All documentation files reviewed
- [ ] API documentation complete
- [ ] Installation instructions verified
- [ ] Code examples accurate
- [ ] Links working
- [ ] No outdated information

---

## Parallel Agent Strategy

Launch 5 parallel agents for Phase 6:

### Agent 1: Test Coverage
- Write security-utils tests (target: 100%)
- Write backend service tests (target: 80%)
- Write widget tests (target: 60%)
- Write Python route tests (target: 80%)
- Run coverage report
- Commit coverage artifacts

### Agent 2: Production Build
- Configure production source maps
- Add production build scripts
- Verify production build
- Run bundle analysis
- Create deployment guide
- Document optimization results

### Agent 3: Bug Bash
- Reproduce all known issues
- Fix quick wins
- Implement global keyboard shortcuts
- Create bug bash report
- Triage remaining issues

### Agent 4: User Acceptance Testing
- Execute 8 UAT test cases
- Document results
- Report issues found
- Create UAT report
- Make recommendation

### Agent 5: Documentation Review
- Review all documentation files
- Fill documentation gaps
- Create API documentation
- Verify installation instructions
- Update outdated information

---

## Execution Order

### Phase 6.1: Foundation (Day 1)
1. **Test coverage boost** (Agent 1) - BLOCKER for alpha
2. **Production build** (Agent 2) - Required for deployment

### Phase 6.2: Quality (Day 1-2)
3. **Bug bash** (Agent 3) - Fix known issues
4. **Documentation review** (Agent 5) - Ensure accuracy

### Phase 6.3: Validation (Day 2)
5. **User acceptance testing** (Agent 4) - Final validation

---

## Success Criteria

### Alpha Acceptance Gates

**Must Pass:**
- [ ] Test coverage ≥70% overall, ≥80% backend
- [ ] Production build succeeds
- [ ] Zero critical/high severity bugs
- [ ] All UAT tests pass (≥6/8)
- [ ] Documentation complete and accurate

**Should Pass:**
- [ ] Bundle size <10 MB gzip
- [ ] Performance benchmarks met
- [ ] All medium severity bugs triaged
- [ ] Security audit verified

**Nice to Pass:**
- [ ] Test coverage ≥80% overall
- [ ] Automated E2E tests created
- [ ] All low severity bugs fixed
- [ ] CI/CD pipeline configured

---

## Expected Outcomes

### If Alpha Accepted
- Tag release: `v0.6.0-alpha`
- Merge to main branch
- Begin Phase 7 (Final Handover)
- Announce alpha availability

### If Not Ready
- Document blocking issues
- Create fix plan
- Re-run Phase 6 after fixes
- Update timeline

---

## Commands Reference

```bash
# Test coverage
cd packages/arc-extension && pnpm test -- --coverage

# Production build
cd packages/arc-browser-app && NODE_ENV=production pnpm build:prod

# Bundle analysis
npx webpack-bundle-analyzer lib/frontend/stats.json

# Start application
pnpm start:browser

# Python tests
cd python && uv run pytest -v

# Check bundle size
du -sh lib/frontend/
```

---

**Status:** Ready to execute Phase 6  
**Estimated Duration:** 2 days  
**Agents Required:** 5 parallel agents  
**Blocking Issues:** None (Phase 5 complete, P0+P1 fixed)
