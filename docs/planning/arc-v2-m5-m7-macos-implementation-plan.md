# ARC v2 — M5/M6/M7 macOS Implementation Plan

Date: 2026-06-13 · Branch: `arc-v2/sprint-1-protocol-bridge` · Baseline HEAD at sync: `ed110a43`

This file is the executed output of
`docs/prompts/arc-v2-m5-m7-deep-research-parallel-implementation-prompt-2026-06-13.md`.
It turns the next three recommended macOS phases into parallelizable local-CLI
work packets.

## 0. Current state

- Provisional framework: **gpui 0.2.2**.
- K1–K4 complete on macOS.
- macOS K3 is closed: G5 VoiceOver Pass, G6 IME Pass, G7 Bidi Pass.
- G8 sustainability recorded as Pass; criterion-#1 facade score still governs
  the selection (gpui 20/20 vs floem 18/20).
- `ed110a43` relocated the three pure render-gpui tests into headless
  `shell.rs`; `arc-shell` 11 and `arc-dock` 30 headless tests pass. The full
  framework test binary still hits a local `gpui_macros` SIGBUS on the M4, which
  is recorded as an environment/compile constraint rather than a logic-test
  failure.
- Remaining FINAL selection blockers stay outside this macOS feature wave:
  Linux session and Windows-gap decision.

## 1. Research summary

### gpui text input / editor pattern

The `gpui 0.2.2` input example is the closest upstream shape for M5. The relevant
pattern is:

- implement an input handler with UTF-16 selection/marked-range methods;
- implement a custom element whose `paint()` calls `window.handle_input(...)`;
- shape text during `prepaint()`;
- paint selection, marked-text underline, line text, and cursor;
- store last layout/bounds so IME candidate window coordinates can be computed.

Source: `https://docs.rs/crate/gpui/0.2.2/source/examples/input.rs`.

The K3 TypeBox implementation already proved this path for a single-line palette
query. M5 should generalize it to a multi-line editor element rather than invent a
second input stack.

### gpui list/scroll patterns

For Workspace/Search/Event rows, gpui 0.2.2 provides:

- `overflow_scroll()` for simple scroll containers.
- `uniform_list(...)` for virtualized fixed-height row lists.

Sources:

- `https://docs.rs/crate/gpui/0.2.2/source/examples/scrollable.rs`
- `https://docs.rs/crate/gpui/0.2.2/source/examples/uniform_list.rs`

M6 should prefer `uniform_list` for workspace/search rows once row counts can grow,
falling back to simple `overflow_scroll()` only for small bounded lists.

### Rope/editor model constraints

`ropey::Rope` gives O(log N) edit/query behavior, line/char conversions, slices,
and cheap clones for async save/index paths. Source:
`https://docs.rs/ropey/latest/ropey/struct.Rope.html`.

The existing `arc-editor::Buffer` already hides rope internals and exposes
char-index transactions, line access, undo/redo, and revisions. M5 should extend
around this API; do not leak Rope types into shell/render code.

### Terminal model constraints

`arc-terminal::TerminalSession` already wraps `alacritty_terminal` with
`write`, `resize`, `pump`, `grid_text`, and `wait_exit`. The underlying event loop
message API supports input, shutdown, and resize messages. Source:
`https://docs.rs/alacritty_terminal/0.25.0/alacritty_terminal/event_loop/enum.Msg.html`.

M7 should render `grid_text()` first, then add keyboard input and resize routing.
Do not bypass `TerminalSession` by reaching into alacritty internals from render
code.

## 2. Local file analysis

### `rust/arc-shell/src/render_gpui.rs`

Current renderer responsibilities:

- opens gpui window and focuses shell on open;
- renders four shell landmarks;
- owns palette/typebox IME state;
- attaches macOS a11y tree via `arc_ui::a11y` and `arc-shell::a11y_macos`;
- renders K4 Event Stream panel;
- drains optional live per-run SSE via channel into `EventStreamPanel::on_event`.

Risk: it is already large. M5/M6/M7 should not add all code inline. Prefer small
modules composed by `render_gpui.rs`.

### `rust/arc-ui/src/a11y.rs`

Current tree covers:

- shell landmarks;
- status rail;
- palette dialog/rows;
- typebox.

M5/M6/M7 must extend this framework-free tree for:

