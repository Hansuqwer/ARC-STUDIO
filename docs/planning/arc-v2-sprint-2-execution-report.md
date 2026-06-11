# ARC v2 — Sprint 2 Execution Report (native shell skeleton)

Date: 2026-06-11 · Branch: `arc-v2/sprint-1-protocol-bridge` · Follows checkpoint #1
(`arc-v2-checkpoint-1-decision-memo.md`: Sprint 2 authorized; C1 resolved via the
AGENTS.md additive exception).

Environment: sandboxed Linux container (x86_64), rustc/cargo 1.96.0. **No display
server is available here**, and — by design — **no UI framework is selected yet**
(ADR-0002 spike = Sprint 3, gates G1–G8). Sprint 2 therefore delivers the shell as a
**framework-free, fully-tested model** plus a headless binary, exactly the split the
facade architecture demands: when Sprint 3 picks a framework, only `arc_ui::kit` and
a thin render layer change; every behavior shipped this sprint keeps its tests.

## What was built (all additive; rollback = delete `rust/arc-ui`, `rust/arc-shell`)

| Crate | Contents |
|---|---|
| `rust/arc-ui` (facade) | `kit` (the ONLY permitted framework import site — currently empty, no default framework feature); `Theme` (NO_COLOR per no-color.org + high-contrast + text status markers); `CommandRegistry` (deterministic order, duplicate-rejecting, `Enablement::Disabled{reason}` so the palette can say *why* — review §11.2); `PaletteModel` (nucleo-matcher fuzzy match, full keyboard state machine, SR announcements); `FocusRing` (F6/Shift+F6 deterministic landmark cycling); `Keymap` (chord normalization, conflict-as-error, import/export round-trip for parity tests) |
| `rust/arc-shell` (lib + bin) | `ShellModel` (regions, palette wiring, status rail with producer-truth daemon state, daemon-gated commands); `supervisor` (Backoff 250ms→30s; **CircuitBreaker 5-restarts/5-min** — review §13 Sprint-6 delta pulled forward; `await_healthy` 2s/10s budget); binary modes `--smoke-exit` / `--headless-status` |

## Exit-gate evidence (Sprint-2 gates, §3.4, adapted headless where honest)

1. **Keyboard-only palette: PASS (model-level).** open → type → arrow → execute →
   escape proven by tests incl.: best-match-first ("replay" → Replay Event Stream
   Fixture), Escape-closes-without-execute, disabled-command Enter → `Rejected{reason}`
   (palette stays open, reason announced), arrow announcements carrying
   name+category+state+shortcut. 15 arc-ui tests green.
2. **Deterministic focus traversal: PASS (model-level).** F6 order
   workspace→editor→dock→status with wrap, Shift+F6 reverse, jump-by-id; re-proof on
   the real framework tree is a Sprint-3 G5 item.
3. **High-contrast / NO_COLOR: PASS (demonstrated).** `NO_COLOR=1` swaps glyph markers
   for text (`[OK]/[WARN]/[ERR]`) — live output captured: status rail renders
   `[ERR] daemon degraded: …` under NO_COLOR, `●  daemon healthy` without.
4. **Degraded strip on health failure: PASS (live).** Without a daemon:
   `status rail: [ERR] daemon degraded: health probe timeout (2s) | trust: UNTRUSTED`.
   With the live daemon: `● daemon healthy`. Producer-truth from day one; trust state
   is never hidden.
5. **Cold/warm start recorded as measurement, not marketing.**
   `--smoke-exit` (model + single health probe, NO window): mean 3 ms (n=20, live
   daemon, container hardware) → `reports/cold-start-skeleton.json`, which carries an
   explicit honesty note: this bounds process+model overhead only; the real B1 gate
   runs after Sprint 3 on pinned hardware.
6. **App opens on macOS/Linux/Windows OR explicitly labels unsupported:** the binary
   prints "window rendering lands with the Sprint-3 framework decision (ADR-0002)" and
   exits 2 without flags — the no-window state is explicit, not silent. Per-OS window
   evidence transfers to Sprint 3 (it cannot honestly be produced before a framework
   exists; the planning package's own G-gates put windowed evidence in the spike).
7. **Facade holds:** `scripts/check-arc-ui-facade.sh` → OK; **0** `gpui|floem` refs in
   `Cargo.lock`; arc-ui declares no framework dependency (feature stubs are commented
   until ADR-0002 selects one — they cannot ship by accident).
8. **Hygiene:** clippy 0 warnings workspace-wide (`unwrap_used` deny held; `Iterator::next`
   confusables renamed `advance`/`focus_next`/`focus_prev`); 37 Rust tests green
   (14 protocol + 13 client + 15 arc-ui + 5 arc-shell, per-target totals).
9. **No v1 regressions:** `tests/protocol` + `tests/web` = **220 passed** (same as
   Sprint-1 exit). No canonical-file edits beyond the owner-approved one-paragraph
   C1 exception in `AGENTS.md`.

## Decisions recorded this sprint

- **C1 RESOLVED** (checkpoint #1, option from the planning package's
  `arc-v2-roadmap-phases-additive-patch.md`): `AGENTS.md` gained one additive
  paragraph blessing `docs/planning/` for v2 planning/evidence artifacts only;
  v1 status stays exclusively in `docs/roadmap.md`/`docs/phases.md`.
  Reversal = delete one paragraph.
- **Supervisor policy pulled forward:** circuit breaker + backoff are pure,
  tested policy objects now; the process-spawning loop attaches in Sprint 3 when
  there is a window to surface `CircuitOpen` in.
- **`Enablement::Disabled{reason}`** adopted as the registry-level contract so
  the §6.2 palette a11y block ("announces enabled/disabled state") and the
  review's "expose *why* disabled" both fall out of the type.

## What Sprint 2 deliberately did NOT do

No UI framework dependency; no window; no panels beyond the status-rail data path;
no editor; no performance claims beyond the labeled skeleton measurement; no new
daemon endpoints; no protocol changes.

## Next (blocked until owner confirms)

**Sprint 3 — framework spike (G1–G8)** requires: ADR-0002 addendum confirmation
(G8 sustainability gate + revised decision rule, review §6.1–6.2, owner item
ARC2-13) and **desktop hardware with a display server + GPU** — the spike's
render/IME/a11y gates cannot run in this sandbox. The spike consumes the models
shipped this sprint as its test harness (palette/focus/status-rail behaviors are
already specified as executable tests).
