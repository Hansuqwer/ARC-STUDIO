# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-12 (PM-2) · Branch: `arc-v2/sprint-1-protocol-bridge` @ b36cf54+1

## Who holds the baton

**ARENA (sandbox):** facade-cost ports landed (criterion #1). **Do the final
criterion-#1 adjudication** — gpui 20 vs floem 18 reorders the provisional
ranking; tension vs G8/G1 documented in memo §5b. CLI did NOT self-adjudicate
the close call (memo reserved it for Arena + owner). Then: `arc_ui::kit`
feature-flag plan for the confirmed leader + top-two G5/G6/G7 evidence.

**M4 (local CLI):** both facade ports done (`shell_port.rs` floem + gpui,
committed). Awaiting final-ranking confirmation before kit work.

## Facade-cost results (criterion #1, 2026-06-12, committed)

| Sub-score | floem | gpui |
|---|---|---|
| F-LOC | 5 (214) | 5 (190) |
| F-CONCEPT | 5 (0 edits) | 5 (0 edits) |
| F-EVENT | 4 (reactive signal mirror) | 5 (retained-mode direct) |
| F-SWAP | 4 | 5 |
| **Total** | **18/20** | **20/20** |

gpui leads criterion #1 (the top criterion) by 2 pts — the floem↔gpui reorder
the memo predicted. Tension: floem still leads G8 (14 vs 9) + G1 (58 vs 201ms).
Final call is Arena's + owner's. `facade` blocks committed in both reports.

Caveat: gpui shell_port tests disk-blocked on M4 box (gpui --test binary >1.6GB
free; SIGBUS). Build+clippy clean; pure-fn logic identical to floem's passing
tests.

## Spike results (committed, indicative-only — M4 not pinned benchmark machine)

| Gate | floem 0.2 | gpui 0.2.2 | gpui-ce c237d57 |
|---|---|---|---|
| G1 first-paint | Pass (58ms src / 6ms path) | Pass (51ms src / 201ms path) | Pass (166ms) |
| G2 scroll p99 | 17.0ms (1.03f) FAIL | 17.7ms (1.06f) FAIL | 17.6ms (1.06f) FAIL |
| G3 replay | Pass (worst 16ms) | Pass (worst 17ms) | Pass (worst 17ms) |
| G4 typing p99 | 17.1ms (1.03f) FAIL | 17.7ms (1.06f) FAIL | **50.6ms (3.03f) FAIL** |
| G5/G6/G7/G8 | EvidencePending | EvidencePending | EvidencePending |
| text render | visible (clean) | visible (clean) | **non-visible (black)** |

Reports: `reports/spike-{floem,gpui,gpui-ce}.json` + raws + `.status` sidecars.

## Candidate findings (recorded)

- **F-floem-1:** floem 0.2 has no raw present callback. Proxy: `create_effect`
  + `exec_after(1ms)` → tick. Post-signal-propagation, pre-GPU-submit. ~0.5ms
  timer noise pushes G2/G4 p99 to 1.03 frames. Score as F-CONCEPT.
- **F-gpui-1:** clean `on_next_frame` present callback (trustworthy). G2/G4 p99
  1.06 frames is the harness's callback-entry-vs-scanout gap, not a render fail.
- **F-gpui-ce-1:** text glyphs did not visibly paint with bare
  `div().font_family().child()` (dark bg only → appeared as black screen);
  on_next_frame still fired at vsync (G2/G3=16.7ms confirm real presents).
  Visual-paint fidelity UNVERIFIED.
- **F-gpui-ce-2:** G4 typing p50=49ms (~3 frames/keystroke) vs gpui/floem
  ~16.6ms — real per-keystroke regression on this fork+rev.

## Cross-candidate read (for the memo, owner to confirm)

- G2/G4 "fails" at 1.03–1.06 frames are **uniform across floem+gpui** → almost
  certainly the harness measurement gap (callback-entry Instant, not scanout),
  NOT a real rendering failure. Recommend the memo flag the G2/G4 bar as
  measurement-bound on unpinned M4 and defer pass/fail to pinned hardware.
- gpui-ce is the **only** candidate with a real anomaly: 3-frame typing +
  non-visible text. Both are fork-specific (c237d57) and lower its provisional
  rank vs upstream gpui.
- floem has the best G1 (58ms) and clean text; gpui has the cleanest present
  callback (on_next_frame). These two lead the provisional 3-way.

## NEW (PM-2): Sprint-10 core + Sprint-12 supply-chain slices landed (Arena)

- **arc-plugin-host** (15 tests, probe-verified wasmtime 36 in-container):
  fuel + epoch budget kills (typed-Trap classified, real ticker thread);
  guarded_host_call — deny-by-default early-denial (op never executes),
  worker-thread time-bound, audit-on-allow AND on-deny, **fail-closed on
  audit failure** (result discarded — review §9.2); CapabilitySet with
  scope-exact matching (no implicit widening); minisign manifest verify
  (unsigned refused; dev override loud). Honest scope label: component-model
  ABI + WASI ctx land with the first real extension; wasm ≠ VM boundary.
- **Supply chain (Sprint-12 slice):** rust/deny.toml live and PASSING
  (advisories/bans/licenses/sources all ok) after real fixes — tempdir→
  tempfile (RUSTSEC deprecation chain), tantivy 0.22→0.25 (drops
  unmaintained `instant`), publish=false on all 10 private crates,
  CC0 allowed for notify. Framework crates also banned at the deny layer
  (defense in depth vs the facade grep).
- Workspace: 10 crates / 124 tests / clippy 0 / fmt clean / deny clean.

## DECIDED 2026-06-12 (owner delegated via "decide")

All five checkboxes recorded in the memo §6: (1) ranking ACCEPTED — floem 1,
gpui 2, gpui-ce PARKED (now with F-gpui-ce-3: rev doesn't compile on Linux,
E0308 in surface.rs — three defects at one rev); (2) R1 ACCEPTED and
CODIFIED in spike-harness (P99 gates: p99 ≤ 1.1 frames AND 0% >2vsync,
raws required — no raws = NotRun); (3) bespoke SKIPPED (reversible);
(4) **M4 PINNED as benchmark machine** (arc-v2-benchmark-environment.md —
macOS numbers now binding); (5) **facade ports AUTHORIZED** for floem +
gpui — THE CLI'S NEXT M4 TASK (shell_port.rs per facade-cost-protocol,
then top-two G5/G6/G7 evidence).

