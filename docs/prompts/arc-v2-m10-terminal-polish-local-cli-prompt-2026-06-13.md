# ARC v2 M10 — Terminal Polish Local CLI Prompt

## Goal

Elevate M7 Terminal from Baseline Complete to macOS-native polished terminal
behavior. Do not start Linux.

## Read first

1. `AGENTS.md`
2. `docs/planning/arc-v2-baton.md`
3. `docs/planning/arc-v2-m8-m10-macos-polish-plan.md`
4. `rust/arc-shell/src/terminal_controller.rs`
5. `rust/arc-shell/src/render_terminal_gpui.rs`
6. `rust/arc-shell/src/render_gpui.rs`
7. `rust/arc-terminal/src/lib.rs`
8. alacritty event-loop message docs:
   `https://docs.rs/alacritty_terminal/0.25.0/alacritty_terminal/event_loop/enum.Msg.html`

## Required work

- Focused terminal receives printable keys and writes to PTY.
- Enter/backspace/tab/arrows route as correct bytes/sequences.
- Paste writes to PTY.
- Output triggers repaint without relying on incidental shell rerenders.
- Bounded scrollback/grid cache.
- Resize maps to `TerminalController::resize` and visible dimensions update.
- Exit/stopped/error states visible.
- Restart terminal action.
- Extend `arc_ui::a11y` for terminal panel status/current line.
- NO_COLOR/high-contrast terminal parity.

## Evidence

Capture M4 evidence under `reports/evidence/` showing:

1. terminal starts;
2. `echo arc-marker` appears;
3. resize updates visible dimensions/grid;
4. exit state renders;
5. restart returns to running state;
6. VoiceOver terminal label/status smoke.

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

## Handback

Update `docs/planning/arc-v2-baton.md` with commands and evidence paths.
