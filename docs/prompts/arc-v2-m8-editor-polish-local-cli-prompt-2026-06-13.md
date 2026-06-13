# ARC v2 M8 — Editor Polish Local CLI Prompt

## Goal

Elevate M5 Editor from Baseline Complete to macOS-native polished behavior.
Do not start Linux.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m8-m10-macos-polish-plan.md`
4. `rust/arc-shell/src/editor_controller.rs`
5. `rust/arc-shell/src/render_editor_gpui.rs`
6. `rust/arc-shell/src/render_gpui.rs`
7. `rust/arc-editor/src/buffer.rs`
8. `rust/arc-ui/src/a11y.rs`
9. gpui input example: `https://docs.rs/crate/gpui/0.2.2/source/examples/input.rs`

## Required work

- Route editor focus keyboard input into `EditorController`.
- Implement/finish multi-line editor input handling with inline IME.
- Add mouse click/drag selection.
- Add copy/cut/paste through deterministic edit transactions.
- Wire file open from workspace and save-to-disk workflow.
- Render dirty/save/error states.
- Extend `arc_ui::a11y` for editor text area/current line/dirty state.
- Prove NO_COLOR/high-contrast editor parity.
- Keep controller/model framework-free.

## Evidence

Capture M4 evidence under `reports/evidence/` showing:

1. open file;
2. type text;
3. select text;
4. copy/paste or cut/paste;
5. undo/redo;
6. save;
7. reopen/verify contents;
8. VoiceOver editor smoke;
9. editor inline IME smoke if input handler changed.

## Verification

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-editor -p arc-shell
cargo clippy -p arc-editor -p arc-shell --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

## Handback

Update `docs/planning/arc-v2-baton.md` with commands and evidence paths.
