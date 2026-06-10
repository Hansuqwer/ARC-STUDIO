# Arena.ai Agent Prompt — ARC Studio Theia Startup Optimization
## Backend Pre-Warm + Lazy Extension Loading

**Target agent:** Arena.ai autonomous agent (preview)
**Date authored:** 2026-06-10
**Authored by:** OpenCode research → prompt synthesis
**Scope:** Performance-only. No feature changes. No roadmap/phase/status file edits unless
         a new phase must be appended under the NEW INTAKE marker.

---

## 0. Context You Must Read First (Do Not Skip)

You are working on **ARC Studio** — an Eclipse Theia 1.71.0–based agent IDE monorepo.

**Critical governance rules (AGENTS.md):**
- `docs/roadmap.md` and `docs/phases.md` are the ONLY status sources of truth.
  Update them in place — never create new roadmap/status/phase markdown files.
- Do not remove or rename existing events, CLI commands, or public API surfaces.
- No commits unless the owner explicitly requests one. Leave changes in the working tree.
- Do not overclaim. Do not raise status to "Polished Complete" unless every DoD gate
  has cited evidence.
- ARC Studio is a single-user, loopback-only alpha workstation tool. Do not change that.

**Repo layout (relevant paths):**
```
arc-theia-studio/
├── applications/
│   ├── browser/                     ← canonical release target
│   │   ├── package.json             ← Theia 1.71.0 browser app config
│   │   └── src-gen/
│   │       ├── backend/
│   │       │   ├── main.js          ← backend entry — sequential module load
│   │       │   └── server.js        ← 21 sequential await load() calls
│   │       └── frontend/
│   │           └── index.js         ← 25 sequential await load() calls
│   └── electron/
│       ├── package.json             ← Electron 39.8.7 desktop app
│       └── src-gen/
│           ├── backend/
│           │   ├── electron-main.js ← Electron main process
│           │   ├── main.js          ← backend entry
│           │   └── server.js        ← same sequential load pattern
│           └── frontend/
│               └── index.js         ← same sequential load pattern
├── packages/
│   ├── arc-extension/               ← main ARC extension (TS, backend + frontend)
│   └── arc-ag-ui/                   ← agent UI components
├── python/
│   └── src/agent_runtime_cockpit/   ← Python daemon (FastAPI + uvicorn)
└── scripts/
    └── start-browser-arc.mjs        ← dev startup script
```

**Technology stack:**
- Frontend: Theia 1.71.0, React, Monaco editor, Inversify DI, WebSockets (JSON-RPC)
- Backend: Node.js + Express (Theia BackendApplication), 21 extension modules loaded sequentially
- Desktop: Electron 39.8.7 — `electron-main.js` → spawns backend → opens window
- Python: FastAPI + uvicorn daemon (separate process, port 8080 by default)
- Build: pnpm + @theia/cli webpack
- Tests: Jest (TS), pytest (Python)

**Current startup behavior (confirmed by reading src-gen files):**
- `backend/server.js`: 21 `await load()` calls — ALL sequential, blocking
- `frontend/index.js`: 25 `await load()` calls — ALL sequential, blocking
- `electron-main.js`: `showWindowEarly: true` is set but backend is still awaited before
  the window becomes interactive
- No pre-warm mechanism exists anywhere
- No lazy/deferred module loading exists anywhere
- Startup milestone logs exist (`startupLog`) but no measurement/reporting harness

---

## 1. Mission

Design, implement, test, and deliver **measurable startup speed improvements** for the
ARC Studio Theia IDE through two orthogonal techniques:

**Technique A — Backend Pre-Warm:**
Start the Theia Node.js backend process *before* the user requests the window, so that
by the time the Electron window opens (or the browser tab loads), the backend's HTTP/WS
server is already listening. The window's JSON-RPC handshake completes in <100ms instead
of waiting for the full backend boot sequence (~3–8s).

**Technique B — Lazy/Deferred Extension Loading:**
Identify which of the 21 backend modules and 25 frontend modules are NOT needed before
the first interactive frame, and load them asynchronously after the application shell
is visible. Users see a responsive IDE shell faster even if some panels are not yet
initialised.

**Success criteria (must be measurable, not subjective):**
1. A new `scripts/measure-startup.mjs` script that instruments and logs:
   - `T_backend_ready` — time from process spawn to first HTTP response on port 3000
   - `T_window_interactive` — time from Electron `app.ready` to `did-finish-load` event
   - `T_frontend_shell_visible` — time to first `FrontendApplication.start()` resolution
   - Baseline (before) and optimized (after) measurements, both captured
2. Backend pre-warm: `T_backend_ready` measured ≥500ms earlier relative to window open
3. Lazy loading: at least 5 non-critical frontend modules deferred; at least 3 non-critical
   backend modules deferred; measured `T_frontend_shell_visible` reduced by ≥20%
