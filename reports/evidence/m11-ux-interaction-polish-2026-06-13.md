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
| Command palette | empty query, results, disabled command, rejected command, closed | Ctrl+Shift+P, type, arrow, enter, escape | **PASS** — `m11-palette-select-all-2026-06-13.png`: Ctrl+Shift+P opens overlay, single-char typing (no double), Cmd+A highlights query + announces `selected query: dvwvw`; fixed double-type (IME path was duplicated by `palette_key`) and added query select-all |
| Editor | empty, dirty, saved, open error, save error | type, select, copy/paste, undo/redo, save/reopen | PENDING |
| Workspace tree | loading, empty folder, scan error, watcher degraded, success | up/down, expand/collapse, enter opens file | **PASS** — `m11-workspace-keyboard-nav-2026-06-13.png`: F6→Workspace tree, docs+audit expanded, audit row selected (blue), Enter on `accessibility-audit.md` → editor title + real content; selection bounds and collapse confirmed by +3 tests |
| Search/index | empty query, no results, rebuilding, query error, success | query, result select, enter opens editor | **PASS** — `m11-search-results-2026-06-13.png`: F6→Search (focused), query `audit` → 20 results with path+snippet; index_workspace on startup; redact_for_index applied (secrets excluded) |
| Event Stream | fixture fallback, live connected, daemon unreachable, stale/gap | fixture rows and live SSE use same `on_event` path | **PASS (fixture path)** — `m11-event-stream-fixture-2026-06-13.png`: header `ARC dock · Event Stream — ready (source: daemon.run_events)`, 18 fixture rows (TOOL_CALL_START→RUN_COMPLETED), footer `18 rows \| 0 dropped \| source: daemon.run_events`; live SSE path uses same `EventStreamPanel::on_event` (K4 evidence); event dock moved into dock column so it is always visible |
| Terminal | empty, running, spawn error, exited, restarting | type command, output, resize, exit, restart | **PASS** — `m11-terminal-exited-2026-06-13.png`: `exited (0)` state; `m11-terminal-restarted-2026-06-13.png`: `running` after F5 restart, announce `terminal: restarted`; running state in `m11-terminal-echo-2026-06-13.png` |
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
