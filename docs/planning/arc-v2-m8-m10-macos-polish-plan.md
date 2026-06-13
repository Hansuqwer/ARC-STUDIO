# ARC v2 — M8/M9/M10 macOS Native Polish Plan

Date: 2026-06-13 · Baseline: `b58c6a99` · Scope: macOS native polish before Linux.

## 0. Current baseline

M5/M6/M7 are Baseline Complete in pixels on the pinned M4:

- M5 Editor: visible editor panel with line numbers and scratch buffer.
- M6 Workspace: visible repository tree with selected row.
- M7 Terminal: visible terminal panel with default shell running.

Evidence: `reports/evidence/m5-m6-m7-panels-2026-06-13.png`.

This is not yet macOS native 100%. The baseline proves the surfaces render; the
next three phases make them usable, accessible, state-complete, and evidence-backed.

## 1. Research summary

### Editor polish research

The gpui 0.2.2 input example shows the correct path for a real editor: custom
input element, `window.handle_input(...)`, UTF-16 selection/marked range,
prepainted text layout, cursor/selection quads, mouse handlers, paste/copy/cut
actions, and candidate-window bounds from the last text layout. M8 should adapt
that pattern to ARC's multi-line `EditorController` rather than extending the
palette TypeBox hack.

Important source: `https://docs.rs/crate/gpui/0.2.2/source/examples/input.rs`.

### Workspace/search polish research

For large tree/search result lists, gpui 0.2.2 exposes `uniform_list(...)` for
virtualized fixed-height rows and `overflow_scroll()` for simple scroll regions.
M9 should use `uniform_list` for the workspace tree and search results once row
counts grow beyond the visible panel.

Sources:

- `https://docs.rs/crate/gpui/0.2.2/source/examples/uniform_list.rs`
- `https://docs.rs/crate/gpui/0.2.2/source/examples/scrollable.rs`

### Terminal polish research

`arc-terminal::TerminalSession` already wraps the alacritty event loop with
`write`, `resize`, `pump`, `grid_text`, `shutdown`, and exit tracking. The
underlying event-loop messages are `Input`, `Resize`, and `Shutdown`, so M10
should route keys through `TerminalController::write_*` and resize through
`TerminalController::resize`, never directly into alacritty internals from render
code.

Source: `https://docs.rs/alacritty_terminal/0.25.0/alacritty_terminal/event_loop/enum.Msg.html`.

## 2. Current gaps by surface

### M5 Editor baseline gaps

Current files:

- `rust/arc-shell/src/editor_controller.rs`
- `rust/arc-shell/src/render_editor_gpui.rs`
- `rust/arc-shell/src/render_gpui.rs`

Baseline limitations:

- Editor is visible but not yet the primary input target.
- No full multi-line editor input handler with real text layout bounds.
- No mouse selection/click placement.
- Clipboard operations not wired.
- Save/open flow exists in controller but not fully exercised in pixels.
- Editor a11y tree is still generic landmark-level, not editor-content aware.
- No large-file viewport evidence.

### M6 Workspace/Search baseline gaps

Current files:

- `rust/arc-shell/src/workspace_controller.rs`
- `rust/arc-shell/src/search_controller.rs`
- `rust/arc-shell/src/render_workspace_gpui.rs`

Baseline limitations:

- Tree is visible, but keyboard file-open workflow needs pixel proof.
- Search panel exists as helper, but not a polished visible workflow.
- Watcher update proof is not recorded in pixels.
- Search snippets/line locations are not yet rich enough for editor navigation.
- Tree/search a11y nodes are not expanded beyond generic landmarks.

### M7 Terminal baseline gaps

Current files:

- `rust/arc-shell/src/terminal_controller.rs`
- `rust/arc-shell/src/render_terminal_gpui.rs`

Baseline limitations:

- Terminal is running and visible, but key input routing to PTY needs proof.
- Resize behavior needs pixel proof.
- Exit/restart actions need explicit UI and evidence.
- Scrollback/copy/paste need bounded behavior.
- Terminal a11y is generic, not current-line/status aware.

## 3. M8 — Editor polish

Goal: make the editor a usable native text editor on macOS.

### Required implementation

1. Promote editor focus to first-class input routing:
   - when FocusRing region is `editor`, normal text keys mutate `EditorController`;
   - palette shortcuts still work globally;
   - terminal/workspace do not steal editor input.
2. Add a real multi-line editor input handler:
   - UTF-16 selection/marked text;
   - inline IME composition;
   - real `bounds_for_range` from line layout;
   - no floating IME window.
3. Add mouse interactions:
   - click to move cursor;
   - drag to select;
   - double-click word optional, not required for M8 if documented.
4. Add clipboard actions:
   - copy selected text;
   - cut selected text;
   - paste via normal transaction path.
