# Phase 6: Bug Bash Report

**Date:** 2026-05-13
**Agent:** Agent 3 (Bug Bash Session)

## Summary

| Metric | Count |
|--------|-------|
| Issues triaged | 7 |
| Issues fixed | 4 |
| Issues accepted (won't fix) | 2 |
| Issues deferred | 1 |
| New issues discovered | 0 |

---

## Issues Reproduced

### 1. @theia/file-search missing (MEDIUM)
- **Status:** ACCEPTED (won't fix)
- **Reproduction:** Attempt to use global file search (Cmd+Shift+F). The feature is not available.
- **Root cause:** ripgrep incompatibility with Node.js v25. The `@theia/file-search` package depends on ripgrep which does not support the current Node.js version.
- **Disposition:** Accepted. This is an upstream dependency issue. Will be resolved when ripgrep adds Node.js v25 support or when the project downgrades Node.js.

### 2. Keyboard shortcuts not global (MEDIUM)
- **Status:** FIXED
- **Reproduction:** 
  1. Open ARC widget
  2. Click on editor area to move focus away from widget
  3. Press Cmd+E (or Ctrl+E)
  4. Observe: shortcut does not trigger workflow execution
- **Root cause:** Keyboard shortcuts were registered via DOM event listener on the widget node (`this.node.addEventListener('keydown', ...)`), which only fires when the widget has focus.
- **Fix:** Created `ArcKeybindingContribution` implementing Theia's `KeybindingContribution` and `CommandContribution` interfaces. Registered commands (`arc.execute`, `arc.loadTraces`, `arc.scanWorkspace`, `arc.showShortcuts`) with global keybindings via Theia's `KeybindingRegistry`.
- **Files changed:**
  - `packages/arc-extension/src/browser/arc-keybinding-contribution.ts` (new)
  - `packages/arc-extension/src/browser/arc-widget-contribution.ts` (added public methods)
  - `packages/arc-extension/src/browser/arc-widget.tsx` (made handlers public)
  - `packages/arc-extension/src/browser/arc-extension-frontend-module.ts` (registered contribution)
- **Note:** Changed `Ctrl+S` to `Ctrl+Shift+S` for scan workspace to avoid conflict with Theia's built-in save shortcut.

### 3. Toast timeout cleanup (LOW)
- **Status:** ALREADY FIXED
- **Reproduction:** 
  1. Trigger multiple toast notifications rapidly
  2. Close the widget before timeouts expire
  3. Check for memory leaks
- **Finding:** The code already correctly implements timeout cleanup. `toastTimeouts` Map tracks all active timeouts (line 68), `dispose()` clears all timeouts (lines 110-118), and `removeToast()` clears individual timeouts (lines 182-191).
- **Disposition:** No action needed. Already implemented correctly.

### 4. Collapsed section badges (LOW)
- **Status:** FIXED
- **Reproduction:**
  1. Load traces or detect workflows
  2. Collapse the respective section
  3. Observe: no visual indication of item count when section is collapsed
- **Fix:** Added badge counters to collapsed section headers. Shows item count for Trace Viewer and Workflow Detection sections, and status indicator for Workflow Execution section.
- **Files changed:**
  - `packages/arc-extension/src/browser/arc-widget.tsx` (added badges to section headers)
  - `packages/arc-extension/src/browser/style/arc-widget.css` (added `.arc-section-badge` and `.arc-section-header-right` styles)

### 5. Trace filter UX (LOW)
- **Status:** FIXED
- **Reproduction:**
  1. Load traces
  2. Type in the filter input
  3. Observe: filter applies immediately on each keystroke (no debounce)
  4. Observe: no clear button to reset the filter
- **Fix:** 
  - Added 300ms debounce to trace filter input via `handleTraceFilterChange()` method
  - Added clear button (×) that appears when filter has content
  - Cleanup of debounce timer in `dispose()`
- **Files changed:**
  - `packages/arc-extension/src/browser/arc-widget.tsx` (added debounce logic, clear button)
  - `packages/arc-extension/src/browser/style/arc-widget.css` (added `.arc-filter-input-wrapper` and `.arc-filter-clear` styles)

### 6. Monaco bundle size (LOW)
- **Status:** ACCEPTED (won't fix)
- **Reproduction:** Check bundle size - bundle.js is 27.5 MiB (exceeds 10 MiB recommended limit)
- **Root cause:** Monaco editor is a large dependency that includes the full VS Code editor. This is inherent to Theia's architecture.
- **Disposition:** Accepted. Monaco editor size is an upstream concern. Theia already code-splits editor workers. Optimization would require significant architectural changes with minimal user benefit for a local dev tool.

### 7. No automated E2E tests (LOW)
- **Status:** DEFERRED
- **Reproduction:** Check test coverage - no E2E tests exist for the UI
- **Disposition:** Deferred to Phase 7 (or next dedicated testing phase). E2E testing requires Playwright/Cypress setup, CI integration, and test fixture management. This is a significant effort beyond bug bash scope.

---

## Issues Fixed

| Issue | Severity | Files Changed |
|-------|----------|---------------|
| Keyboard shortcuts not global | MEDIUM | `arc-keybinding-contribution.ts` (new), `arc-widget-contribution.ts`, `arc-widget.tsx`, `arc-extension-frontend-module.ts` |
| Collapsed section badges | LOW | `arc-widget.tsx`, `arc-widget.css` |
| Trace filter UX | LOW | `arc-widget.tsx`, `arc-widget.css` |
| Toast timeout cleanup | LOW | Already fixed (no changes needed) |

---

## Issues Accepted (Won't Fix)

| Issue | Severity | Justification |
|-------|----------|---------------|
| @theia/file-search missing | MEDIUM | Upstream ripgrep incompatibility with Node.js v25. Not fixable within this project. |
| Monaco bundle size | LOW | Inherent to Theia architecture. Local dev tool, not production-facing. |

---

## Issues Deferred

| Issue | Severity | Target Phase | Justification |
|-------|----------|--------------|---------------|
| No automated E2E tests | LOW | Phase 7+ | Requires significant infrastructure setup beyond bug bash scope |

---

## Keyboard Shortcuts Reference

After fix, the following global shortcuts are available:

| Action | Windows/Linux | Mac |
|--------|--------------|-----|
| Execute Workflow | `Ctrl+E` | `⌘+E` |
| Load Traces | `Ctrl+L` | `⌘+L` |
| Scan Workspace | `Ctrl+Shift+S` | `⌘+Shift+S` |
| Show Shortcuts | `Ctrl+H` | `⌘+H` |

**Note:** Scan Workspace was changed from `Ctrl+S` to `Ctrl+Shift+S` to avoid conflict with Theia's built-in file save shortcut.

---

## Build Verification

- TypeScript compilation: **PASSED**
- Full project build: **PASSED** (webpack compiled successfully)
- Bundle size: 27.5 MiB (unchanged, Monaco-related warning expected)