## Still owner-gated / next

1. **Arena:** draft provisional ranking memo (G1–G4 + findings + G8 pre-fills),
   flag G2/G4 as measurement-bound, → owner sign-off.
2. **bespoke spike:** NOT started (stop condition). Owner override required.
3. **Evidence rows** (G5/G6/G7/G8) for all 3: operator screenshots (bidi),
   VoiceOver tree dumps, IME scripts — needed before any final verdict.
4. On sign-off: `arc_ui::kit` feature-flag plan for the leading candidate.

## Build/infra notes

- Spike target dir moved OUT of worktree to `~/cargo-spike-target` (the macOS
  `/T/` worktree filesystem hit 100% during gpui-ce git-dep build). Spike
  `target/` is gitignored. Run spikes from `rust/spikes/` so `../../reports/`
  relative paths resolve.
- gpui spike crashed first run (SIGABRT via `__eprint`): root cause was
  registering `on_next_frame` from inside `render()` + `cx.notify()` re-entry.
  Fixed to blessed Zed pattern: register first frame at window-open, re-register
  inside the callback, pure render(), no stdout/stderr in run loop.

## Stop conditions (active)

- Ambiguous gate → stop, report finding.
- Untrustworthy present-callback → record finding, continue. (gpui-ce hit this.)
- All-fail → escalate to owner; **never self-start the bespoke sprint.**

## Standing constraints (unchanged)

Native-only · v1 shippable (230 tests) · additive protocol · deterministic
security · daemon producer-of-truth · facade rule · no overclaiming
(M4 unpinned ⇒ indicative-only; CI runners ⇒ compile evidence only).

## M4 execution order (next)

1. **gpui** spike — uncomment `gpui-editor` in `rust/spikes/Cargo.toml`, bind
   Action arms, run, generate `reports/spike-gpui.json`.
2. **gpui-ce** — same pattern, `gpui-ce-editor`.
3. **bespoke** — last.
4. When 4 reports land: Arena drafts provisional ranking memo → owner sign-off.

## floem spike findings (recorded)

- F-floem-1: No raw present callback in floem 0.2. Measurement proxy:
  `create_effect(|_| { tick.get(); ... exec_after(1ms, |_| tick.set(now)); })`
  Post-signal-propagation, pre-GPU-submit. Timer adds ~0.5ms noise → G2/G4
  p99 reads 17.1ms = 1.03 frames at 60Hz (bar is ≤1 frame). Real render cost
  is likely ~16.6ms (one frame). Record as F-CONCEPT cost in facade rubric.
- G7 bidi screenshot: NOT captured. Operator must re-run and screenshot the
  bidi phase (mixed Arabic/Hebrew/Latin text visible in window) before filling
  in `reports/spike-floem.json` G7 raw_data_path.

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

Native-only · v1 shippable (230 tests) · additive protocol · deterministic
security · daemon producer-of-truth · facade rule · no overclaiming
(M4 unpinned ⇒ indicative-only; CI runners ⇒ compile evidence only).

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