5. Add save/open pixel workflow:
   - workspace-opened file loads into editor;
   - dirty indicator;
   - save clears dirty;
   - save error renders explicit error.
6. Add editor a11y semantics:
   - editor text area label/value/current line;
   - dirty/read-only/error state;
   - focused state.
7. Add large-file viewport sanity:
   - render bounded visible rows only;
   - no full-file row allocation in hot render path beyond controller's visible slice.

### Evidence

Commit evidence under `reports/evidence/`:

- `m8-editor-polish-YYYY-MM-DD.png` or `.mov` showing open/type/select/undo/save.
- Optional `m8-editor-ime-YYYY-MM-DD.png` for inline composition in editor.
- Notes in baton with exact commands.

### Verification

```bash
cd rust
cargo test -p arc-editor -p arc-shell
cargo clippy -p arc-editor -p arc-shell --all-targets -- -D warnings
```

## 4. M9 — Workspace/Search polish

Goal: make workspace tree/search a real editor workflow.

### Required implementation

1. Keyboard tree workflow:
   - up/down selection;
   - expand/collapse folder;
   - enter opens file into M8 editor;
   - selected/open file state visible.
2. Watcher pixel proof:
   - create file;
   - delete file;
   - update tree after debounce;
   - explicit degraded/error if watcher unavailable.
3. Search workflow:
   - palette command opens workspace search;
   - query updates results;
   - result row shows path + line/snippet where possible;
   - enter opens result in editor.
4. Redaction truth:
   - snippets must not show redacted secret lines;
   - if snippet producer cannot prove redaction, render path-only row instead of invented snippet.
5. Index state:
   - loading/empty/error/rebuilding/success states;
   - explicit rebuild command.
6. A11y semantics:
   - workspace tree/list row roles;
   - selected item label;
   - search field and result list labels.

### Evidence

Commit evidence under `reports/evidence/`:

- `m9-workspace-search-polish-YYYY-MM-DD.png` or `.mov` showing tree navigation,
  file open, watcher update, search, open result.

### Verification

```bash
cd rust
cargo test -p arc-workspace -p arc-index -p arc-shell
cargo clippy -p arc-workspace -p arc-index -p arc-shell --all-targets -- -D warnings
```

## 5. M10 — Terminal polish

Goal: make terminal panel usable and explicit under macOS.

### Required implementation

1. Focus/input routing:
   - when terminal is focused, printable keys write to PTY;
   - enter/backspace/tab/arrow escape sequences route correctly;
   - global shortcuts still work.
2. Output/repaint:
   - terminal output triggers repaint without relying only on incidental shell renders;
   - bounded visible grid/scrollback.
3. Resize:
   - panel/window resize maps to `TerminalController::resize`;
   - grid dimensions visible and correct.
4. Lifecycle:
   - stopped/exited state visible;
   - spawn error visible;
   - restart action.
5. Clipboard:
   - copy visible selection if implemented;
   - paste writes to PTY.
6. A11y:
   - terminal panel label;
   - focused/running/exited status;
   - current line summary.

### Evidence

Commit evidence under `reports/evidence/`:

- `m10-terminal-polish-YYYY-MM-DD.png` or `.mov` showing terminal input,
  `echo arc-marker`, resize, exit, restart.

### Verification

```bash
cd rust
cargo test -p arc-terminal -p arc-shell
cargo clippy -p arc-terminal -p arc-shell --all-targets -- -D warnings
```

## 6. Cross-cutting DoD gates for all three phases

For each phase, record evidence for:

1. UX states: loading/empty/error/degraded/success where relevant.
2. Accessibility: keyboard reachable, visible focus, a11y labels, VoiceOver smoke.
3. Parity: controller tests and pixel path use the same model functions.
4. Tests: crate-specific unit tests plus `arc-shell` tests.
5. Performance: bounded rows/viewport/scrollback; no unbounded hot-path allocation.
6. Security: deterministic behavior; no LLM allow/deny; destructive process actions explicit.
7. Reliability: error states and restart/retry/cancel where applicable.
8. Docs: baton/evidence updated; banned-claims clean.

## 7. Recommended commit sequence

1. `m8-editor-polish-controller`: controller refinements + tests.
2. `m8-editor-polish-pixels`: render/input/a11y + M4 evidence.
3. `m9-workspace-search-polish-controller`: tree/search/index refinements + tests.
4. `m9-workspace-search-polish-pixels`: render/a11y/watcher/search evidence.
5. `m10-terminal-polish-controller`: terminal lifecycle/input/cache refinements + tests.
6. `m10-terminal-polish-pixels`: render/input/resize/restart evidence.
7. `m8-m10-baton`: final baton/report update.

Linux remains deferred until these macOS polish phases are complete.
