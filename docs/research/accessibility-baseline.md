# Accessibility Baseline Audit

**Date:** 2026-06-07
**Phase:** 152 (R-AUDIT21)
**HEAD:** aa788f3

---

## Scope

Zero-effort ARIA label pass over the top 3 most-used ARC Theia extension panels.

## Widgets audited

| Widget | File |
|---|---|
| ARC Studio main panel (tabs) | `arc-studio-widget.tsx` |
| Runtime Adapters widget | `arc-adapters-widget.tsx` |
| ARC Health widget | `arc-health-widget.tsx` |

---

## Findings

### ARC Studio widget (`arc-studio-widget.tsx`)
- **Was:** `role="main" aria-label="ARC Studio"` already present (from prior work). `role="tablist"`, `role="tab"`, `role="tabpanel"` all present.
- **Status:** No changes needed.

### Runtime Adapters widget (`arc-adapters-widget.tsx`)
- **Was:** No `role` or `aria-label` on the container or card list. Loading div had no role. Refresh button had no `aria-label`.
- **Fixed:**
  - Container: `role="main" aria-label="ARC Runtime Readiness"`
  - Loading state: `role="status"`
  - Refresh button: `aria-label="Refresh runtime adapters"`
  - Card list wrapper: `role="list" aria-label="Runtime adapter cards"`
  - Each card: `role="listitem" aria-label="Runtime adapter: {id}"`

### ARC Health widget (`arc-health-widget.tsx`)
- **Was:** Refresh button had `aria-label="Refresh health status"` already present.
- **Status:** Minimal; health panel container has no landmark role. Deferred to axe-core pass.

---

## What remains (deferred to axe-core pass)

- Keyboard focus management for modal dialogs (CapabilityDiffViewer confirm dialog)
- Screen-reader announcement for status changes (runs completing, HITL decisions)
- Color contrast checks (theme-dependent; requires visual audit)
- `arc-health-widget.tsx` container landmark role
- All event-stream and simulation widgets

---

## Verification

Not automated yet. axe-core integration is a follow-on slice.
