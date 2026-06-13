# ARC v2 M6 / Sprint 5 — Workspace + File Open + Search Local CLI Prompt

## Context

Branch: `arc-v2/sprint-1-protocol-bridge`  
Baseline: after `ed110a43` and preferably after the M5 editor-open API exists.  
Plan: `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`

M6 makes the Workspace tree landmark real, wires file-open into the M5 editor,
and exposes local search/index results.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`
4. `rust/arc-workspace/src/{lib.rs,tree.rs,watcher.rs}`
5. `rust/arc-index/src/{lib.rs,search.rs,symbols.rs}`
6. `rust/arc-shell/src/render_gpui.rs`
7. M5 editor controller/open API once available
8. gpui list/scroll examples:
   - `https://docs.rs/crate/gpui/0.2.2/source/examples/uniform_list.rs`
   - `https://docs.rs/crate/gpui/0.2.2/source/examples/scrollable.rs`

## Deliverable

Render a real workspace tree, open files into the editor, and wire local
redaction-aware search/index.

## Work package A — workspace controller

Create a framework-free controller, preferably:

```text
rust/arc-shell/src/workspace_controller.rs
```

Required state/operations:

- workspace root path
- `WorktreeModel`
- flattened visible rows: depth, kind, path, label, expanded, selected
- keyboard selection movement
- expand/collapse folders
- enter on file returns an `OpenFile(path)` effect
- watcher events apply through the same model path as tests
- explicit loading/empty/error/degraded/success render states

Tests:

- flatten order and indentation
- selection clamps
- expand/collapse
- open-file effect
- watcher-create/delete path updates rows

## Work package B — search/index controller

Create a framework-free search controller, preferably:

```text
rust/arc-shell/src/search_controller.rs
```

Required state/operations:

- index root/open-or-rebuild
- explicit rebuild command
- query text
- result rows: file path, line/snippet/rank
- selected result
- enter returns `OpenFileAt(path, location)` or compatible editor-open effect
- redaction-aware snippets: no secret leakage

Tests:

- search returns deterministic rows
- redaction-safe snippets
- rebuild command explicit, not hidden side effect
- open result effect

## Work package C — gpui workspace/search render

Create a cfg-gated render module or isolated section, preferably:

```text
rust/arc-shell/src/render_workspace_gpui.rs
```

Rules:

- Import framework items only through `arc_ui::kit::*`.
- Prefer `uniform_list` for large tree/search lists.
- Do not put framework types in controller APIs.

Required render behavior:

- Workspace tree region is real, not placeholder.
- Up/down/enter/expand/collapse works by keyboard.
- File opens into M5 editor.
- Search command from palette opens search UI.
- Search result enter opens editor at target.
- NO_COLOR/high-contrast visible switch.

## Work package D — accessibility

Extend `rust/arc-ui/src/a11y.rs` with semantic nodes for:

- workspace tree/list
- selected row
- file/folder labels
- search field/results
- selected/opened result

The platform bridge should consume the semantic tree; do not make platform a11y
truth separate from `arc-ui`.

## M4 evidence

Record under `reports/evidence/`:

1. workspace tree renders;
2. open file from tree into editor;
3. create/delete file updates tree after watcher debounce;
4. search query shows results;
5. enter on search result opens editor;
6. a11y row labels smoke if tree/search a11y changed.

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

Run Python v1 gate if protocol/web surfaces are touched:

```bash
cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
```

## Handback

Update `docs/planning/arc-v2-baton.md` with commands/evidence paths and remaining
M6 gaps.
