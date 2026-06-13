# ARC v2 M11 — UX States + Interaction Polish Local CLI Prompt

## Goal

Close macOS UX-state and interaction gaps. Do not start Linux.

## Read first

- `AGENTS.md`, `docs/planning/arc-v2-baton.md`
- `docs/planning/arc-v2-macos-100-percent-completion-plan.md`
- `docs/planning/arc-v2-macos-dod-gap-matrix.md`
- `rust/arc-shell/src/render_gpui.rs`, all controller files

## Required work

1. Keyboard routing audit: F6/Shift-F6 cycles all landmarks; each surface receives only its keys.
2. Explicit UX states: editor empty/dirty/saved/error; workspace loading/empty/error; search empty/no-results/rebuilding/error; terminal empty/running/spawn-error/exited/restarting; event stream fixture/live/degraded.
3. Command palette parity: major actions route same controller methods as direct UI.

## Verification

```bash
cd rust && cargo fmt --all --check
cargo test -p arc-shell -p arc-dock
cargo clippy -p arc-shell -p arc-dock --all-targets -- -D warnings
cd .. && bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

Update `docs/planning/arc-v2-baton.md` and add evidence under `reports/evidence/`.
