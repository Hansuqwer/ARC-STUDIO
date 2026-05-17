# Extension Migration Inventory

**Date:** 2026-05-14
**Source:** `docs/IMPLEMENTATION_PLAN.md` (migration policy), code audit of `theia-extensions/*`

Canonical extension: `packages/arc-extension`
Status: Wired into `applications/browser` since PR 5 (commit 765beb4), replacing
duplicate `theia-extensions/*` browser dependencies during transition.

**Migration status (2026-05-17):** Phase C cleanup in progress — critical release-scope
widgets/services are canonical in `packages/arc-extension` (adapters, workflow graph,
run timeline, event stream, safe settings prefs, health, status bar, welcome widget,
chat launch UI, and run diff UI/service). Legacy `theia-extensions/*` packages are no
longer wired into `applications/browser`, `applications/electron`, root typecheck, or
the pnpm workspace; source dirs remain on disk only for rollback/history until archive.

---

## Inventory

| # | Extension | Type | Files / Lines | Tests | Overlap w/ canonical | Action | Priority | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | `arc-core` | Both | 14 / 694 | 4 | Ported for release scope — protocol/service/main widget/status bar/welcome/prefs now canonical | Archive after smoke | P0 | Removed from browser app deps; legacy source retained for rollback/history until archive. |
| 2 | `arc-runs` | FE | 5 / 1181 | 2 | Ported for release scope — timeline, chat launch controls, and run diff now canonical | Archive after smoke | P0 | Removed from browser app deps; legacy source retained for rollback/history until archive. |
| 3 | `arc-adapters` | FE | 3 / 240 | 0 | None | Port | P0 | Runtime readiness cards and doctor actions are product-critical. No equivalent in canonical extension. |
| 4 | `arc-workflows` | FE | 3 / 238 | 0 | None | Port | P0 | Workflow graph SVG visualization. No equivalent in canonical extension. |
| 5 | `arc-event-stream` | FE | 3 / 973 | 0 | Partial — replaces `TraceViewerSection` | Port | P0 | Significantly richer event visualization than inline component. |
| 6 | `arc-schemas` | FE | 3 / 162 | 0 | None | Port | P1 | Schema inspector. No equivalent in canonical extension. |
| 7 | `arc-health` | FE | 3 / 150 | 0 | Ported | Port small pieces | P1 | Backend health polling now lives in canonical `arc-extension`; original removed from browser app deps. |
| 8 | `arc-context` | FE | 3 / 114 | 0 | None | Port if in scope | P1 | Context pack viewer. Thin wrapper over existing service. |
| 9 | `arc-settings` | FE | 2 / 93 | 0 | Ported | Port prefs only | P1 | Safe preference schema lives in canonical `arc-extension`; raw token prefs intentionally excluded. |
| 10 | `arc-audit` | FE | 3 / 59 | 0 | None (stub) | Archive or rewrite | P1 | Currently shows "Not implemented" with empty array. Keep concept, archive code. |
| 11 | `arc-arena` | Both | 6 / 520 | 1 | None | Archive | P0 | LM Arena is out of v0.1 scope. Already excluded from workspace config. |
| 12 | `arc-product` | FE | 2 / 231 | 0 | None (branding) | Archive/delete | P0 | Branding shell removed from browser app deps; canonical extension provides its own widget identity. |

---

## Migration Sequence

### Phase A — Port critical UI (P0, ~3 PRs)

These extensions provide product-critical UX missing from `packages/arc-extension`. Port them
one at a time, adding tests and removing theia-extensions dependency after each port.

| Step | Extension | Method | Gate |
|------|-----------|--------|------|
| A.1 | `arc-adapters` | Copy widget and contribution code into `packages/arc-extension/src/browser/components/` | Build + UI contract tests |
| A.2 | `arc-workflows` | Copy workflow graph widget into canonical extension | Build + UI contract tests |
| A.3 | `arc-runs` | Copy run timeline widget, replacing inline `TraceViewerSection` and `WorkflowExecutionSection` | Build + all tests pass |

After A.3, the canonical extension should have equivalent or better UI than the
extensions it replaces.

### Phase B — Port remaining useful UI (P1, ~3 PRs)

