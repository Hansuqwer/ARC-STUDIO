# ARC v2 M9 — Workspace/Search Polish Local CLI Prompt

## Goal

Elevate M6 Workspace/Search from Baseline Complete to macOS-native polished
workflow. Do not start Linux.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m8-m10-macos-polish-plan.md`
4. `rust/arc-shell/src/workspace_controller.rs`
5. `rust/arc-shell/src/search_controller.rs`
6. `rust/arc-shell/src/render_workspace_gpui.rs`
7. `rust/arc-shell/src/render_gpui.rs`
8. `rust/arc-workspace/src/tree.rs`
9. `rust/arc-workspace/src/watcher.rs`
10. `rust/arc-index/src/search.rs`
11. gpui list/scroll examples:
    - `https://docs.rs/crate/gpui/0.2.2/source/uniform_list.rs` (or docs.rs source path under examples)
    - `https://docs.rs/crate/gpui/0.2.2/source/examples/scrollable.rs`

## Required work

- Keyboard tree workflow: up/down, expand/collapse, enter opens file into editor.
- Visible opened/selected file state.
- Watcher pixel proof: create/delete/rename or documented best supported subset.
- Search UI: query, loading/empty/error/success states, selected result.
- Search result opens in editor.
- Redaction-safe snippets or explicit path-only rows if snippet producer cannot prove redaction.
- Explicit index rebuild command/status.
- Extend `arc_ui::a11y` for workspace tree rows and search result rows.
- NO_COLOR/high-contrast workspace/search parity.

## Evidence

Capture M4 evidence under `reports/evidence/` showing:

1. tree keyboard navigation;
2. expand/collapse;
3. open file into editor;
4. watcher update after create/delete;
5. search query and result rows;
6. open search result;
7. VoiceOver tree/search row smoke.

## Verification

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-workspace -p arc-index -p arc-shell
cargo clippy -p arc-workspace -p arc-index -p arc-shell --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

## Handback

Update `docs/planning/arc-v2-baton.md` with commands and evidence paths.
