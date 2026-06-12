# Sprint-3 Criterion-#1 Adjudication — Provisional Selection

Date: 2026-06-12 · Author: Arena agent (per memo handback: "final call is
Arena's + owner's") · Inputs: facade blocks in `reports/spike-{floem,gpui}.json`
(rubric: `arc-v2-facade-cost-protocol.md`), both `shell_port.rs` files (audited
line-level), provisional ranking memo + its owner-decided checkboxes.

## 1. Audit of the facade scores (Arena verification, this container)

| Check | Result |
|---|---|
| Shared models unchanged (F-CONCEPT 5 claims) | ✔ verified: zero commits touching `rust/arc-ui/` since `8c4bd24`; both ports import `PaletteModel`/`FocusRing`/`Theme` unmodified |
| The F-EVENT 4-vs-5 gap is architectural, not stylistic | ✔ verified in code: floem `shell_port.rs:110-130` carries a mandatory `sync` model→signal mirror (6 RwSignals) because fine-grained reactivity can't observe plain struct mutation; gpui's view Entity holds the models directly, `render()` reads them, `cx.notify()` re-renders — 0 signals, no mirror |
| F-SWAP estimates cite specifics (rubric rule) | ✔ both cite the exact mechanism; the asymmetry is load-bearing (see §3) |
| F-LOC counted per one-file rule | ✔ 214 vs 190 code lines, both score 5; counting method noted (tokei unavailable, blank/comment-strip — acceptable, method recorded) |
| gpui port unit tests | ⚠ disk-blocked on the M4 (~1.6 GB free, SIGBUS) AND memory-blocked in this container (2 GB RAM, SIGKILL compiling gpui+debuginfo). Tests are 3 pure functions structurally identical to floem's 3/3 passing ones. **Open item, low risk, must close before FINAL selection** (any box with >5 GB disk + >4 GB RAM). |

Scores stand as recorded: **gpui 20 · floem 18**.

## 2. Applying the owner-confirmed rule (ADR-0002 addendum)

The rule orders: (1) facade cost → (2) G8 → (3) a11y/IME evidence quality.
Criterion #1 is **not tied** (20 vs 18), so the tie-breakers are not invoked.
By the letter of the rule the owner confirmed at ARC2-13:

> **Provisional selection: gpui 0.2.2.**

The tension the CLI correctly refused to self-adjudicate (G8 14-vs-9 and G1
58ms-vs-201ms favoring floem) is real but does not override the rule —
G8 is tie-break only, and G1 at 201 ms clears its 1000 ms bar five-fold.
What the tension DOES mandate (per the G8 evidence doc's own rule): a
**mitigation plan attached to the selection**, §3.

## 3. Mandatory G8 mitigation plan (gpui's 9/20 sustainability)

1. **The escape hatch is cheap and stays tested.** F-SWAP's asymmetry is the
   decisive risk-reducer: re-porting gpui→floem only ADDS the mechanical
   signal mirror (≤3 days for shell chrome). floem's `shell_port.rs` is NOT
   deleted — it stays in-tree as the proven escape, and the facade CI gate
   keeps `arc_ui::kit` the single swap point. Selecting gpui with a
   floem-shaped parachute is strictly safer than the reverse (floem→gpui
   re-port was estimated ~5 days).
2. **R1 kill criterion armed** (risk register): if the pinned gpui 0.2.2
   becomes unbuildable on stable Rust within one toolchain cycle AND
   vendoring exceeds one sprint, the floem escape executes. gpui-ce is NOT
   the vendor path at c237d57 (three recorded defects); re-evaluate the
   fork's tree only if upstream stalls.
3. **Vendoring budget reserved**: one sprint, pre-approved by this plan.
4. **Version pin discipline**: `=0.2.2` exact; upgrades are reviewed diffs
   with the spike harness re-run (the G-gates are the regression suite).

## 4. What this selection unblocks / what stays blocked

UNBLOCKED (provisional, reversible pending Linux):
- `arc_ui::kit` implementation behind `framework-gpui` (plan: companion doc
  `arc-v2-kit-implementation-plan.md`).
- gpui evidence rows (G5 VoiceOver / G6 IME / G7 bidi per the macOS
  protocol) — now needed for ONE candidate first, floem's only if the
  escape ever executes (cost saving from sequencing).

STILL BLOCKED (final selection requires):
- gpui shell_port tests run green on an adequate box;
- gpui G5/G6/G7 evidence rows complete;
- Linux session (owner's box) — G1–G4 sanity + Orca + fcitx5/ibus;
- Windows-gap decision recorded (os-sequencing doc).
Per os-sequencing: if Linux exposes a gpui-specific failure floem doesn't
share, the provisional selection reverts and the escape executes early.

## 5. Sign-off

- [x] Provisional selection: **gpui 0.2.2** under the owner-confirmed rule
      (criterion #1: 20 vs 18), with the §3 mitigation plan binding.
      Recorded by Arena agent under the standing owner delegation pattern;
      owner may veto by reverting this commit (delete-only).
- [ ] Owner countersign (next session): ____________