| Step | Extension | Method | Gate |
|------|-----------|--------|------|
| B.1 | `arc-event-stream` | Replace `TraceViewerSection` with ported event stream widget | Build + UI contract tests |
| B.2 | `arc-schemas` | Copy schema inspector widget | Build + UI contract tests |
| B.3 | `arc-health` | ✅ Inline backend health checker into canonical extension | Build |
| B.4 | `arc-context` | Copy context pack viewer (if context UX remains in scope) | Build |
| B.5 | `arc-settings` | ✅ Consolidate safe preference schema; remove from browser deps | Build + preference tests |

### Phase C — Archive/delete remaining (P1)

After all useful code is ported:

| Step | Extension | Action |
|------|-----------|--------|
| C.1 | `arc-core` | ✅ Removed from `applications/browser` deps after canonical service/protocol/status/welcome/prefs landed; archive source after browser smoke |
| C.2 | `arc-adapters` | ✅ Removed from `applications/browser` deps; archive source after browser smoke |
| C.3 | `arc-runs` | ✅ Removed from `applications/browser` deps after canonical chat launch controls and run diff UI landed; archive source after browser smoke |
| C.4 | `arc-workflows` | ✅ Removed from `applications/browser` deps; archive source after browser smoke |
| C.5 | `arc-event-stream` | ✅ Removed from `applications/browser` deps; archive source after browser smoke |
| C.6 | `arc-schemas` | ✅ Removed old-core schema inspector from `applications/browser` deps; archive source after browser smoke |
| C.7 | `arc-context` | ✅ Removed old-core context-pack viewer from `applications/browser` deps; archive source after browser smoke |
| C.8 | `arc-settings` | ✅ Removed from `applications/browser` deps; archive source after browser smoke |
| C.9 | `arc-health` | ✅ Removed from `applications/browser` deps; archive source after browser smoke |
| C.10 | `arc-audit` | ✅ Removed static stub from `applications/browser` deps; archive source after browser smoke |
| C.11 | `arc-arena` | Already excluded; ensure no import paths remain |
| C.12 | `arc-product` | ✅ Removed branding shell from `applications/browser` deps; archive source after browser smoke |

---

## Dependency Graph

```
arc-core ──┬── arc-adapters
           ├── arc-audit
           ├── arc-context
           ├── arc-event-stream
           ├── arc-health
           ├── arc-runs
           ├── arc-schemas
           └── arc-workflows

arc-arena (standalone, its own backend service)
arc-product (standalone, no arc-core dependency)
arc-settings (depends on arc-core for theia types)
```

All extensions except `arc-product` depend on `arc-core` for:
- Protocol types (`ArcEnvelope`, `RunRecord`, etc.)
- `ArcFrontendService` proxy (JSON-RPC to backend)
- `ArcServiceImpl` (backend CLI/daemon caller)
- Command registrations

This means `arc-core` must be the LAST extension removed, after its protocol and
service types are properly represented in `packages/arc-extension` and the Python daemon.

---

## Current State

| Extension | Status |
|-----------|--------|
| `arc-adapters` | ✅ Ported into arc-extension and removed from browser app deps; source still present for rollback until browser smoke |
| `arc-audit` | ✅ Static stub removed from browser app deps; per-run audit verification lives in canonical Runs tab |
| `arc-arena` | 🗑️ ARCHIVE CANDIDATE — out of v0.1 scope; source retained outside workspace |
| `arc-context` | ✅ Old-core context-pack viewer removed from browser app deps; port later only if context-pack UX returns to release scope |
| `arc-core` | ✅ Removed from browser app deps; canonical extension owns service/protocol/status/welcome/prefs |
| `arc-event-stream` | ✅ Ported into arc-extension and removed from browser app deps; source still present for rollback until browser smoke |
| `arc-health` | ✅ Ported into arc-extension and removed from browser app deps |
| `arc-product` | ✅ Branding shell removed from browser app deps; canonical extension owns ARC Studio identity |
| `arc-runs` | ✅ Removed from browser app deps; run timeline, chat launch controls, and run diff UI/service are canonical |
| `arc-schemas` | ✅ Old-core schema inspector removed from browser app deps; port later only if schema UI returns to release scope |
| `arc-settings` | ✅ Safe prefs ported into arc-extension and removed from browser app deps |
| `arc-workflows` | ✅ Ported into arc-extension and removed from browser app deps; source still present for rollback until browser smoke |
