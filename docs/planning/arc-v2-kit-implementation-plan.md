# arc_ui::kit Implementation Plan — framework-gpui (provisional)

Companion to `arc-v2-sprint-3-final-adjudication.md`. Scope: make the facade
real for gpui behind a feature flag, render the existing tested models, keep
the floem escape warm. All work reversible (flag off = today's headless build).

## Phase K1 — flag + kit surface (no behavior change when off)

```toml
# rust/arc-ui/Cargo.toml
[features]
default = []                       # headless stays the default everywhere
framework-gpui = ["dep:gpui"]
[dependencies]
gpui = { version = "=0.2.2", optional = true }
```

```rust
// rust/arc-ui/src/lib.rs — kit stays the ONLY framework import site
#[cfg(feature = "framework-gpui")]
pub mod kit {
    pub use gpui::*;
}
```

Gate updates (same commit): facade CI script already passes (gpui import is
inside arc-ui); `deny.toml` bans list gets a feature-scoped exception —
change `deny = [{ crate = "gpui" }...]` to allow gpui ONLY as an arc-ui
optional dep (cargo-deny `wrappers = ["arc-ui"]`); main-workspace
`Cargo.lock` WILL now contain gpui — the Sprint-1 "no framework in lock"
gate is formally retired by this plan (it did its job: nothing depended on
a framework before the evidence said so). CI grep gate stays (source-level).

## Phase K2 — promote the port (throwaway becomes seed)

`rust/spikes/gpui-editor/src/shell_port.rs` (190 lines, F-CONCEPT 0 leaks)
is the seed of `rust/arc-shell/src/render_gpui.rs` (cfg-gated module):
window + the four regions + palette overlay + status rail + focus ring,
all reading the EXISTING `ShellModel` (which already carries daemon state
via Sprint-1's client and supervisor policies). `arc-shell --headless-*`
modes keep working without the feature; `arc-shell --window` requires it.

DoD for K2 (from Sprint-2's deferred gates, now satisfiable):
- window opens on macOS (M4, pinned) — Linux/Windows rows per os-sequencing;
- keyboard-only palette WORKS IN PIXELS (the model tests already prove the
  logic; this proves the wiring);
- NO_COLOR/high-contrast visibly switch;
- daemon Degraded strip renders from a live kill test;
- cold-start B1 measured for real (hyperfine, pinned machine, honesty rules).

## Phase K3 — evidence rows on the real shell

G5 VoiceOver / G6 IME / G7 bidi per `arc-v2-macos-g5-g6-protocol.md`, run
against the K2 shell (better evidence target than the spike scaffold — same
framework, real chrome). These rows complete the macOS half of FINAL
selection; Linux session completes the rest.

## Phase K4 — first panel in pixels (proof of the whole stack)

Event Stream panel: `arc-dock::EventStreamPanel` (already replay-parity
tested) + `views::EventTable` line discipline + per-run SSE from the live
daemon. One panel end-to-end validates model→render→daemon before the
remaining panels are mechanical.

## Sequencing & ownership

| Phase | Where | Blocked by |
|---|---|---|
| K1 | sandbox or M4 (no display needed for flag plumbing + CI updates) | nothing — can start now |
| K2 | M4 | K1 |
| K3 | M4 | K2 |
| K4 | M4 (render) over sandbox-tested models | K2 |

Escape hatch at every phase: flag off, floem `shell_port.rs` in-tree,
re-port ≤3 days (adjudication §3). Sprint 4+ editor rendering stays gated
on FINAL selection — K-phases are shell chrome only.
