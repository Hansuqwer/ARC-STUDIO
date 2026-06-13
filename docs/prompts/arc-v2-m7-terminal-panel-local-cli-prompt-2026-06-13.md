# ARC v2 M7 / Sprint 6 — Terminal Panel in Pixels Local CLI Prompt

## Context

Branch: `arc-v2/sprint-1-protocol-bridge`  
Baseline: after `ed110a43`; can run in parallel with M5/M6 if render-file merge
conflicts are avoided.  
Plan: `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`

M7 renders `arc-terminal::TerminalSession` as a native terminal panel in the gpui
shell/dock, with PTY input/output and explicit lifecycle states.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m5-m7-macos-implementation-plan.md`
4. `rust/arc-terminal/src/lib.rs`
5. `rust/arc-shell/src/render_gpui.rs`
6. `rust/arc-dock/src/event_stream.rs` for the K4 panel pattern
7. alacritty terminal event-loop message docs:
   `https://docs.rs/alacritty_terminal/0.25.0/alacritty_terminal/event_loop/enum.Msg.html`

## Deliverable

A terminal panel that proves PTY → terminal model → gpui render in pixels.

## Work package A — terminal controller

Create a framework-free controller, preferably:

```text
rust/arc-shell/src/terminal_controller.rs
```

Required state/operations:

- optional `TerminalSession`
- visible grid cache
- focused state
- spawn/default shell config
- write bytes/key text
- resize
- pump pending events
- exit code / stopped / error state
- restart action
- bounded scrollback or bounded cached rows

Tests:

- starts empty/stopped
- spawn failure yields explicit error state
- bounded cache does not grow unbounded
- resize updates dimensions
- exit/stopped state preserved
- restart clears stopped/error state

## Work package B — gpui terminal render

Create a cfg-gated render module or isolated section, preferably:

```text
rust/arc-shell/src/render_terminal_gpui.rs
```

Rules:

- Import framework items only through `arc_ui::kit::*`.
- Do not reach into alacritty internals from render code; use `TerminalSession`
  and the terminal controller.
- Keep terminal model/controller APIs framework-free.

Required render behavior:

- terminal rows in monospace fixed-width discipline
- focus marker
- keyboard input → PTY
- PTY output → visible grid repaint
- resize event/command → PTY resize
- stopped/exited/error state visible
- restart action
- NO_COLOR/high-contrast visible switch

## Work package C — accessibility/security

Extend `rust/arc-ui/src/a11y.rs` with semantic nodes for:

- terminal panel label
- focused terminal state
- current line or selected-line summary
- stopped/error state

Security/reliability requirements:

- terminal actions are deterministic;
- no LLM allow/deny decisions;
- destructive process actions should be explicit/confirmable when surfaced;
- terminal output buffers are bounded;
- no secrets redaction claims unless a deterministic producer exists.

## M4 evidence

Record under `reports/evidence/`:

1. terminal panel opens;
2. run `echo arc-marker` and verify visible output;
3. resize panel/window and verify grid adapts;
4. exit shell/process and verify stopped/exit state;
5. restart terminal and verify fresh prompt/output.

## Verification

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-terminal -p arc-shell
cargo clippy -p arc-terminal -p arc-shell --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

If macOS PTY behavior differs from Linux tests, record the exact command/output;
do not generalize Linux evidence to macOS or vice versa.

## Handback

Update `docs/planning/arc-v2-baton.md` with commands/evidence paths and remaining
M7 gaps.
