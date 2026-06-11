# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-11 (PM-5) · Branch: `arc-v2/sprint-1-protocol-bridge` @ `88f93571`

## Who holds the baton

**M4 (local CLI):** the spike queue — unchanged, **top priority / critical path**.

**Arena (sandbox):** all framework-free phase cores DONE and merged, including
Sprint-8 daemon integration:
- §3.12 streams (`arc-daemon-client::streams`)
- Sprint-4 editor core (`arc-editor`: Buffer/undo-redo/completion stub)
- Sprint-5 (`arc-workspace` worktree+watcher; `arc-index` tantivy w/ planted-secret
  redaction + corruption-rebuilds, rusqlite WAL symbols)
- Sprint-6 (`arc-terminal` PTY echo/resize/exit matrix; Linux rows container-proven,
  macOS rows CLI-proven, ConPTY rows await Windows shell)
- Sprint-7 panels (`arc-dock`: SurfaceState/Runs/EventStream w/ replay parity)
- Sprint-8 security surfaces (`arc-dock`: HitlModal Escape=dismiss-not-deny +
  DiffReview confirmation-gated apply)
- **Sprint-8 daemon integration (DONE):** HITL decision endpoint authorized +
  implemented. `GET /api/hitl` + `POST /api/hitl/{hitl_id}/decision`. Thin HTTP
  face over existing `HitlSqliteStore`. Verdict vocabulary: daemon's enum
  (`approve|reject|modify|skip`); shell's `AlwaysRequireApproval` → `reject` +
  notes (documented in `rust/arc-dock/src/hitl.rs`). Rust client:
  `arc-daemon-client::hitl` (`hitl_list()` / `hitl_decide()`). 10 route tests,
  live e2e verified. Sprint 8 daemon integration **unblocked**.

Workspace: 9 crates / 117 macOS tests / 104 Linux tests (two honest
`#[cfg(linux)]` gates: watcher-live, 1MiB throughput; xcompile CI covers).

**When the spike selects a framework, Sprints 4–8 collapse into pure
render work over tested models.**

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