4. All existing tests still pass: `cd python && uv run pytest tests/ -q` (6438+ passing),
   `pnpm typecheck && pnpm build`
5. No regressions in `scripts/check-banned-claims.sh`
6. No changes to public CLI commands, JSON output shapes, or protocol surfaces

---

## 2. Phase 1 — Research (Do This Before Writing Any Code)

### 2.1 Read and understand these files completely

Read every file listed here before making any code decisions:

```
applications/browser/src-gen/backend/main.js
applications/browser/src-gen/backend/server.js
applications/browser/src-gen/frontend/index.js
applications/electron/src-gen/backend/electron-main.js
applications/electron/src-gen/backend/main.js
applications/electron/src-gen/backend/server.js
applications/electron/src-gen/frontend/index.js
applications/electron/src/daemon-manager.ts
applications/browser/package.json
applications/electron/package.json
packages/arc-extension/src/node/arc-extension-backend-module.ts
packages/arc-extension/src/browser/arc-extension-frontend-module.ts
scripts/start-browser-arc.mjs
```

### 2.2 Answer these specific questions before coding

For each question, write your finding in the `docs/patches/startup-opt/RESEARCH.md`
file you will create (see §5).

**Backend module criticality audit:**
For each of the 21 backend modules in `server.js`:
- Q1: Does this module register an HTTP route or WebSocket handler that the frontend
  needs during its initial load sequence? (critical = cannot defer)
- Q2: Does this module have a synchronous side effect that must complete before
  `BackendApplication.start()` is called? (critical = cannot defer)
- Q3: What is the approximate require() cost? (run with `--prof` or estimate from
  package size if profiling not available)
- Q4: Safe to defer? Yes / No / Maybe + reason

**Frontend module criticality audit:**
For each of the 25 frontend modules in `frontend/index.js`:
- Q5: Is this module needed before `FrontendApplication.start()` returns?
- Q6: Does this module contribute anything visible in the first 500ms?
- Q7: Can its DI contributions be registered lazily without breaking Inversify's
  resolution graph?
- Q8: Safe to defer? Yes / No / Maybe + reason

**Electron pre-warm window:**
- Q9: In `electron-main.js`, what is the sequence: app.ready → backend spawn →
  backend ready → window create → window load → did-finish-load?
  Draw this as a timeline with approximate durations from `startupLog` evidence.
- Q10: At what point in the sequence can we START the backend process earlier?
  (before `app.ready`? immediately at process start? at `app.will-finish-launching`?)
- Q11: Does `DaemonManager` in `applications/electron/src/daemon-manager.ts` provide
  a hook or interface we should extend, or should pre-warm be separate?
- Q12: What IPC mechanism should the pre-warm use to signal readiness to the main
  process? (existing `process.send(addressInfo)` pattern in main.js? named pipe?
  HTTP health poll?)

**Theia DI safety:**
- Q13: Can Inversify `Container.load()` calls be split across microtasks without
  breaking binding resolution? Specifically: if module A binds interface X and
  module B depends on X, is it safe to defer B to after `application.start()` if B's
  contributions are only resolved on first user action?
- Q14: What does `@theia/core`'s `FrontendApplicationContribution` lifecycle
  (specifically `onStart`, `onWillStart`) guarantee about load order?
- Q15: Does `arc-extension-frontend-module` have any `onWillStart` contributions that
  are blocking the shell from rendering? Read the actual source.

### 2.3 Baseline measurement

Before any code change, run the measurement harness (or instrument manually):

```bash
# Backend cold-start time
time node applications/browser/src-gen/backend/main.js --port 3001 &
# Then measure time to first HTTP 200 on :3001/
curl -o /dev/null -s -w "%{time_total}" http://127.0.0.1:3001/
```

Record the baseline in `docs/patches/startup-opt/RESEARCH.md` under
`## Baseline Measurements`.

---

## 3. Phase 2 — Plan

After completing the research, write `docs/patches/startup-opt/PLAN.md` containing:

### 3.1 Module deferral list

A table with columns:
`Module | Layer | Defer? | Defer strategy | Risk | Fallback`

Strategies allowed:
- **PARALLEL**: load concurrently with other deferred modules using `Promise.all()`
  instead of sequential `await`
- **POST-SHELL**: load after `application.start()` resolves, in a non-blocking
  continuation; register contributions via late-binding
- **LAZY-ON-USE**: use Theia's `activationEvents` pattern — only load when the user
  opens a specific view/command
- **KEEP-SEQUENTIAL**: must stay in place for correctness

### 3.2 Pre-warm architecture decision

Choose ONE of these strategies based on your Q9–Q12 research findings:

