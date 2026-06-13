# ARC v2 — M5/M6/M7 Deep Research + Parallel Implementation Prompt

Use this prompt for the next macOS-native implementation wave after K1–K4.

## Goal

Plan and execute the next three macOS phases under the provisional `gpui 0.2.2`
selection:

| Phase | Name | Goal |
|---|---|---|
| M5 / Sprint 4 | Editor in pixels | Turn `arc-editor::Buffer` into the real gpui editor surface. |
| M6 / Sprint 5 | Workspace + file open + search/index | Render the workspace tree, open files into the editor, and wire local search/index. |
| M7 / Sprint 6 | Terminal panel in pixels | Render `arc-terminal::TerminalSession` as a native terminal panel with PTY input/output. |

The work must preserve the v2 architecture: ARC-owned model/state crates remain
framework-free; gpui code is cfg-gated and imports the framework only through
`arc_ui::kit::*`.

## Read first

Read, in order:

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-kit-implementation-plan.md`
4. `docs/planning/arc-v2-macos-g5-g6-protocol.md`
5. `rust/arc-shell/src/render_gpui.rs`
6. `rust/arc-ui/src/a11y.rs`
7. `rust/arc-editor/src/{lib.rs,buffer.rs,completion.rs}`
8. `rust/arc-workspace/src/{lib.rs,tree.rs,watcher.rs}`
9. `rust/arc-index/src/{lib.rs,search.rs,symbols.rs}`
10. `rust/arc-terminal/src/lib.rs`
11. `rust/arc-dock/src/event_stream.rs`
12. `reports/spike-gpui.json`
13. `reports/evidence/k3-gpui-macos-evidence.json`

Verify lineage:

```bash
git fetch origin arc-v2/sprint-1-protocol-bridge
git log --oneline -8 origin/arc-v2/sprint-1-protocol-bridge
```

Expected current HEAD at time of writing: `ed110a43` (or newer), with K1–K4,
G5/G6/G7/G8 closed on macOS and gpui render pure-logic tests relocated to
headless `shell.rs` because the full framework test binary hits a local
`gpui_macros` SIGBUS on the M4.

## Mandatory research before editing

Use all available research tools before changing code. If Context7 or Vercel
Grep are unavailable, state that explicitly in the handback and use docs.rs,
GitHub source, local code, and web search instead.

Research topics:

1. gpui text input/editor pattern:
   - `InputHandler`
   - `ElementInputHandler`
   - custom `Element` `prepaint`/`paint`
   - cursor/selection painting
   - marked text / IME underline
   - source: `https://docs.rs/crate/gpui/0.2.2/source/examples/input.rs`
2. gpui list/scroll patterns:
   - `uniform_list`
   - `overflow_scroll`
   - sources:
     - `https://docs.rs/crate/gpui/0.2.2/source/examples/uniform_list.rs`
     - `https://docs.rs/crate/gpui/0.2.2/source/examples/scrollable.rs`
3. Rope/editor model constraints:
   - `ropey::Rope` line/char queries, slicing, cheap clones, huge-file behavior
   - source: `https://docs.rs/ropey/latest/ropey/struct.Rope.html`
4. Terminal model constraints:
   - `alacritty_terminal::event_loop::Msg::{Input, Resize, Shutdown}`
   - source: `https://docs.rs/alacritty_terminal/0.25.0/alacritty_terminal/event_loop/enum.Msg.html`
5. Local ARC crates listed above.

## Parallelization rule

Do not let three agents edit the same gpui render file at once. Parallelize by
file/module boundaries first, then compose:

- Headless model/view-model work can run in parallel in the framework-free crates.
- Pixel work should be split into small gpui adapter modules and composed in
  `render_gpui.rs` only after each module is independently green.
- Avoid direct `gpui::` references in comments outside `arc-ui`; the facade gate
  greps comments as well as code.

Suggested module boundaries:

