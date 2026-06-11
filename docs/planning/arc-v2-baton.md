# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-11 (PM-4) · Branch: `arc-v2/sprint-1-protocol-bridge` @ `ececa19` + sprint-8 cherry-pick

## Who holds the baton

**Split lanes (owner directive "execute as many phases as you can"):**
- **M4 (local CLI):** the spike queue — unchanged, **top priority / critical path**.
- **Arena (sandbox):** all framework-free phase cores are now DONE and merged:
  §3.12 streams (`arc-daemon-client::streams`), Sprint-4 editor core
  (`arc-editor`: Buffer/undo-redo/completion stub), Sprint-5
  (`arc-workspace` worktree+watcher; `arc-index` tantivy w/ planted-secret
  redaction + corruption-rebuilds, rusqlite WAL symbols), Sprint-6
  (`arc-terminal` PTY echo/resize/exit matrix; Linux rows container-proven,
  macOS rows CLI-proven, ConPTY rows await Windows shell), Sprint-7 panels
  (`arc-dock`: SurfaceState/Runs/EventStream w/ replay parity), Sprint-8
  security surfaces (`arc-dock`: HitlModal Escape=dismiss-not-deny +
  DiffReview confirmation-gated apply).
  Workspace: 9 crates / 104 tests (Linux) / 97 (macOS — two honest
  #[cfg(linux)] gates: watcher-live, 1MiB throughput; xcompile CI covers).
  **When the spike selects a framework, Sprints 4–8 collapse into pure
  render work over tested models.**
- **Open owner item:** HITL decision API proposal
  (`arc-v2-hitl-decision-api-proposal.md`, F3) — checkbox block awaiting
  verdict; gates Sprint-8 daemon integration.

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
