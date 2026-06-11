# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-11 · Branch: `arc-v2/sprint-1-protocol-bridge` @ `00c24bd`

## Who holds the baton

**Local CLI on the M4.** Arena agent idle until `reports/spike-<candidate>.json`
files land (handover §6 stop-conditions govern).

## M4 execution order (recorded recommendation)

1. `workflow_dispatch` on `arc-v2-spike-xcompile` — 5 min; catches Linux/Windows
   compile breaks before any hook investment.
2. **floem** — healthiest G8, clearest docs; best place to discover
   FrameScript integration friction.
3. **gpui**, then **gpui-ce** — shared Metal toolchain, shared learnings.
4. **bespoke** — most integration work, last.

Per candidate: uncomment member in `spikes/Cargo.toml` → bind Action arms to
`spike_harness::views` types → run script → `shell_port.rs` + facade
sub-scores (`arc-v2-facade-cost-protocol.md`) → G5/G6 recordings
(`arc-v2-macos-g5-g6-protocol.md`) → commit report + raws + evidence.

## Stop conditions (active)

- Ambiguous gate → stop, report finding.
- Untrustworthy present-callback (render-return only) → record as candidate
  finding, continue.
- All-fail → escalate to owner; never self-start the bespoke sprint.

## Queued on the Arena side when reports land

1. Provisional ranking memo (G1–G4 + facade totals + G8 pre-fills + macOS
   G5/G6 quality) → owner sign-off on provisional verdict block.
2. Escalation drafts per stop-condition.
3. `arc_ui::kit` feature-flag implementation plan for the selected candidate.

## Standing constraints (unchanged)

Native-only · v1 shippable (220 tests) · additive protocol · deterministic
security · daemon producer-of-truth · facade rule · no overclaiming
(M4 unpinned ⇒ indicative-only; CI runners ⇒ compile evidence only).
