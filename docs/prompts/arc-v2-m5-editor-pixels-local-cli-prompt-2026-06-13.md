# ARC v2 M5 / Sprint 4 — Editor in Pixels Local CLI Prompt

## Context

Branch: `arc-v2/sprint-1-protocol-bridge`  
Baseline: after `ed110a43`  
Plan: `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`

K1–K4 are complete on macOS. gpui 0.2.2 remains the provisional framework.
M5 turns `arc-editor::Buffer` into the real editor surface in the gpui shell.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`
4. `rust/arc-editor/src/{lib.rs,buffer.rs,completion.rs}`
5. `rust/arc-shell/src/render_gpui.rs`
6. `rust/arc-ui/src/a11y.rs`
7. gpui input example: `https://docs.rs/crate/gpui/0.2.2/source/examples/input.rs`
8. ropey docs: `https://docs.rs/ropey/latest/ropey/struct.Rope.html`

## Deliverable

Build the editor landmark into a real pixel editor.

## Work package A — headless editor controller

Create a framework-free controller, preferably:

```text
rust/arc-shell/src/editor_controller.rs
```

Required state:

- current `arc_editor::Buffer`
- optional file path
- dirty flag
- cursor char index
- selection range
- viewport start line
- explicit loading/error/empty/success states where user-visible

Required operations:

- open text file from path
- save to path
- insert text
- delete backward/forward
- move left/right/up/down
- home/end
- page up/down
- undo/redo using `arc-editor::Transaction`
- visible line projection for render code

Add headless tests for all operations above.

## Work package B — gpui editor render

Create a cfg-gated render module or isolated section, preferably:

```text
rust/arc-shell/src/render_editor_gpui.rs
```

Rules:

- Import framework items only through `arc_ui::kit::*`.
- Avoid `gpui::` text in comments outside `arc-ui`; facade script greps comments.
- Keep `arc-editor` and controller APIs framework-free.

Required render behavior:

- editor line text
- cursor
- selection
- dirty marker
- focus marker
- inline IME composition using the proven input-handler pattern
- NO_COLOR/high-contrast visible switch

## Work package C — accessibility

Extend `rust/arc-ui/src/a11y.rs` so the editor is represented as a semantic
text/editor node with:

- label: `Editor`
- focused state
- current line / dirty summary
- typeable text area role/value where practical

Update macOS bridge only as needed; the semantic truth must stay in `arc-ui`.

## M4 evidence

On M4, record evidence under `reports/evidence/`:

1. open a fixture file;
2. type visible text;
3. undo/redo;
4. save;
5. reopen or compare file contents;
6. IME inline smoke if editor input handler changed;
7. NO_COLOR/high-contrast visual check if editor colors changed.

## Verification

Run at minimum:

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-editor -p arc-shell
cargo clippy -p arc-editor -p arc-shell --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

If `framework-gpui` test binary hits the known M4 `gpui_macros` SIGBUS, record it
honestly and ensure pure logic tests run headless.

## Handback

Update `docs/planning/arc-v2-baton.md` with exact commands, evidence paths, and
remaining M5 gaps. Commit only when the owner expects CLI commits; Arena requires
a bundle if committing from the sandbox.