**Option PW-A (Electron main early spawn):**
In `electron-main.js`, spawn the backend Node.js process at `app.will-finish-launching`
(before `app.ready`). Backend process writes its address to a named pipe or temp file.
Main process polls for readiness (HTTP GET /health, max 10s, 100ms interval).
When ready, create the window immediately (backend already warm).

**Option PW-B (Persistent background process):**
Keep the backend running between window closes (don't `process.kill` on window close).
On window re-open, skip backend startup entirely. Use `app.on('before-quit')` to
clean up. Scope: Electron only.

**Option PW-C (Browser: startup script pre-start):**
Modify `scripts/start-browser-arc.mjs` to start the backend, wait for `/health`,
then open the browser tab. Reduces perceived startup for development workflow.
Does not help packaged Electron.

**Recommendation rule:** Prefer PW-A for the Electron path (biggest user impact),
PW-C for the browser dev path. Only implement PW-B if PW-A is measured to be
insufficient AND the session persistence risk is acceptable.

### 3.3 Risk register

For each planned change, document:
- What breaks if the defer is wrong (e.g., DI binding missing at resolution time)
- How to detect the failure (test, runtime error, or visual regression)
- Rollback: what single-line revert restores prior behavior

### 3.4 Test plan

For each optimization:
- Unit test: what existing test exercises the affected module path?
- New test: what new test validates the optimization doesn't regress behavior?
- Measurement test: how do we assert the performance gate (§1 success criteria)?

---

## 4. Phase 3 — Implementation

Implement changes in this exact order. Do not skip ahead.

### 4.1 Measurement harness first (no optimization yet)

Create `scripts/measure-startup.mjs`:

```javascript
// Instruments ARC Studio startup and reports timing milestones.
// Usage: node scripts/measure-startup.mjs [--electron|--browser] [--iterations=3]
// Output: JSON to stdout + human summary to stderr
// Schema:
// {
//   "run": number,
//   "mode": "electron" | "browser",
//   "milestones": {
//     "t_process_start": 0,              // anchor
//     "t_backend_modules_loaded": number, // ms from process_start
//     "t_backend_http_ready": number,     // ms from process_start
//     "t_electron_app_ready": number,     // Electron only
//     "t_window_created": number,         // Electron only
//     "t_window_did_finish_load": number, // Electron only
//     "t_frontend_modules_loaded": number,
//     "t_frontend_shell_start": number,
//     "t_frontend_application_started": number
//   },
//   "deltas": { ... computed from milestones ... },
//   "baseline": boolean
// }
```

Instrument the existing `startupLog` calls in `main.js`, `server.js`, `index.js`, and
`electron-main.js` to emit structured JSON to a temp file (path in `ARC_STARTUP_TRACE`
env var) IN ADDITION to the existing console.debug output. Do not remove console.debug.

Run baseline: `node scripts/measure-startup.mjs --browser --iterations 3 > docs/patches/startup-opt/baseline.json`

**Do not proceed to 4.2 until baseline.json exists with real measurements.**

### 4.2 Backend: parallel module loading

In `applications/browser/src-gen/backend/server.js` and
`applications/electron/src-gen/backend/server.js`:

Replace sequential `await load()` chains with grouped `Promise.all()` for modules
that your Phase 2 research classified as PARALLEL-safe. Keep KEEP-SEQUENTIAL modules
in their original position.

Pattern:
```javascript
// BEFORE (sequential — slow):
await load(require('@theia/markers/lib/node/problem-backend-module'));
await load(require('@theia/messages/lib/node/messages-backend-module'));
await load(require('@theia/navigator/lib/node/navigator-backend-module'));

// AFTER (parallel — faster, only when modules are independent):
await Promise.all([
    load(require('@theia/markers/lib/node/problem-backend-module')),
    load(require('@theia/messages/lib/node/messages-backend-module')),
    load(require('@theia/navigator/lib/node/navigator-backend-module')),
]);
```

**Safety rule:** NEVER parallelise modules that bind the same interface token or
where module B's `onLoad` depends on a binding registered by module A.
Document each parallelisation decision with a comment: `// PARALLEL-SAFE: <reason>`

**Do not touch:**
- `backendApplicationModule` — must stay first
- `messagingBackendModule` — must stay second
- `loggerBackendModule` — must stay third
- `arc-extension-backend-module` — last, depends on all Theia services

### 4.3 Frontend: parallel module loading

Same pattern as 4.2, applied to `frontend/index.js` in both browser and electron apps.

Additional constraint: `monaco-frontend-module` and `editor-frontend-module` have known
ordering requirements in Theia 1.71.x — keep them sequential relative to each other.
`MonacoInit.init(container)` must stay after all modules are loaded.

**Do not touch:**
- `preload` step — must complete before container loads
- `messagingFrontendModule` — must stay in the synchronous pre-async block
- `frontendApplicationModule` — must stay first in the async block
- `loggerFrontendModule` — must stay immediately after frontendApplicationModule
- `arc-extension-frontend-module` — keep last (depends on all Theia services)

### 4.4 Backend: POST-SHELL deferral of non-critical modules

For modules classified POST-SHELL in your plan:

```javascript
// Pattern: defer non-critical backend module registration
// Load these AFTER server.start() returns, in a non-blocking continuation
// Use setImmediate() to yield to the event loop first
async function loadDeferredModules(container) {
    await new Promise(resolve => setImmediate(resolve));
    try {
        await load(require('<deferred-module>'));
        startupLog('deferred module loaded: <name>');
    } catch (err) {
        // Log but do not crash — deferred module failures are non-fatal
        console.error('Deferred module load failed (non-fatal):', err);
    }
}

// In server export function, after start() returns:
const serverAddr = await start(port, host, argv);
loadDeferredModules(container).catch(err =>
    console.error('Deferred backend module error:', err)
);
return serverAddr;
```

### 4.5 Electron pre-warm (Option PW-A)

Edit `applications/electron/src-gen/backend/electron-main.js`:

```javascript
// PRE-WARM: Start backend process as early as possible — before app.ready
// This moves ~3-8s of backend boot time off the critical path.

const { fork } = require('child_process');
const path = require('path');
const http = require('http');

let prewarmedBackendAddress = null;
let prewarmedBackendProcess = null;

function startPrewarmedBackend() {
    const backendMain = path.resolve(__dirname, 'main.js');
    prewarmedBackendProcess = fork(backendMain, ['--port', '0'], {
        // port 0 = OS-assigned port; backend sends address via process.send()
        silent: false,
        env: { ...process.env, ARC_PREWARM: '1' }
    });
    prewarmedBackendProcess.on('message', (addressInfo) => {
        prewarmedBackendAddress = addressInfo;
        startupLog(`Backend pre-warm ready on port ${addressInfo.port}`);
    });
    prewarmedBackendProcess.on('error', (err) => {
        console.error('Pre-warm backend process error:', err);
        prewarmedBackendAddress = null;
    });
}

// Start backend pre-warm IMMEDIATELY — before app.ready
startPrewarmedBackend();
```

In the `ElectronMainApplication` startup sequence, modify the backend-spawn path to
skip spawning a new backend process if `prewarmedBackendAddress` is already set:

```javascript
// In the application.start(config) call site, pass the pre-warmed address
// so ElectronMainApplication uses it instead of spawning a new backend.
// Check @theia/core's ElectronMainApplication API for the correct injection point.
// If no public API exists, patch via environment variable:
if (prewarmedBackendAddress) {
    process.env.THEIA_BACKEND_PORT = String(prewarmedBackendAddress.port);
}
```

Add cleanup on app quit:
```javascript
app.on('before-quit', () => {
    if (prewarmedBackendProcess) {
        prewarmedBackendProcess.kill();
    }
});
```

**Safety gates:**
- Pre-warm failure must be non-fatal. If `prewarmedBackendAddress` is null when the
  window opens, fall back to the existing backend-spawn path (the current code).
- Pre-warm process must be killed on app quit — no orphan backends.
- `ARC_PREWARM=1` environment variable allows the backend to detect it was pre-warmed
  and potentially skip non-essential init steps.

### 4.6 Browser dev: pre-start in startup script

Edit `scripts/start-browser-arc.mjs`:

```javascript
// Add a health-poll before opening the browser tab.
// The backend is already started by this script; just wait for it to be ready.
async function waitForBackend(port, maxWaitMs = 15000) {
    const start = Date.now();
    while (Date.now() - start < maxWaitMs) {
        try {
            await fetch(`http://127.0.0.1:${port}/`);
            return true;
        } catch (_) {
            await new Promise(r => setTimeout(r, 150));
        }
    }
    throw new Error(`Backend on port ${port} did not become ready within ${maxWaitMs}ms`);
}
```

### 4.7 Health endpoint

Add a `/health` GET endpoint to the backend so pre-warm polling is deterministic:

In `packages/arc-extension/src/node/arc-extension-backend-module.ts` (or a new
`arc-health-module.ts`), bind a `BackendApplicationContribution` that registers:

```typescript
configure(app: express.Application): void {
    app.get('/health', (_req, res) => {
        res.json({
            status: 'ok',
            uptime: process.uptime(),
            version: require('../../../package.json').version
        });
    });
}
```

This endpoint must:
- Respond within 10ms (no async work)
- Return HTTP 200 with JSON `{ status: 'ok' }`
- Be available as soon as the backend HTTP server is listening (before full DI init
  completes, if possible)

---

## 5. Deliverables — Patch Folder

All output artifacts go into a NEW folder: `docs/patches/startup-opt/`

Create this folder and populate it with:

```
docs/patches/startup-opt/
├── RESEARCH.md          ← Phase 2 findings: module audit, Q1-Q15 answers, baseline measurements
├── PLAN.md              ← Phase 3 plan: deferral table, pre-warm decision, risk register, test plan
├── IMPLEMENTATION.md    ← What was changed, file by file, with before/after diffs
├── MEASUREMENTS.md      ← Baseline vs. optimized timing tables; must include real numbers
├── TESTS.md             ← New test descriptions + test run evidence
├── HANDOVER.md          ← Full handover document (see §6 for required sections)
├── baseline.json        ← Raw JSON output from measure-startup.mjs before changes
└── optimized.json       ← Raw JSON output from measure-startup.mjs after changes
```

**Do not put these files anywhere else. Do not create a new roadmap/phases file.**

---

## 6. Handover Document (HANDOVER.md) — Required Sections

The handover document must contain ALL of the following sections, each with real content
(not placeholders):

### Section 1: Executive Summary
- What was the problem (specific measured cold-start times)
- What was implemented (specific techniques)
- What was the result (specific measured improvements)
- What was NOT done and why

### Section 2: Architecture Decisions Made
For each architectural decision (e.g., PW-A vs PW-B, which modules to defer):
- Decision statement
- Alternatives considered
- Reason chosen
- Reversibility (how to undo in one sentence)

### Section 3: Files Changed
Complete table: `File | Type of change | Lines changed | Risk level`
For every file touched, no exceptions.

### Section 4: Module Deferral Map
Complete table of all 21 backend + 25 frontend modules:
`Module | Original position | New strategy | Rationale | Tested by`

### Section 5: Pre-Warm Sequence Diagram
ASCII sequence diagram showing the new Electron startup sequence:
```
Process start → startPrewarmedBackend() → [backend booting in background]
                                                     ↓
