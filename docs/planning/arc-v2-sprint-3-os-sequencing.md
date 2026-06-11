# ARC v2 Sprint-3 — OS sequencing plan

Prepared 2026-06-11. This documents the multi-OS spike execution order,
claims policy, and the selection-gating consequence of partial coverage.

## Tracks

| Track | Status | Scope |
|---|---|---|
| macOS spike (now, CLI's lane) | In progress | Full G1–G4 + G7 + macOS G5 (VoiceOver) + G6 (JA/ZH/KO + dead keys) per candidate → `spike-<candidate>.json` |
| Linux/Windows hardware-free (now, automatic) | Active | `arc-v2-spike-xcompile` CI workflow compiles all four candidates against pinned deps on `ubuntu-latest` / `windows-latest` / `macos-latest` — platform breakage surfaces before any physical session is spent |
| Linux physical (later, owner's box) | Planned | Pre-written checklist: timing re-runs, Orca on X11 and Wayland, fcitx5 and ibus |
| Windows physical (later, no hardware recorded) | Planned | Pre-written checklist; if hardware never materializes, the selection memo must say Windows support unverified — never silently assumed |

## Honesty line

CI runners produce compile evidence only. Xvfb/llvmpipe numbers are banned from
the decision matrix: software rasterizer + virtual display measures the wrong
thing. Each CI run prints that banner into its own log.

## Selection gating under this sequencing

1. After the macOS round: draft provisional ranking memo. The owner may
   approve a provisional selection to unblock `arc-ui::kit` work
   (feature-flagged, labeled `reversible-pending-Linux`).
2. Final selection still needs the Linux session plus a recorded owner
   decision on the Windows gap.
3. If the M4 is the daily-driver v2 must feel good on, pinning it as the
   benchmark machine is one line in the benchmark plan — that would upgrade
   macOS numbers from indicative to binding.
