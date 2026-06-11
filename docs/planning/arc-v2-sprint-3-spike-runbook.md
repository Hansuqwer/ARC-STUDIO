# ARC v2 — Sprint-3 Framework Spike Runbook (G1–G8)

Date prepared: 2026-06-11 · Prepared on: sandbox (no display) · Executes on:
**desktop hardware with display server + GPU** (this runbook's whole purpose is
that the desktop session is fill-in-the-numbers, not engineering).

Preconditions:
1. Owner confirms the ADR-0002 addendum (`arc-v2-adr-0002-addendum-draft.md`) — revised
   decision rule + G8 (ARC2-13). **DONE 2026-06-11, confirmed as written.**
2. A spike machine matching `arc-v2-benchmark-plan.md §Environment`, or an explicit
   owner note that spike numbers are indicative-only until re-run on pinned hardware.

## 0. What is already built (sandbox-verified, tests green)

| Piece | Where | Status |
|---|---|---|
| Measurement harness: percentiles (nearest-rank, Sprint-1-consistent), vsync-aware frames conversion | `rust/spikes/spike-harness/src/percentile.rs` | 5 tests green |
| Gate table G1–G8 with encoded pass bars; evidence gates can NEVER auto-pass; missing measurements = NotRun (not Pass) | `src/gates.rs` | 5 tests green |
| SpikeReport JSON (machine identity embedded; honesty note auto-attached on unpinned machines; verdict blocks on Fail/Pending/NotRun) | `src/report.rs` | 3 tests green |
| FrameScript event-loop inversion: one `Action` per present callback; G1/G2/G3/G4 sample semantics centralized; chunked G3 arrival records finding F9 | `src/script.rs` + `src/runner.rs` | simulated loop tests green |
| Deterministic workloads (seeded LCG, digest-verified): source-like 10/100 MB, pathological single-line, 5k-line diff, 2000-key stream | `src/workloads.rs` + `gen-workloads` bin | 4 tests green; 10 MB digest `12ffe06c82255722` reproduced |
| G3 headless baseline (decode+project half, for time attribution) | `g3-headless-baseline` bin → `reports/g3-headless-baseline.json` | run: 100-row replay p50 122 µs — rendering budget is effectively the whole 250 ms |
| Shell model as executable spec (palette/focus/status-rail behaviors) | `rust/arc-shell` tests | 37 tests green since Sprint 2 |

The spikes workspace is **separate** (`rust/spikes/Cargo.toml`): framework deps can
never leak into the main `Cargo.lock` (Sprint-1 gate stays true by construction).

## Local preflight 2026-06-11

Owner confirmed the ADR-0002 addendum as written. Local macOS preflight ran on an
unpinned MacBook Air (Apple M4, 60 Hz built-in display); results are indicative-only.
Evidence lives in `reports/sprint3-local-preflight.json`.

Preflight completed:
- Rust 1.96 installed via Homebrew.
- Xcode Metal Toolchain installed via `xcodebuild -downloadComponent MetalToolchain` after gpui initially failed without `metal`.
- Candidate pins resolved: gpui 0.2.2, gpui-ce rev `c237d57d1caed1bb6c6651ddc3ce9cafa86161b6`, floem 0.2.0, bespoke deps winit 0.31.0-beta.2 / vello 0.9.0 / parley 0.10.0 / accesskit_winit 0.33.0 / optional masonry 0.4.0.
- Deterministic workloads generated under `/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-v2-spike/workloads`; digest values are recorded in the preflight report.
- Main Rust tests, main clippy, spike-harness tests, spike-harness clippy, and facade gate passed.
- Temp dependency build checks passed for gpui, gpui-ce, floem, and bespoke deps. No framework deps entered main `rust/Cargo.lock`.

Still blocked:
- No `reports/spike-<candidate>.json` exist yet because the five render hooks have not been implemented per candidate.
- Full G5/G6 evidence requires Linux and Windows screen-reader/IME sessions in addition to macOS; this macOS-only preflight cannot complete those gates.

## 1. Candidate pins (resolve exact versions on spike day — pin THEN build)

| Candidate | Source | Pin note (2026-06-11 status) |
|---|---|---|
| gpui | crates.io | published ~Oct 2025; upstream investment paused for non-Zed use (Dec 2025) — still spiked for completeness |
| gpui-ce | github.com/gpui-ce/gpui-ce | community fork, pin a rev not a branch |
| floem | crates.io | active (repo updated Feb 2026); pre-1.0, expect breaking changes |
| bespoke | winit + vello + parley + accesskit_winit (+ optionally masonry as widget layer) | Linebender Q1-2026: Masonry has IME via ui-events; CuTTY (alacritty fork on Vello/Parley) is the text-surface existence proof |

Per candidate, move one `rust/spikes/<name>-editor/` crate from `exclude` to
`members` in `spikes/Cargo.toml`, implement one window/event loop against
`FrameScript`, run it, then move it back before starting the next candidate:

```text
Action::OpenWorkload(path,label) -> swap text view, next present closes G1 sample
Action::LoadDiff(path)           -> swap diff view, warmup/settle only
Action::ScrollStep               -> scroll once; G2 samples present-to-present
Action::AppendRows{from,count}   -> append only that chunk; G3 samples issue-to-present
Action::TypeChar{ch}             -> insert one synthetic key; G4 samples issue-to-present
Action::TakeScreenshot{out}      -> render bidi/ligature sample, write screenshot
```

Finding F9: the old one-row-per-frame G3 rule and the 250 ms total budget were
mutually unsatisfiable at vsync. The script uses chunked arrival (`g3_chunk=10`)
to model SSE bursts while preventing all-rows batching; the 33 ms worst-frame
bar still guards per-frame rendering cost.

## 2. Run order per candidate (one sitting, one report file)

1. `gen-workloads <dir>` once per machine; verify `digests.json` matches the
   committed values (byte-identical workloads across candidates/machines).
2. Record machine identity into the report **first** (hostname/CPU/GPU/display Hz/
   power profile/pinned-flag) — the report constructor demands it.
3. G1 → G2 → G3 → G4 (automatic; raw JSON per gate beside the report).
4. G5 (screen reader per OS) and G6 (IME matrix: macOS JA/ZH/KO; Linux fcitx5 AND
   ibus on Wayland, fcitx5 X11 smoke; Windows TSF; dead-keys row) — recordings or
   tree dumps; file paths into the report's evidence rows.
5. G7 golden-image compare.
6. G8 sustainability rows (can be filled before spike day — desk research).
7. `SpikeReport::spike_verdict()` — blockers list is the candidate's scorecard.
   Commit `reports/spike-<candidate>.json` raw.

## 3. Decision (after all candidates)

Apply the addendum rule (facade cost → G8 sustainability → a11y/IME quality), fill
`arc-v2-sprint-3-decision-matrix.md`, write the one-page owner memo, get the verdict
recorded. Only then does `arc-ui::kit` gain a framework feature and `arc-shell` a window.

## 4. Honesty rails

- A spike run on an unpinned machine carries the auto-generated honesty note and
  cannot produce pass/fail claims — indicative only.
- NotRun gates block the verdict; silence is not a pass (encoded in `spike_verdict`).
- No universal editor comparisons; candidates are compared to each other on this
  workload only.
