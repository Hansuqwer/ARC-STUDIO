# ARC v2 M12 — Accessibility + IME + Theme Polish Local CLI Prompt

## Goal

Close macOS accessibility, IME, NO_COLOR, and high-contrast gaps. Do not start Linux.

## Read first

- `AGENTS.md`, `docs/planning/arc-v2-baton.md`
- `docs/planning/arc-v2-macos-g5-g6-protocol.md`
- `rust/arc-ui/src/a11y.rs`, `rust/arc-shell/src/a11y_macos.rs`
- All render_*_gpui.rs files

## Required work

1. VoiceOver: editor current line/dirty; workspace selected row; search field/results; terminal status; event stream rows.
2. IME: palette regression smoke; editor inline composition commit/cancel.
3. Theme: NO_COLOR and high-contrast evidence across editor/workspace/search/terminal/event stream.
4. A11y tree drift audit: `arc_ui::a11y` matches visible surfaces.

## Verification

```bash
cd rust && cargo fmt --all --check
cargo test -p arc-ui -p arc-shell
cargo clippy -p arc-ui -p arc-shell --all-targets -- -D warnings
cd .. && bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```