app.ready ──────────────────────────────────────────→ window.loadURL()
                                                     ↓
                          [if pre-warm ready] ──→ instant handshake
                          [if pre-warm failed] ─→ fallback: spawn new backend
```

### Section 6: Performance Measurements
Table with columns: `Metric | Baseline (ms) | Optimized (ms) | Delta (ms) | Delta (%)`
Rows for every milestone in measure-startup.mjs.
Must be real numbers from actual runs, not estimates.
Include iteration count and stddev if multiple runs taken.

### Section 7: Test Evidence
For every new test added:
- Test file path + test name
- What it asserts
- Pass/fail status + command run to verify

For regression suite:
- `cd python && uv run pytest tests/ -q` — paste actual output summary
- `pnpm typecheck && pnpm build` — paste actual exit code and any warnings

### Section 8: Known Limitations and Risks
- What could go wrong in production that wasn't covered
- Platform-specific concerns (macOS / Linux / Windows differences)
- Theia version upgrade risks (these are src-gen files — they regenerate on `theia build`)
- Any module that was kept sequential because deferral was unsafe

### Section 9: Continuation Instructions
Step-by-step instructions for the next agent or engineer to:
1. Verify the optimizations are still in place
2. Re-run the measurement harness
3. Add a new deferred module (the pattern to follow)
4. Roll back a specific deferral if it causes a regression
5. Apply this same pattern to the Electron app if only the browser app was done first

### Section 10: Roadmap / Phases Update Required
State explicitly:
- Whether a new phase entry should be appended to `docs/phases.md` under NEW INTAKE
- If yes: the exact phase text to append (follow the phases.md format exactly)
- If no: why not (e.g., this is an internal build optimization with no product surface)
- Status to claim (use only: Not Started / In Progress / Baseline Complete; do NOT claim
  Polished Complete without all DoD gates having cited evidence)

---

## 7. Verification Checklist (Agent Must Run All Before Declaring Done)

Run each command and record actual output in TESTS.md:

```bash
# 1. Python test suite — must match or exceed baseline pass count
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
# Expected: ≥6438 passed, 0 failed

