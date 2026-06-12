# ARC v2 — Arena Handover Prompt (2026-06-12 evening)

**For a fresh Arena session with zero context.**
Read the docs in the order listed. Do not start work until you have read all of them.

---

## 0. Who you are and what this project is

You are the Arena sandbox agent on the ARC v2 project. ARC Studio is a local AI
agent workstation tool (Python CLI + Textual TUI + Eclipse Theia IDE). The v2
track is building a **native Rust IDE** to replace the Theia browser frontend.

The canonical repo: `https://github.com/Hansuqwer/arc-theia-studio` (redirects
to `Hansuqwer/ARC-STUDIO.git`).

Active branch: **`arc-v2/sprint-1-protocol-bridge`**  
Current HEAD: **`0ee9618e`**  
Worktree (CLI's push target): `/private/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-v2-live-push`

---

## 1. Read these files first (in order)

All paths are relative to the repo root.

### Governance (read before anything else)
1. `AGENTS.md` — locked agent charter; working discipline, DoD gates, banned claims, sync-loss rules
2. `docs/planning/arc-v2-baton.md` — **primary handover state** (ignore the stale stacked content at the bottom; the live state is the TOP section)

### Decisions already made (do not re-litigate)
3. `docs/planning/arc-v2-sprint-3-final-adjudication.md` — **provisional framework selection: gpui 0.2.2**. Criterion-#1 rule applied; gpui 20/20 vs floem 18/20; floem escape hatch in-tree; G8 mitigation plan binding
4. `docs/planning/arc-v2-sprint-3-provisional-ranking-memo.md` — full analysis including §5b (facade port comparison) and §6 (owner decision record with all 5 checkboxes ticked)
5. `docs/planning/arc-v2-kit-implementation-plan.md` — **the active work plan**: K1 → K2 → K3 → K4

### Active protocols (reference during K2/K3 work)
6. `docs/planning/arc-v2-facade-cost-protocol.md` — scoring rubric (already used for facade ports; reference for K2 shell chrome)
7. `docs/planning/arc-v2-macos-g5-g6-protocol.md` — VoiceOver 5-step script + IME scripts; needed for K3 evidence rows
8. `docs/planning/arc-v2-benchmark-environment.md` — pinned M4 machine identity; all macOS numbers are now binding
9. `docs/planning/arc-v2-hitl-decision-api-proposal.md` — AUTHORIZED & IMPLEMENTED; daemon HITL routes live

### Spike evidence (don't re-run; reports are committed)
10. `reports/spike-floem.json` — floem results + `facade` block (18/20)
11. `reports/spike-gpui.json` — gpui results + `facade` block (20/20)
12. `reports/spike-gpui-ce.json` — gpui-ce results + `candidate_finding` (parked; 3 defects)

---

## 2. Current state in one paragraph

It is 2026-06-12 evening. The Sprint-3 framework selection is complete:
**gpui 0.2.2 is the provisional selection** (criterion-#1, by the owner-confirmed
ADR-0002 addendum rule). The floem escape hatch is committed and in-tree.
The CLI just finished K1 (the first phase of `arc_ui::kit`): the
`framework-gpui` optional feature is live in `rust/arc-ui/Cargo.toml`,
`arc_ui::kit` exports `gpui::*` under the flag, `rust/deny.toml` has a
`wrappers = ["arc-ui"]` exception for gpui, and the Sprint-1 "no framework
in lock" gate is formally retired. Headless arc-ui tests pass (15/15).
The flag-on build (`--features framework-gpui`) is disk-blocked on the M4
(~220Mi free — same root cause as the gpui `--test` binary issue; both
close on a box with ≥5GB disk + ≥4GB RAM).

---

## 3. What you (Arena) own right now

### Immediate: K2 on the M4 (requires display)
Per `arc-v2-kit-implementation-plan.md §K2`:
- Promote `rust/spikes/gpui-editor/src/shell_port.rs` (190 lines, F-CONCEPT 0,
  already committed) → `rust/arc-shell/src/render_gpui.rs` (cfg-gated module)
- Window opens on macOS (pinned M4)
- Keyboard-only palette works IN PIXELS (the model logic is already proven in
  `arc-ui`; K2 proves the wiring)
- NO_COLOR / high-contrast visibly switch rendered output
- Daemon Degraded strip renders from a live kill test
- Cold-start B1 measured with `hyperfine` (honesty rules: is_pinned=true)
- DoD: `arc-shell --window` opens, `arc-shell --headless-status` still works

### After K2: K3 evidence rows
- G5 VoiceOver (5-step script: `arc-v2-macos-g5-g6-protocol.md`)
- G6 IME scripts (JA/ZH/KO/dead keys per the same doc)
- G7 bidi screenshot (the spike's `TakeScreenshot` phase — re-run floem or
  gpui spike and screenshot when mixed-script text is visible; commit to
  `reports/spike-gpui-bidi.png` or `reports/spike-floem-bidi.png`)
- These rows complete the macOS half of FINAL selection

### After K3: K4 first panel
- Event Stream panel: `arc-dock::EventStreamPanel` (already replay-parity
  tested in headless) + `views::EventTable` line discipline + per-run SSE
  from the live daemon. One panel proves the whole model→render→daemon stack.

### Final selection still gates on
1. gpui shell_port unit tests run green (need ≥5GB disk + ≥4GB RAM)
2. K3 evidence rows complete
3. Linux session (owner's hardware) — G1–G4 sanity + Orca + fcitx5/ibus
4. Windows-gap decision recorded

---

## 4. What the CLI owns (don't duplicate)

The CLI agent (Kiro on the developer's macOS M4) owns:
- Running spikes and generating `reports/spike-*.json` (done for floem/gpui/gpui-ce)
- K2 window/pixel work on the M4 (display required — CLI has it, Arena doesn't)
- Committing and pushing to `origin arc-v2/sprint-1-protocol-bridge`

**You (Arena) own**: analysis, ranking memos, implementation planning,
headless Rust work (crate structure, new test-only logic, docs), and
code that doesn't require a GPU/display.

---

## 5. Sync-loss rule (critical — read this)

Arena commits often don't reach the remote because the sandbox can't push.
The established recovery protocol:
1. Arena provides a **git bundle** (not just a commit hash)
2. CLI does `git bundle verify <bundle>` then `git fetch <bundle> ... && git merge --ff-only`
3. **Never trust a bare commit hash** from Arena's chat output unless it's been
   independently verified in `git log` after fetching

Commits known to have been sync-lost this session (already recovered):
- `239eacf` — provisional ranking memo (recovered via re-graft from Downloads)
- `b36cf54` — five spike decisions (recovered via bundle `arc-v2-branch-8c4bd24.bundle`)
- `8c4bd24` — arc-plugin-host + supply-chain (same bundle)
- `e4a4f45` — final adjudication docs (recovered via direct file copy from Downloads)

The bundle mechanism (`arc-v2-branch-8c4bd24.bundle`) permanently fixed the
sync-loss for those commits. If you produce new commits, provide a bundle.

---

## 6. Key architecture facts

```
Branch: arc-v2/sprint-1-protocol-bridge  (separate from main)
HEAD:   0ee9618e

Rust workspace: rust/
  arc-ui/          — facade crate; ONLY crate that may import gpui/floem
                     NOW has framework-gpui feature (K1 complete)
  arc-shell/       — ShellModel, supervisor, daemon client wiring
  arc-editor/      — rope-backed buffer, InlineCompletionProvider (Sprint-4)
  arc-workspace/   — WorktreeModel, WorkspaceWatcher (Sprint-5)
  arc-index/       — tantivy full-text + rusqlite symbols (Sprint-5)
  arc-terminal/    — alacritty PTY+grid (Sprint-6)
  arc-dock/        — SurfaceState panels + HitlModal + DiffReview (Sprint-7/8)
  arc-daemon-client/ — HITL client, stream taxonomy
  arc-plugin-host/ — wasmtime fuel+epoch budgets, guarded_host_call (Sprint-10)
  rust/spikes/     — SEPARATE workspace (not in rust/Cargo.toml)
                     floem-editor, gpui-editor both have shell_port.rs

Python (v1 shippable):
  python/src/agent_runtime_cockpit/web/routes.py — HITL routes live
  cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
  → 230 passed (gate: must stay green)

spike harness (rust/spikes/spike-harness/):
  R1 discriminator live: P99 gates need p99 ≤ 1.1 frames AND 0% >2vsync raws
  36 tests pass
```

---

## 7. Constraints that never change

- **Native-only v2**: no Electron/WebView/Tauri fallback
- **v1 shippable**: `cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q` must stay at ≥230 passed
- **Additive only**: no renames or removals of existing events/CLI commands/API surfaces
- **No overclaiming**: CI runners = compile evidence only; Xvfb/llvmpipe numbers banned; M4 IS NOW PINNED (numbers are binding)
- **No framework imports** outside `arc-ui` and `rust/spikes/*-editor` throwaway crates
- **Deterministic security**: no LLM allow/deny decisions
- **Facade rule**: `arc_ui::kit` is the single swap point; no framework type may leak into other workspace crates

---

## 8. Disk pressure warning

The CLI's M4 machine is at ~99% disk (228GB drive, ~220Mi free most of the time).
This causes:
- `cargo test -p gpui-editor` → SIGBUS (gpui --test binary too large to link)
- `cargo build --features framework-gpui` in the main workspace → fails mid-build
- Recovery pattern: `rm -rf ~/cargo-spike-target/release` frees ~1-2GB temporarily

The open item "gpui shell_port tests must close before FINAL" requires a
machine with ≥5GB disk + ≥4GB RAM. K2 pixel work on the M4 also needs the
disk cleared first.

---

## 9. Your first action

1. Confirm you have read all 12 docs listed in §1.
2. Check `git log --oneline -5` on the branch to verify HEAD is `0ee9618e`.
3. State which phase you will execute (K2 requires display on M4 — if you
   are in a headless container, you can work on: K2 rust structure headless
   parts, K3 protocol/CI prep, K4 model-side wiring, or baton updates).
4. Update `docs/planning/arc-v2-baton.md` when you hand back.
5. Provide a git bundle if you produce commits the CLI needs.
