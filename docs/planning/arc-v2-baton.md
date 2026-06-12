# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-12 (PM-8) · Branch: `arc-v2/sprint-1-protocol-bridge` @ `0ee9618e`

## Who holds the baton

**Arena (sandbox):** K2 (pixel shell) — requires M4/display. If headless, do
K2 structure + K3/K4 model-side prep. Provide a git bundle on commit.

**M4 (local CLI):** K2 pixel work (window, keyboard palette, NO_COLOR, B1).
Blocked on disk (~220Mi free — clear `~/cargo-spike-target` before building).
Also: gpui shell_port unit tests (SIGBUS disk-blocked; needs ≥5GB + ≥4GB RAM).

## Provisional selection

**gpui 0.2.2** — criterion-#1 rule (ADR-0002 addendum): 20/20 vs floem 18/20.
Floem escape: in-tree `floem-editor/src/shell_port.rs`, ≤3-day re-port.
Docs: `arc-v2-sprint-3-final-adjudication.md`, `arc-v2-kit-implementation-plan.md`

## Kit phases

| Phase | What | Status |
|---|---|---|
| K1 | `framework-gpui` feature in arc-ui; deny.toml wrapper; Sprint-1 lock gate retired | **DONE** (0ee9618e) |
| K2 | shell_port.rs → arc-shell/src/render_gpui.rs; window + palette + NO_COLOR + B1 | **NEXT (M4)** |
| K3 | G5 VoiceOver + G6 IME + G7 bidi evidence on the real K2 shell | after K2 |
| K4 | Event Stream panel end-to-end (model→render→daemon) | after K2 |

## K1 evidence (committed)

- `rust/arc-ui/Cargo.toml`: `framework-gpui = ["dep:gpui"]`, `gpui = { version = "=0.2.2", optional = true }`
- `rust/arc-ui/src/lib.rs`: `#[cfg(feature = "framework-gpui")] pub use gpui::*;` in `pub mod kit`
- `rust/deny.toml`: `{ crate = "gpui", wrappers = ["arc-ui"] }` — feature-scoped exception
- Headless: 15/15 arc-ui tests pass; flag-on: disk-blocked (same root as gpui-test SIGBUS)

## Open items before FINAL selection

1. gpui shell_port unit tests (≥5GB disk + ≥4GB RAM required; 3 pure fns)
2. K3 evidence rows: G5 VoiceOver + G6 IME + G7 bidi screenshot
3. Linux session (owner hardware): G1–G4 + Orca + fcitx5/ibus
4. Windows-gap decision recorded per os-sequencing doc

## Facade scores (criterion #1, committed in spike reports)

| | floem 0.2.0 | gpui 0.2.2 |
|---|---|---|
| F-LOC | 5 (214) | 5 (190) |
| F-CONCEPT | 5 | 5 |
| F-EVENT | 4 (signal mirror) | 5 (direct) |
| F-SWAP | 4 | 5 |
| **Total** | **18** | **20** |

## Spike results summary (M4, binding per benchmark-environment.md)

| Gate | floem 0.2 | gpui 0.2.2 | gpui-ce c237d57 |
|---|---|---|---|
| G1 | Pass 58ms | Pass 201ms | Pass 166ms |
| G2/G4 (R1) | Pass (0% >2vsync) | Pass (0% >2vsync) | FAIL (88.8% >2vsync) |
| G3 | Pass | Pass | Pass |
| Text render | clean | clean | non-visible |
| G5/G6/G7/G8 | pending | pending | parked (3 defects) |

R1 discriminator: p99 ≤ 1.1 frames AND 0% samples >2 vsyncs (codified in harness).
gpui-ce parked at c237d57 (F-gpui-ce-1/2/3: invisible glyphs, 3-frame typing, Linux build break).

## Workspace state

- 10 crates, 124 tests, clippy 0, fmt clean, deny clean, facade holds
- Python v1: `cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q` → 230 passed
- arc-plugin-host: Sprint-10 core (15 tests; wasmtime fuel+epoch; guarded_host_call fail-closed)
- Supply chain: deny.toml live, all 4 checks PASS after real fixes (tempfile, tantivy 0.25, publish=false)

## Sync-loss rule

Arena often can't push. Always provide a **git bundle**. Never assume a bare
commit hash is in the remote. CLI verifies with `git bundle verify` then
`git fetch <bundle> && git merge --ff-only`.

## Standing constraints

Native-only v2 · v1 shippable (230 tests) · additive protocol · deterministic
security · no framework imports outside arc-ui and rust/spikes · no overclaiming
(M4 IS pinned; CI runners = compile evidence only) · facade rule (arc_ui::kit
is the single swap point).