# 2. TypeScript typecheck
pnpm typecheck
# Expected: exit 0, no errors

# 3. TypeScript build
pnpm build
# Expected: exit 0

# 4. Banned claims check
bash scripts/check-banned-claims.sh
# Expected: exit 0

# 5. Electron smoke build (no signing required)
cd applications/electron
pnpm package:smoke
# Expected: generates dist/ directory, no errors

# 6. Startup measurement — MUST produce real numbers
node scripts/measure-startup.mjs --browser --iterations 3 > docs/patches/startup-opt/optimized.json
# Expected: JSON with all milestone timestamps, t_backend_http_ready reduced vs baseline

# 7. Health endpoint test
node applications/browser/src-gen/backend/main.js --port 3099 &
sleep 5
curl -f http://127.0.0.1:3099/health
# Expected: {"status":"ok",...}
kill %1
```

---

## 8. Constraints and Anti-Patterns (Do Not Do These)

| Anti-pattern | Why forbidden |
|---|---|
| Modify `docs/roadmap.md` or `docs/phases.md` with NEW top-level scope | Violates AGENTS.md §1 |
| Create a replacement or competing roadmap/status markdown | Violates AGENTS.md locked charter |
| Change public CLI command names, flags, or JSON output shapes | Violates AGENTS.md §4 |
| Remove `startupLog` milestone calls | Breaks future profiling |
| Parallelize DI modules that share bindings | Will cause Inversify `ambiguous binding` errors |
| Defer `backendApplicationModule`, `messagingBackendModule`, `loggerBackendModule` | Core — deferring breaks the entire backend |
| Defer `frontendApplicationModule`, `loggerFrontendModule` | Core — deferring breaks the entire frontend |
| Defer `arc-extension-frontend-module` or `arc-extension-backend-module` without careful audit | ARC's own extension — check DI graph first |
| Claim "production ready" or "multi-user" anywhere | Banned by `check-banned-claims.sh` |
| Commit changes without explicit owner request | AGENTS.md §7 |
| Use LLM-based security decisions | AGENTS.md §5 |
| Pre-warm that leaves orphan backend processes on crash | Security / resource leak |
| Hard-code port numbers for pre-warmed backend | Use port 0 + OS assignment + IPC |
| Mutate frozen `EnforcementContext` | AGENTS.md §6 |

---

## 9. Scope Boundaries

**In scope:**
- `applications/browser/src-gen/backend/server.js`
- `applications/browser/src-gen/frontend/index.js`
- `applications/electron/src-gen/backend/electron-main.js`
- `applications/electron/src-gen/backend/server.js`
- `applications/electron/src-gen/frontend/index.js`
- `applications/electron/src/daemon-manager.ts` (read-only unless pre-warm extension needed)
- `scripts/start-browser-arc.mjs`
- `scripts/measure-startup.mjs` (new file)
- `packages/arc-extension/src/node/` (health endpoint only)
- `docs/patches/startup-opt/` (new folder, all deliverables)

**Out of scope (do not touch):**
- `docs/roadmap.md` — read-only
- `docs/phases.md` — read-only (append NEW INTAKE only if required, per §6 Section 10)
- `python/` — no changes (no Python startup optimization in this prompt)
- `packages/arc-extension/src/browser/` — no changes except to audit for Q15
- `packages/arc-ag-ui/` — no changes
- `applications/electron/electron-builder.release.yml` — no changes
- Any test file in `tests/` — only ADD new tests, never delete existing ones
- `.github/workflows/` — no changes

---

## 10. Research Annex — Build From Scratch: The Zed Model

This section is **research only** — no implementation is required in this prompt.
Record your findings and recommendations in `docs/patches/startup-opt/SCRATCH_BUILD_RESEARCH.md`.
This research directly informs whether the Theia optimizations in §§2–9 are sufficient
long-term, or whether a future "ARC Native" track should be proposed as a NEW INTAKE item.

### 10.1 Background: Why Zed Is The Reference

Zed (https://github.com/zed-industries/zed, Apache-2.0 / GPL-3.0) is the most
technically aggressive IDE built from scratch in the 2020s. Its architecture is the
primary counter-argument to "Electron + Node.js is good enough for a fast IDE."

**Key facts to research and verify:**

| Claim | Source to verify | What to look for |
|---|---|---|
| Zed cold-starts in <200ms on macOS arm64 | `zed.dev/blog`, GitHub benchmarks, `ZED_MEASUREMENTS=1` output in issues | Actual reported numbers |
| GPUI renders via Metal (macOS) / Vulkan (Linux) / Direct3D (Windows) directly | `crates/gpui/` in zed repo | GPU backend abstraction layer |
| No Chromium / no WebView / no DOM — all text rendered on GPU | `crates/gpui/src/` rendering pipeline | Custom text shaping, glyph atlas |
| Single-process architecture (no renderer/main split) | `crates/zed/src/main.rs` | Process count at runtime |
| Extensions run in WASM sandbox (not Node.js subprocesses) | `crates/extension/` | `wasmtime` or similar |
| Tree-sitter for syntax (not TextMate / Monaco grammar system) | `crates/language/` | `tree-sitter` crate deps |
| LSP client built in, not delegated to a language server host process | `crates/lsp/` | Direct LSP socket management |
| Startup time: Zed window interactive in ~150–250ms on M-series Mac | GitHub issues, blog posts, `ZED_MEASUREMENTS=1` | Histogram data |

### 10.2 GPUI Architecture Deep Dive

Research and document the GPUI rendering stack in `SCRATCH_BUILD_RESEARCH.md`:

**GPUI is Zed's proprietary UI framework** (Apache-2.0, open source since Jan 2024).
It is NOT a web browser, NOT an Electron renderer, NOT a React reconciler.

Architecture to map:
```
User code (Rust) → GPUI retained-mode model → GPU command buffer
                                             ↓
                          macOS: Metal  ←── platform abstraction ──→ Linux: Vulkan
                          Windows: Direct3D                            (WebGPU future)
                                             ↓
                          GPU renders every frame at 120fps
                          CPU is NEVER in the render critical path