```text
rust/arc-shell/src/editor_controller.rs        # framework-free editor state/file IO adapter
rust/arc-shell/src/workspace_controller.rs     # framework-free workspace/search open controller
rust/arc-shell/src/terminal_controller.rs      # framework-free terminal panel state adapter
rust/arc-shell/src/render_editor_gpui.rs       # cfg(feature="framework-gpui"), imports arc_ui::kit::*
rust/arc-shell/src/render_workspace_gpui.rs    # cfg(feature="framework-gpui"), imports arc_ui::kit::*
rust/arc-shell/src/render_terminal_gpui.rs     # cfg(feature="framework-gpui"), imports arc_ui::kit::*
```

If the operator chooses not to split files, still use the same conceptual
boundaries in separate commits to minimize merge/review risk.

## Phase M5 — Editor in pixels

Implement the editor first. M6 file-open depends on the editor open API.

Required behavior:

- Create/open a text buffer from disk.
- Render line text in the Editor landmark.
- Keyboard edit path: insert chars, backspace/delete, arrows, home/end, page up/down.
- Undo/redo via `arc-editor::Transaction`.
- Save dirty buffer to disk; dirty indicator clears on success.
- Inline IME composition uses the proven `InputHandler`/marked-text pattern.
- Accessibility tree exposes the editor as a text/editor node with focused state
  and current line/value summary.
- NO_COLOR/high-contrast visibly affect the editor region.

Evidence:

- `arc-editor` tests pass.
- `arc-shell` headless tests pass.
- facade gate passes.
- M4 pixel proof: open file → type → undo/redo → save → reopen/verify.

## Phase M6 — Workspace + file open + search/index

Start model-side work in parallel with M5, but do not wire pixel file-open until
M5 exposes an editor open API.

Required behavior:

- Render workspace tree in the Workspace tree landmark.
- Keyboard navigation: up/down, expand/collapse, enter opens file.
- Watcher updates apply through the same `WorktreeModel` path as tests.
- Search command opens a search UI backed by `arc-index::SearchIndex`.
- Search result enter opens the target file in M5 editor.
- Redaction rules remain enforced before snippets/index bodies are rendered.
- Accessibility tree exposes tree/list rows and selected/opened file labels.

Evidence:

- `arc-workspace` tests pass.
- `arc-index` tests pass.
- `arc-shell` tests pass.
- facade gate passes.
- M4 pixel proof: tree renders, open file from tree, create/delete updates tree,
  search result opens in editor.

## Phase M7 — Terminal panel in pixels

Can proceed in parallel after K4 because it uses the dock/panel pattern, but
avoid merge conflicts with M5/M6 by isolating terminal render code.

Required behavior:

- Render `arc-terminal::TerminalSession::grid_text()` in a terminal dock/panel.
- Focused terminal receives keyboard input and writes bytes to the PTY.
- PTY output pumps into visible grid rows.
- Resize path calls `TerminalSession::resize`.
- Exit/kill state renders explicitly; restart action available.
- Scrollback is bounded; no unbounded row accumulation.
- Accessibility tree exposes terminal panel label and current/selected line
  summary.

Evidence:

- `arc-terminal` tests pass.
- `arc-shell` tests pass.
- facade gate passes.
- M4 pixel proof: terminal opens, `echo arc-marker` appears, resize works, exit
  state renders, restart works.

## Verification gates

For Rust changes:

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-shell -p arc-dock
cargo clippy --workspace --all-targets -- -D warnings
```

If `framework-gpui` test binaries hit the known local `gpui_macros` SIGBUS,
record it honestly and keep pure logic tests headless, as in `ed110a43`.

For facade:

```bash
bash scripts/check-arc-ui-facade.sh
```

For docs/planning:

```bash
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

For Python v1 touch points:

```bash
cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
```

## Handback

At handback:

1. Update `docs/planning/arc-v2-baton.md`.
2. State exact commands run and outcomes.
3. Do not claim pixel evidence unless run on the M4 display.
4. If Arena produced commits, provide a git bundle.
