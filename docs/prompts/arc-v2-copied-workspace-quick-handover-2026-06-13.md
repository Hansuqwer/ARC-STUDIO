# ARC v2 — Quick Handover Prompt for Copied Workspace

Use this when handing a copied Arena/local workspace to another agent.

## 0. First actions

```bash
git status --short --branch
git log --oneline -10
```

Expected current remote baseline at time of this handover:

- Branch: `arc-v2/sprint-1-protocol-bridge`
- HEAD: `b58c6a99`
- Recent commits:
  - `b58c6a99` — M5/M6/M7 wired into gpui shell; pixel evidence on M4; 83 tests pass
  - `e1406d80` — Arena M5/M6/M7 scaffolds copied/fixed; controllers + render helpers
  - `ed110a43` — render-gpui pure logic tests relocated headless; 11 arc-shell + 30 arc-dock pass
  - `4e04bcde` — G6 IME Pass

## 1. Read governance and baton first

Read in order:

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-kit-implementation-plan.md`
4. `docs/planning/arc-v2-sprint-3-final-adjudication.md`
5. `docs/planning/arc-v2-sprint-3-provisional-ranking-memo.md`

Key state:

- `gpui 0.2.2` is the provisional framework selection.
- macOS K1–K4 are done.
- macOS K3 gates are closed: G5 VoiceOver Pass, G6 IME Pass, G7 Bidi Pass.
- G8 sustainability is recorded.
- M5/M6/M7 are Baseline Complete in pixels on the M4.
- Remaining FINAL selection blockers: Linux session + Windows-gap decision.

## 2. Read M5/M6/M7 planning and prompts

Read next:

1. `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`
2. `docs/prompts/arc-v2-m5-m7-deep-research-parallel-implementation-prompt-2026-06-13.md`
3. `docs/prompts/arc-v2-m5-editor-pixels-local-cli-prompt-2026-06-13.md`
4. `docs/prompts/arc-v2-m6-workspace-search-local-cli-prompt-2026-06-13.md`
5. `docs/prompts/arc-v2-m7-terminal-panel-local-cli-prompt-2026-06-13.md`

## 3. Read implementation files

### Core shell/render integration

1. `rust/arc-shell/Cargo.toml`
2. `rust/arc-shell/src/lib.rs`
3. `rust/arc-shell/src/render_gpui.rs`
4. `rust/arc-ui/src/a11y.rs`
5. `rust/arc-shell/src/a11y_macos.rs`

### M5 editor

1. `rust/arc-shell/src/editor_controller.rs`
2. `rust/arc-shell/src/render_editor_gpui.rs`
3. `rust/arc-editor/src/lib.rs`
4. `rust/arc-editor/src/buffer.rs`
5. `rust/arc-editor/src/completion.rs`

### M6 workspace/search

1. `rust/arc-shell/src/workspace_controller.rs`
2. `rust/arc-shell/src/search_controller.rs`
3. `rust/arc-shell/src/render_workspace_gpui.rs`
4. `rust/arc-workspace/src/lib.rs`
5. `rust/arc-workspace/src/tree.rs`
6. `rust/arc-workspace/src/watcher.rs`
7. `rust/arc-index/src/lib.rs`
8. `rust/arc-index/src/search.rs`
9. `rust/arc-index/src/symbols.rs`

### M7 terminal

1. `rust/arc-shell/src/terminal_controller.rs`
2. `rust/arc-shell/src/render_terminal_gpui.rs`
3. `rust/arc-terminal/src/lib.rs`

### K4 dock/event stream

1. `rust/arc-dock/src/event_stream.rs`
2. `rust/arc-dock/src/lib.rs`

## 4. Read evidence/report files

1. `reports/spike-gpui.json`
2. `reports/evidence/k3-gpui-macos-evidence.json`
3. `reports/evidence/g6-ime-ja-screenshot-2026-06-13.png`
4. `reports/spike-gpui-bidi.png`
5. `reports/b1-cold-start.json`
6. `reports/evidence/m5-m6-m7-panels-2026-06-13.png`

## 5. Verification commands

For the current macOS baseline, local CLI reported 83 tests pass, clippy clean,
facade clean. Re-run if changing code:

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-shell -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock
cargo clippy -p arc-shell -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

If a framework test binary hits the known M4 `gpui_macros` SIGBUS, record it
honestly; pure render logic tests are headless in `shell.rs` and pass.

## 6. Remaining FINAL-selection work

1. Linux session on owner hardware:
   - G1–G4 sanity
   - Orca a11y
   - fcitx5/ibus IME
2. Windows-gap decision per os-sequencing doc.

## 7. Constraints

- Native-only v2: no Electron/WebView/Tauri fallback.
- Additive protocol only.
- No framework imports outside `arc-ui`, cfg-gated render modules, and spikes.
- Use `arc_ui::kit::*` inside cfg-gated gpui render modules.
- Do not overclaim: pixel evidence only from the M4 display.
- Keep floem escape in-tree.
- Provide a git bundle if Arena commits are used and cannot be pushed directly.
