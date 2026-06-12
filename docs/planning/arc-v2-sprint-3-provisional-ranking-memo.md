# Sprint-3 Provisional Ranking Memo (macOS round, 3 of 4 candidates)

Date: 2026-06-12 · Author: Arena agent (per baton handoff at `761255d`)
Inputs: `reports/spike-{floem,gpui,gpui-ce}.json` + raw sample files +
`.status` sidecars + CLI findings F-floem-1, F-gpui-1, F-gpui-ce-1/2 +
G8 desk research (`arc-v2-g8-sustainability-evidence.md`).

**Honesty header:** M4 is NOT the pinned benchmark machine — every number
below is indicative-only and cannot constitute a pass/fail claim on its own
(the reports carry this note machine-generated). This memo therefore asks for
a *provisional* verdict only, exactly as `arc-v2-sprint-3-os-sequencing.md`
defines it: unblocks `arc_ui::kit` behind a feature flag, reversible pending
Linux, NOT a final selection.

---

## 1. The G2/G4 "failures" are measurement-bound — raw-data proof

The harness bar is p99 ≤ 1.0 frame. All three candidates "fail" G2/G4 at
1.03–1.06 frames — except gpui-ce's G4 at 3.03. The raw samples
(`spike-raw-*-g4.json`, n=2000 each) separate measurement artifact from real
regression decisively:

| Candidate | G4 mean | G4 max | **Frames > 2 vsyncs** |
|---|---|---|---|
| floem | 16,656 µs (= vsync) | 18,939 µs | **0 / 2000 (0.0%)** |
| gpui | 16,666 µs (= vsync) | 19,365 µs | **0 / 2000 (0.0%)** |
| gpui-ce | 40,866 µs (≈ 2.5 vsyncs) | 50,968 µs | **1,775 / 2000 (88.8%)** |

floem and gpui sit *exactly on* the 16,667 µs vsync period with sub-3 ms
jitter and zero missed-double-deadlines: a frame-scheduled pipeline measured
from callback-entry rather than scanout will read 1.0X frames by
construction. This is the measurement gap the review flagged pre-emptively
(§10.2 vsync quantization) — the bar is unsatisfiable as written on a 60 Hz
compositor when sampling callback-entry Instants.

**Recommendation R1:** treat G2/G4 ≤ ~1.1 frames with **0% frames > 2
vsyncs** as presumptively-pass on unpinned hardware; re-adjudicate the exact
bar at pinned-hardware time (either measure scanout, or codify the
frames>2vsync discriminator as the gate metric). This is a *bar
clarification*, not a bar relaxation — gpui-ce still fails it decisively.

## 2. Results under that reading

| Gate | floem 0.2.0 | gpui 0.2.2 | gpui-ce c237d57 |
|---|---|---|---|
| G1 worst-of-two first paint | **58 ms** | 201 ms | 166 ms |
| G2 scroll | presumptive-pass (0% >2v) | presumptive-pass (0% >2v) | presumptive-pass (0% >2v) |
| G3 replay (250 ms / 33 ms) | Pass (165/16) | Pass (167/17) | Pass (166/17) |
| G4 typing | presumptive-pass (0% >2v) | presumptive-pass (0% >2v) | **FAIL — 3 frames/keystroke, 88.8% >2v** |
| Text paint fidelity | clean | clean | **unverified (glyphs not visible; F-gpui-ce-1)** |
| Present-callback trust | proxy only (F-floem-1: create_effect+exec_after, ~0.5 ms timer noise) | **clean (`on_next_frame`)** | callback fires at vsync but paints unverified |
| G8 desk score (of 20) | **14** | 9 | 8 |
| G5/G6/G7 | pending | pending | pending |

## 3. Provisional ranking

> **1. floem · 2. gpui (close second) · 3. gpui-ce (anomalies disqualify at this rev)**

Reasoning against the ADR-0002 addendum rule, honestly labeled:

- **The rule's criterion #1 (facade cost) has NOT been scored yet** — no
  `shell_port.rs` exists for any candidate. This ranking is therefore based
  on criteria #2 (G8) and #3 (evidence quality) plus the automatic gates,
  and is *provisional twice over*. Facade ports can reorder floem↔gpui;
  they cannot rehabilitate gpui-ce's measured regression.
- floem leads on G1 (58 ms vs 201/166 — 3× faster on the worst workload),
  G8 (14 vs 9/8), and clean text. Its one debit is the present-callback
  proxy (F-floem-1) — a real F-CONCEPT hit for the facade port to quantify,
  and the strongest reason the gpui port must actually be built rather than
  skipped.
- gpui's trustworthy `on_next_frame` is the better *measurement* story and
  likely the better *render-loop integration* story; its G1 pathological
  cost (201 ms, still well under the 1000 ms bar) and G8 (9, upstream
  attention withdrawn) are the debits.
- gpui-ce at c237d57: 3-frames-per-keystroke (raw-data confirmed, 88.8% of
  samples) + unverified glyph paint are fork-specific regressions vs
  upstream gpui (F-gpui-ce-1/2). **Recommend: park the fork** — do not
  spend G5/G6/G7 evidence effort on it at this rev; re-pin only if a later
  rev demonstrably fixes both findings. Its existence remains G8-relevant
  to gpui (it is the vendor path).

## 4. Bespoke spike: recommend SKIP for the provisional round (owner call)

The stop condition was honored (not self-started). Recommendation: with two
viable candidates showing 0% missed frames and clean text, the bespoke
spike's information value no longer justifies its cost (it was the
no-candidate-survives fallback; two survived). Skipping is reversible — the
crate skeleton and pins stay committed. If the owner wants the data anyway,
it slots after the facade ports without blocking anything.

## 5. What the provisional verdict would unblock / still requires

On owner sign-off of ranking + R1:
1. **Facade-cost ports** (criterion #1, finally measurable): `shell_port.rs`
   for floem AND gpui per `arc-v2-facade-cost-protocol.md` — the deciding
   input between the top two.
2. `arc_ui::kit` feature-flag plan drafted for the leader (work may begin
   behind `framework-floem` / `framework-gpui` flags without committing).
3. Evidence rows for the TOP TWO only (G7 bidi screenshots, G5 VoiceOver,
   G6 IME scripts per `arc-v2-macos-g5-g6-protocol.md`) — required before
   any *final* verdict, along with the Linux session.

Still blocked regardless: final selection (needs Linux session + Windows-gap
decision per os-sequencing doc), Sprint 4+ render work beyond the flag-gated
kit, retirement-path anything.

## 6. Owner decision checkboxes

- [ ] **Ranking accepted** (floem 1 · gpui 2 · gpui-ce parked at this rev)
- [ ] **R1 accepted** — G2/G4 measurement-bound reading + frames>2vsync
      discriminator, re-adjudicated at pinned hardware
- [ ] **Bespoke spike:** skip for provisional round / run anyway: ____
- [ ] **M4 pinning:** pin as benchmark machine (one line in
      arc-v2-benchmark-plan §Environment; upgrades these numbers from
      indicative to binding) / keep unpinned: ____
- [ ] **Authorize facade-cost ports** for floem + gpui (top-two decider)

Recorded: ____________ (date / venue)
