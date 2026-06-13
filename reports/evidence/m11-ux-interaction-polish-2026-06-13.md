# M11 — UX States + Interaction Polish Evidence

Date: 2026-06-13  
Baseline: `cd0a9b0`  
Status: **Prepared by Arena; pending M4 execution evidence**

This report template is ready for local CLI/M4 evidence. Arena cannot produce
pixel evidence or run Rust tests in this sandbox.

## Required evidence checklist

| Surface | Required UX states | Interaction proof | Evidence path/result |
|---|---|---|---|
| Shell chrome | focused landmark, command palette open/closed, daemon healthy/degraded | F6/Shift-F6 cycles all landmarks | PENDING |
| Command palette | empty query, results, disabled command, rejected command, closed | Ctrl+Shift+P, type, arrow, enter, escape | PENDING |
| Editor | empty, dirty, saved, open error, save error | type, select, copy/paste, undo/redo, save/reopen | PENDING |
| Workspace tree | loading, empty folder, scan error, watcher degraded, success | up/down, expand/collapse, enter opens file | PENDING |
| Search/index | empty query, no results, rebuilding, query error, success | query, result select, enter opens editor | PENDING |
| Event Stream | fixture fallback, live connected, daemon unreachable, stale/gap | fixture rows and live SSE use same `on_event` path | PENDING |
| Terminal | empty, running, spawn error, exited, restarting | type command, output, resize, exit, restart | PENDING |
| Status rail | healthy, degraded, stopped/circuit-open where applicable | live kill/degraded proof | PENDING |

## Commands to run locally

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-shell -p arc-dock
cargo clippy -p arc-shell -p arc-dock --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

## Evidence to add

- `reports/evidence/m11-ux-interaction-polish-2026-06-13.mov` or screenshots.
- Update this table with Pass/Fail and exact notes.
- Update `docs/planning/arc-v2-baton.md`.

## Current Arena result

Arena created this report template and ran only headless-safe doc/facade checks.
No M11 gate is closed by this file alone.
