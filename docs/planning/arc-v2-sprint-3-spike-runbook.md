# ARC v2 — Sprint-3 Framework Spike Runbook (G1–G8)

Date prepared: 2026-06-11 · Prepared on: sandbox (no display) · Executes on:
**desktop hardware with display server + GPU** (this runbook's whole purpose is
that the desktop session is fill-in-the-numbers, not engineering).

Preconditions (both currently OPEN):
1. Owner confirms the ADR-0002 addendum (`arc-v2-adr-0002-addendum-draft.md`) — revised
   decision rule + G8 (ARC2-13).
2. A spike machine matching `arc-v2-benchmark-plan.md §Environment`, or an explicit
   owner note that spike numbers are indicative-only until re-run on pinned hardware.

## 0. What is already built (sandbox-verified, tests green)

| Piece | Where | Status |
|---|---|---|
| Measurement harness: percentiles (nearest-rank, Sprint-1-consistent), vsync-aware frames conversion | `rust/spikes/spike-harness/src/percentile.rs` | 5 tests green |
| Gate table G1–G8 with encoded pass bars; evidence gates can NEVER auto-pass; missing measurements = NotRun (not Pass) | `src/gates.rs` | 5 tests green |
| SpikeReport JSON (machine identity embedded; honesty note auto-attached on unpinned machines; verdict blocks on Fail/Pending/NotRun) | `src/report.rs` | 3 tests green |
| Deterministic workloads (seeded LCG, digest-verified): source-like 10/100 MB, pathological single-line, 5k-line diff, 2000-key stream | `src/workloads.rs` + `gen-workloads` bin | 4 tests green; 10 MB digest `12ffe06c82255722` reproduced |
| G3 headless baseline (decode+project half, for time attribution) | `g3-headless-baseline` bin → `reports/g3-headless-baseline.json` | run: 100-row replay p50 122 µs — rendering budget is effectively the whole 250 ms |
| Shell model as executable spec (palette/focus/status-rail behaviors) | `rust/arc-shell` tests | 37 tests green since Sprint 2 |

The spikes workspace is **separate** (`rust/spikes/Cargo.toml`): framework deps can
never leak into the main `Cargo.lock` (Sprint-1 gate stays true by construction).

## 1. Candidate pins (resolve exact versions on spike day — pin THEN build)

| Candidate | Source | Pin note (2026-06-11 status) |
|---|---|---|
| gpui | crates.io | published ~Oct 2025; upstream investment paused for non-Zed use (Dec 2025) — still spiked for completeness |
| gpui-ce | github.com/gpui-ce/gpui-ce | community fork, pin a rev not a branch |
| floem | crates.io | active (repo updated Feb 2026); pre-1.0, expect breaking changes |
| bespoke | winit + vello + parley + accesskit_winit (+ optionally masonry as widget layer) | Linebender Q1-2026: Masonry has IME via ui-events; CuTTY (alacritty fork on Vello/Parley) is the text-surface existence proof |

Per candidate, create `rust/spikes/<name>-editor/`, add to `spikes/Cargo.toml`
members (uncomment), and implement the **same five hooks** against spike-harness:

```text
open_workload(path) -> first_paint_ms          (G1: 100 MB + pathological)
scroll_diff(patch) -> frame_times              (G2: 5k-line diff)
replay_rows(100 fixture rows) -> total+frames  (G3: tool-use-streaming scenario)
type_stream(2000 keys) -> keypress->present    (G4: on_next_present callback)
render_bidi_ligature_sample() -> screenshot    (G7: golden compare)
```

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