- editor text area / current line / dirty state;
- workspace tree/search result lists;
- terminal panel / current line or focused row summary.

### `rust/arc-editor`

Already implemented:

- `Buffer::from_text`, `line`, `slice`, `apply`, `undo`, `redo`, `revision`;
- atomic transaction validation;
- inline-completion provider trait stubs.

Missing for M5:

- file-open/save wrapper;
- editor viewport/cursor/selection state;
- mapping keyboard/edit operations to `Transaction`;
- render-facing line rows and dirty state.

### `rust/arc-workspace`

Already implemented:

- worktree model;
- tree state;
- debounced watcher.

Missing for M6:

- shell controller that binds selected path to editor open;
- render-facing flattened rows with indentation/expanded/selected state;
- command palette/search integration.

### `rust/arc-index`

Already implemented:

- search index and symbol store;
- redaction-aware indexing contract;
- rebuild/open-or-rebuild behavior.

Missing for M6:

- shell-side search session/controller;
- search-result row projection and enter-to-open wiring.

### `rust/arc-terminal`

Already implemented:

- PTY spawn;
- write/resize/shutdown;
- event pump;
- visible `grid_text()`;
- wait helpers.

Missing for M7:

- shell-side terminal panel controller;
- render-facing bounded grid/scrollback adapter;
- keyboard focus/input routing;
- restart/exit state actions.

## 3. Parallelization plan

Do not have multiple agents edit `render_gpui.rs` simultaneously. Parallelize by
new module/controller first, then compose.

| Workstream | Can run in parallel? | Primary files | Dependency |
|---|---:|---|---|
| M5-A editor controller/model | yes | `rust/arc-shell/src/editor_controller.rs`, maybe `rust/arc-editor/src/view.rs` | none |
| M5-B editor gpui render | after M5-A shape starts | `rust/arc-shell/src/render_editor_gpui.rs` | M5-A public API |
| M6-A workspace/search controllers | yes | `rust/arc-shell/src/workspace_controller.rs`, `rust/arc-shell/src/search_controller.rs` | editor open trait stub |
| M6-B workspace/search gpui render | after M6-A shape starts | `rust/arc-shell/src/render_workspace_gpui.rs` | M6-A public API |
| M7-A terminal controller | yes | `rust/arc-shell/src/terminal_controller.rs` | none |
| M7-B terminal gpui render | after M7-A shape starts | `rust/arc-shell/src/render_terminal_gpui.rs` | M7-A public API |
| Composition | no, serialize | `rust/arc-shell/src/render_gpui.rs`, `rust/arc-shell/src/lib.rs`, `Cargo.toml` | module APIs stabilized |
| A11y extension | can be one separate stream | `rust/arc-ui/src/a11y.rs` | API snapshots from M5/M6/M7 |

## 4. Phase M5 — Editor in pixels

### M5-A Headless controller

Suggested file: `rust/arc-shell/src/editor_controller.rs`.

Responsibilities:

- `EditorController { buffer, path, dirty, cursor, selection, viewport_start_line }`.
- `open_path(path) -> Result<Self, EditorOpenError>` using UTF-8 text loading.
- `save() -> Result<(), EditorSaveError>` writes a cheap snapshot to disk.
- `insert_text`, `delete_backward`, `delete_forward`, `move_left/right/up/down`,
  `page_up/down`, `home/end`, `undo`, `redo`.
- `visible_lines(height) -> Vec<EditorLineVm>` for render code.
- no gpui types, no blocking IO in render hot path.

Tests:

- open/save dirty transition;
- edit/undo/redo through `arc-editor::Transaction`;
- cursor movement clamps;
- viewport row projection stable;
- invalid path/error state explicit.

### M5-B gpui editor render

Suggested file: `rust/arc-shell/src/render_editor_gpui.rs`.

Responsibilities:

- import only `arc_ui::kit::*` for framework items;
- render visible lines, cursor, selection, dirty marker;
- use the existing TypeBox/InputHandler lessons but with a dedicated editor input
  handler and real bounds for candidate anchoring;
- route keyboard events to `EditorController`;
- notify/repaint only after state mutation;
- expose editor focused state to `arc_ui::a11y`.

M4 evidence:

