# ARC v2 — M8/M9/M10 macOS Native Polish Deep Research Prompt

Use this prompt after M5/M6/M7 Baseline Complete (`b58c6a99`) when the owner wants
macOS native to reach 100% before starting Linux.

## Goal

Deep-research, plan, and implement the next macOS polish sequence:

1. **M8 — Editor polish**
2. **M9 — Workspace/Search polish**
3. **M10 — Terminal polish**

These are DoD-elevation phases for macOS native surfaces. Do not start Linux yet.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m8-m10-macos-polish-plan.md`
4. `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`
5. `rust/arc-shell/src/render_gpui.rs`
6. `rust/arc-shell/src/editor_controller.rs`
7. `rust/arc-shell/src/workspace_controller.rs`
8. `rust/arc-shell/src/search_controller.rs`
9. `rust/arc-shell/src/terminal_controller.rs`
10. `rust/arc-shell/src/render_editor_gpui.rs`
11. `rust/arc-shell/src/render_workspace_gpui.rs`
12. `rust/arc-shell/src/render_terminal_gpui.rs`
13. `rust/arc-ui/src/a11y.rs`
14. `reports/evidence/m5-m6-m7-panels-2026-06-13.png`

## Research checklist before editing

Use Context7/Vercel Grep if available; otherwise record that they are unavailable
and use docs.rs/GitHub source/local files.

Research:

- gpui input example for real text editing:
  `https://docs.rs/crate/gpui/0.2.2/source/examples/input.rs`
- gpui list/scroll virtualization:
  - `https://docs.rs/crate/gpui/0.2.2/source/examples/uniform_list.rs`
  - `https://docs.rs/crate/gpui/0.2.2/source/examples/scrollable.rs`
- alacritty event loop messages:
  `https://docs.rs/alacritty_terminal/0.25.0/alacritty_terminal/event_loop/enum.Msg.html`
- local ARC controller/render files listed above.

## Execution order

1. M8 Editor polish
2. M9 Workspace/Search polish
3. M10 Terminal polish

Rationale: M9 depends on real editor open/save. Terminal polish can proceed after
the core editor/workspace loop is solid.

## Verification before handback

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-shell -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock
cargo clippy -p arc-shell -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

Pixel evidence must be collected on the pinned M4 display only.

## Handback

Update `docs/planning/arc-v2-baton.md` and add evidence files under
`reports/evidence/`. Do not claim Polished Complete until all relevant DoD gates
have cited evidence.
