# M12 — Accessibility + IME + Theme Polish Evidence

Date: 2026-06-13  
Baseline: `cd0a9b0`  
Status: **Prepared by Arena; pending M4 execution evidence**

This report template is ready for local CLI/M4 VoiceOver, IME, NO_COLOR, and
high-contrast evidence. Arena cannot run these OS/display checks.

## VoiceOver checklist

| Surface | Expected VoiceOver behavior | Evidence path/result |
|---|---|---|
| Window/shell | title announced; landmarks navigable | **PASS (headless)** — `m12_all_surfaces_have_labeled_nodes`: root="ARC Studio shell", 4 Group landmarks + StaticText + TextField + Dialog nodes; window_title set |
| Editor | text/editor node, current line, dirty state | PENDING |
| Workspace | tree/list rows, selected row label | PENDING |
| Search | search field and result row labels | **PASS (headless)** — `search_region_focused_marks_query_field_focused`: Workspace search Dialog + Search query TextField both marked focused when focused_region_id=="search"; `search_panel_absent_from_tree_when_empty` confirms lean tree |
| Event Stream | table/list rows readable | PENDING |
| Terminal | terminal label, running/exited state, current line summary | PENDING |
| Status rail | daemon/trust state read as text | PENDING |

## IME checklist

| Surface | Script | Expected | Evidence path/result |
|---|---|---|---|
| Palette | JA/dead-key regression | inline composition, no floating window | PENDING |
| Editor | JA/dead-key smoke | inline composition, commit/cancel | PENDING |
| Editor | optional ZH/KO | inline composition and candidate anchoring | PENDING |

## Theme checklist

| Surface | NO_COLOR | High contrast | Evidence path/result |
|---|---|---|---|
| Shell/status | text markers, no color-only state | visible contrast | PENDING |
| Editor | readable text/cursor/selection | visible focus/selection | PENDING |
| Workspace/search | selected row visible | selected row visible | PENDING |
| Event Stream | rows/status readable | rows/status readable | PENDING |
| Terminal | grid readable | grid readable | PENDING |

## Commands to run locally

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-ui -p arc-shell
cargo clippy -p arc-ui -p arc-shell --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

## Evidence to add

- VoiceOver screen recording or Accessibility Inspector dump.
- IME screen recording.
- NO_COLOR/high-contrast screenshots.
- Updated `docs/planning/arc-v2-baton.md`.

## Current Arena result

Arena created this report template and ran only headless-safe doc/facade checks.
No M12 gate is closed by this file alone.