- open a fixture file;
- type text;
- undo/redo;
- save;
- reopen or compare file contents;
- screenshot/recording under `reports/evidence/`.

## 5. Phase M6 — Workspace + open file + search/index

### M6-A Workspace/search controllers

Suggested files:

- `rust/arc-shell/src/workspace_controller.rs`
- `rust/arc-shell/src/search_controller.rs`

Responsibilities:

- bind workspace root to `WorktreeModel`;
- flatten visible tree rows with depth, expanded, selected, kind, path;
- keyboard navigation and expand/collapse;
- `enter` on file returns an `OpenFile(path)` effect for M5 editor;
- watcher events apply through `WorktreeModel` path;
- search session builds/rebuilds local `SearchIndex`, returns redaction-safe rows;
- `enter` on search result returns `OpenFileAt(path, line/char)` effect.

Tests:

- flatten order/indentation;
- selection clamps;
- expand/collapse state;
- open-file effect;
- search result opens target;
- redaction-safe snippet behavior.

### M6-B gpui workspace/search render

Suggested file: `rust/arc-shell/src/render_workspace_gpui.rs`.

Responsibilities:

- workspace landmark becomes a real tree/list;
- use `uniform_list` if rows can be large;
- render selected row, file/folder markers, dirty/open marker;
- command palette entry opens search;
- render search box/results and route enter to editor;
- extend a11y tree for tree/list rows and selected/opened file.

M4 evidence:

- tree renders;
- open file from tree into editor;
- create/delete file and watcher updates tree;
- search opens result in editor.

## 6. Phase M7 — Terminal panel in pixels

### M7-A Terminal controller

Suggested file: `rust/arc-shell/src/terminal_controller.rs`.

Responsibilities:

- own optional `TerminalSession`;
- spawn default shell or configured program;
- `write_key` / `write_bytes` routing;
- `resize(cols, rows)`;
- `pump()` + dirty flag;
- bounded scrollback or visible grid cache;
- stopped/exited/restart state.

Tests:

- controller starts in empty/stopped state;
- spawn failures render explicit error;
- resize calls through and updates dimensions;
- bounded scrollback does not grow unbounded;
- exit state preserved.

### M7-B gpui terminal render

Suggested file: `rust/arc-shell/src/render_terminal_gpui.rs`.

Responsibilities:

- render grid rows in a dock/panel using monospace fixed-width discipline;
- focused terminal receives keyboard input and writes bytes to PTY;
- periodically/driven by render pumps pending terminal events;
- render exit/restart controls;
- extend a11y tree with terminal panel/current-line summary.

M4 evidence:

- terminal opens;
- `echo arc-marker` appears;
- resize works;
- exit state renders;
- restart works.

## 7. Integration order

Recommended commits for local CLI:

1. `m5-editor-controller`: headless controller + tests.
2. `m5-editor-pixels`: gpui editor render + M4 evidence.
3. `m6-workspace-search-controller`: workspace/search controllers + tests.
4. `m6-workspace-search-pixels`: render + open-file/search evidence.
5. `m7-terminal-controller`: terminal controller + tests.
6. `m7-terminal-pixels`: render + PTY evidence.
7. `m5-m7-baton`: final baton/report update.

If running multiple local agents, assign 1, 3, and 5 first; serialize 2, 4, 6
where they touch `render_gpui.rs`.

## 8. Verification matrix

| Phase | Required commands | M4 evidence |
|---|---|---|
| M5 | `cargo test -p arc-editor -p arc-shell`; facade gate; clippy/fmt | open/type/undo/save/reopen |
| M6 | `cargo test -p arc-workspace -p arc-index -p arc-shell`; facade gate; clippy/fmt | tree/open/search/watch |
| M7 | `cargo test -p arc-terminal -p arc-shell`; facade gate; clippy/fmt | terminal echo/resize/exit/restart |

For any docs/planning updates:

```bash
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

For protocol/web/shared changes:

```bash
cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
```

## 9. Non-goals

- Do not reopen framework selection during M5–M7 unless a hard blocker appears.
- Do not delete the floem escape.
- Do not move framework imports outside `arc_ui::kit`/cfg-gated render modules.
- Do not claim Linux/Windows evidence from macOS or CI.
- Do not turn this into a broad roadmap rewrite; this is the next macOS feature wave only.