```

Research questions:
- Q-Z1: What is the GPUI component model? (retained vs immediate mode, entity system)
- Q-Z2: How does text rendering work? (font rasterization, glyph atlas, subpixel AA)
- Q-Z3: How does GPUI handle input events on Wayland vs X11 vs macOS vs Windows?
- Q-Z4: What is the extension host model? (WASM `wasmtime`, language extensions,
         theme extensions — all loaded at startup vs lazy?)
- Q-Z5: What is Zed's startup sequence from `main()` to first interactive frame?
         (Draw the timeline: process start → asset loading → window create → first paint)
- Q-Z6: How does Zed handle Monaco-equivalent editor features?
         (custom rope data structure, incremental syntax highlighting, virtual scroll)
- Q-Z7: What does Zed NOT support that ARC requires?
         (Node.js backend, Python daemon, React-based widgets, WebSocket JSON-RPC,
          Theia's DI system, existing ARC extension API surface)

### 10.3 "Build ARC Native" — What It Would Actually Mean

If ARC were to build an IDE shell from scratch in the spirit of Zed (call it
"ARC Native"), document the realistic scope:

**Option SN-A: GPUI-based ARC shell (Rust + GPUI)**

Replace: Electron + Theia frontend + Monaco + WebSocket JSON-RPC + React
With: Rust binary + GPUI + ropey/xi-rope text model + tree-sitter + custom LSP

What stays: Python daemon (FastAPI/uvicorn), ARC CLI, SwarmGraph runtime, adapters
What goes: `packages/arc-extension/`, `applications/browser/`, `applications/electron/`,
           all `@theia/*` dependencies (~150MB node_modules)

Cost estimate (research-based, not guessed):
- Zed team size when they built GPUI: ~5–8 engineers, ~2 years before open-sourcing
- ARC-specific surfaces to rebuild in GPUI: chat panel, run timeline, graph view,
  diff viewer, trace viewer, approval/HITL panel, provider config, sandbox status
- TypeScript → Rust migration: ALL existing arc-extension code
- Loss of VS Code extension ecosystem compatibility (Theia's key value prop)
- Loss of Monaco editor (would need Zed-style rope + tree-sitter pipeline)

Blocking constraints for ARC today:
1. ARC's entire extension and UI code is TypeScript/React — a Rust/GPUI rewrite
   is a full discard, not a migration.
2. ARC depends on Monaco editor for code editing fidelity — Zed's editor is NOT
   Monaco and NOT compatible.
3. ARC's DI architecture (Inversify) has no Rust equivalent; all widget/service
   wiring would need to be redesigned.
4. VS Code extension compatibility (OpenVSX) — Theia supports it; GPUI does not.
5. Zed is GPL-3.0 for the editor (GPUI is Apache-2.0) — GPL is compatible with
   ARC's current open-source posture but must be verified.

**Option SN-B: Tauri v2 shell + retain ARC TypeScript frontend**

Replace: Electron + Node.js bundled in renderer
With: Tauri v2 (Rust shell) + system WebView (WKWebView/WebView2/WebKitGTK)
Keep: All TypeScript/React frontend code, Monaco editor, existing Theia widgets

This is NOT "build from scratch" — it's "replace the shell only."
This was already evaluated in the pre-research (§0 of the parent research).
Key finding: WKWebView on macOS has known Monaco rendering bugs. WebView2 on
Windows requires a separate bootstrap install. Not recommended before v1.0.

**Option SN-C: Hybrid — GPUI chrome + WebView panel for complex UI**

Replace: Electron window chrome with a lightweight GPUI shell
Keep: WebView iframe inside GPUI for Monaco + React panels

This is the architecture that some tools (e.g., early Tauri + web hybrid apps)
have attempted. Reality: GPUI's WebView embedding is experimental and not
production-proven as of 2026. High maintenance cost.

### 10.4 Competitive Startup Time Benchmarks

Research and populate this table in `SCRATCH_BUILD_RESEARCH.md`.
All numbers must be sourced — cite the URL or GitHub issue.
If a number is unavailable, write "not publicly measured" rather than estimating.

| IDE | Stack | Cold start to interactive (macOS arm64) | Source |
|---|---|---|---|
| **Zed** | Rust + GPUI + Metal | ~150–250ms | zed.dev performance blog / GitHub |
| **Helix** | Rust + crossterm (TUI) | ~30–80ms | TUI, not GUI — not comparable |
| **Neovim** | C + Lua | ~50–150ms | TUI — not comparable |
| **VS Code** | Electron + Node.js | ~1.5–3s | Various benchmarks |
| **Cursor** | Electron (VS Code fork) | ~2–4s | Community benchmarks |
| **Windsurf** | Electron (VS Code fork) | ~2–4s | Similar to Cursor |
| **IntelliJ IDEA** | JVM + Swing | ~4–8s | JetBrains docs + community |
| **Theia (vanilla)** | Electron + Node.js | ~5–12s | Upstream Theia issues |
| **ARC Studio (current)** | Electron + Node.js | MEASURE THIS | §4.1 baseline |
| **ARC Studio (optimized)** | Electron + Node.js + pre-warm | MEASURE THIS | §4.1 optimized |

### 10.5 Honest Assessment: Should ARC Build From Scratch?

Based on your research, write a SHORT (max 500 words) recommendation in
`SCRATCH_BUILD_RESEARCH.md` covering:

1. **The honest gap**: How large is the startup time gap between optimized
   ARC Studio (Theia + pre-warm + lazy loading) and Zed? Is it a product-level
   problem or an engineering curiosity?

2. **The VS Code extension moat**: Theia's ability to run OpenVSX extensions is
   a significant competitive advantage that a GPUI rewrite would forfeit entirely.
   Is this worth the startup speed gain?

3. **The rewrite cost vs. optimization ROI**: The pre-warm + lazy loading
   optimizations in §§2–9 are estimated at 1–2 weeks of engineering. A Rust/GPUI
   rewrite of ARC's IDE layer is estimated at 18–36 months for a small team.
   Is there a middle path?

4. **Recommended path for ARC**:
   - Near-term (next 6 months): Implement §§2–9 optimizations. Target
     `T_frontend_shell_visible` ≤ 2s on macOS arm64.
   - Medium-term (6–18 months): If the optimized Theia startup remains a user
     complaint AND VS Code extension compat is not needed for ARC's agent-IDE
     use case, evaluate Tauri v2 shell (when WKWebView Monaco bugs are closed)
     as a shell replacement — keeping ALL TypeScript/React frontend code.
   - Long-term (18m+): Only propose a GPUI/native rewrite if (a) ARC has
     shipped v1.0, (b) user research confirms startup is a top-3 complaint,
     (c) the team has Rust expertise, and (d) the VS Code extension ecosystem
     is explicitly deprioritized in favor of ARC's own plugin system.

5. **NEW INTAKE item**: If the research supports it, draft the exact text for
   a new roadmap item to add under `docs/roadmap.md`'s NEW INTAKE marker:
   ```
   ## NEW INTAKE

   ### R-NATIVE1 — ARC Native Shell Research Track
   Status: Not Started
   Scope: Research-only. Evaluate GPUI / Tauri v2 / native shell options as
   a long-term successor to the Electron + Theia shell. Gate: post-v1.0.
   No implementation until R-NATIVE1 is explicitly promoted to In Progress
   by the product owner.
   Evidence required before promotion: startup benchmark gap confirmed >3s
   versus Zed, user research data, Rust/GPUI prototype feasibility spike.
   ```
   **Do not add this entry without explicit owner approval.** Include it in
   the handover as a proposed entry only.

### 10.6 Deliverable for This Annex

Write `docs/patches/startup-opt/SCRATCH_BUILD_RESEARCH.md` containing:
- Section A: GPUI Architecture Notes (Q-Z1 through Q-Z7 answers with sources)
- Section B: Startup Benchmark Table (§10.4, filled with sourced numbers)
- Section C: "Build From Scratch" Cost Analysis (SN-A, SN-B, SN-C assessments)
- Section D: Recommendation (§10.5, max 500 words)
- Section E: Proposed NEW INTAKE item text (draft only, not applied)

---

## 11. Final Note to the Agent

**Evidence over claims.** Every number in MEASUREMENTS.md must come from a real run.
If you cannot measure a milestone (e.g., Electron `did-finish-load` requires a display),
state that explicitly and describe how to measure it manually instead of inventing a number.

**Fail safely.** Every optimization must degrade gracefully: if parallel loading throws,
fall back to sequential. If pre-warm fails, fall back to existing backend spawn. Log but
do not crash.

**Read before writing.** Do not assume what a module does — read it. The src-gen files
are generated by `@theia/cli` but are already customized for ARC. Treat them as
first-class source files.

**The scratch-build research (§10) is RESEARCH ONLY** — no Rust code, no GPUI code,
no shell replacement. Its sole output is `SCRATCH_BUILD_RESEARCH.md` and a draft
NEW INTAKE item for human review. Do not start implementing a native shell.

**The goal is a working, measured, tested patch** delivered in `docs/patches/startup-opt/`
with a complete handover that the next engineer can pick up cold and understand in 15 minutes.
