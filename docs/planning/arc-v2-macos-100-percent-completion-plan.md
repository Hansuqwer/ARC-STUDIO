# ARC v2 — macOS Native Completion Plan (post-M10)

Date: 2026-06-13 · Branch: `arc-v2/sprint-1-protocol-bridge` · Baseline: `6578db8`

## 0. Current state

Baseline Complete through M10. K1–K4 + G5/G6/G7/G8 done. M5–M10 pixel evidence committed.
See `docs/planning/arc-v2-macos-evidence-ledger.md` for full evidence index.

## 1. Remaining macOS phases

| Phase | Name | DoD outcome |
|---|---|---|
| M11 | UX states + interaction polish | Every surface has explicit loading/empty/error/degraded/success states and keyboard routing |
| M12 | Accessibility + IME + theme polish | VoiceOver, inline IME, NO_COLOR, high-contrast evidence across all surfaces |
| M13 | macOS certification pass | Performance, bounded buffers, reliability, security, evidence ledger, final report |

## 2. Non-goals

- Do not begin Linux evidence in this phase set.
- Do not reopen framework selection unless a hard blocker appears.
- Do not remove the floem escape.

## 3. Verification

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock
cargo clippy -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```
