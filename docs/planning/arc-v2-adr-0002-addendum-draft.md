# ADR-0002 Addendum (DRAFT) — Spike decision rule revision + G8

Status: **DRAFT — awaiting owner confirmation (backlog item ARC2-13).**
This is an additive addendum; ADR-0002's candidate set, gate structure G1–G7,
and never-WebView escalation path are unchanged.

## Context (what changed since ADR-0002 was written)

Evidence gathered 2026-06-11 (deep-research review §4.1, sources cited there):

1. **GPUI upstream investment paused.** Dec 2025: Zed publicly deprioritized GPUI
   work not directly relevant to Zed through 2026. A community fork, **gpui-ce**,
   was started by Zed's former employee #1, co-maintained off-hours by a current
   Zed engineer. GPUI remains the engine of a shipping editor (technology proven);
   its availability *as a dependency for outsiders* has degraded.
2. **cargo-dist precedent.** The axodotdev funding collapse (2025) demonstrated,
   inside this project's own toolchain choices, how fast a single-vendor OSS
   dependency can stall. Framework choice is the least reversible decision in
   the v2 plan; sustainability deserves a scored gate, not a vibe.
3. **Bespoke fallback got cheaper.** Linebender Q1-2026: Masonry gained IME
   integration (ui-events) and renderer abstraction; Parley adoption now includes
   a ported Alacritty fork (CuTTY) — a text-heavy-surface existence proof.

## Decision (proposed)

1. **Spike five build targets, four candidates:** gpui (crates.io pin), gpui-ce
   (rev pin), floem (pin), bespoke (winit+vello+parley+accesskit, Masonry
   permitted as widget layer).
2. **Add gate G8 — Sustainability** (scored row, no auto pass/fail):
   (a) release cadence trailing 12 months; (b) bus factor / governance;
   (c) breaking-change rate vs our pinned version; (d) vendoring cost if
   upstream stalls. Encoded in `spike-harness::gates` as an evidence gate.
3. **Replace the tie-breaker.** OLD: "both pass → prefer GPUI." NEW: among clean
   candidates, select by (1) facade cost, (2) G8, (3) a11y/IME evidence quality.
   GPUI holds no default preference. (Supersedes the v1-brief D1 wording too.)
4. **Unchanged:** no candidate clean → one contained bespoke sprint; bespoke
   fails → owner escalation; WebView/Tauri/Electron never selected silently.

## Consequences

- R1 (GPUI churn) severity raised in the risk register; kill criterion now
  includes "pinned version unbuildable on stable Rust within one toolchain
  upgrade cycle AND vendoring cost exceeds one sprint."
- The facade-cost criterion is *measurable*: port the Sprint-2 ShellModel render
  (palette, focus ring, status rail) in each candidate and count the diff.
- Spike cost rises by one candidate (gpui-ce); harness reuse keeps the increment
  to the render hooks only.

## Owner decision requested

- [ ] Confirm addendum as written
- [ ] Confirm with changes: ____________________
- [ ] Reject (spike proceeds under original ADR-0002 rule)

Recorded: ____________ (date / venue)
