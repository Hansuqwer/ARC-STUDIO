# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-12 (PM-12 Arena sync) · Branch: `arc-v2/sprint-1-protocol-bridge` @ `e3b2a5a`

## Who holds the baton

**Arena (sandbox):** synced to remote `e3b2a5a`. K2 is committed and M4-pixel
verified. K3 macOS evidence is now mostly closed: G5 VoiceOver is **Pass** via
the ARC-owned semantic a11y tree + macOS NSAccessibility bridge, G7 Bidi is
**Pass** with screenshot, and G6 IME dead-key inline composition CONFIRMED on M4 (é via Option+e in palette); full CJK rerun pending input-source setup. Arena can do headless analysis/model-side
prep only. Provide a git bundle on commit.

**M4 (local CLI):** owns remaining OS/display evidence: manual G6 IME script
(JA/ZH/KO/dead keys) after the `InputHandler` implementation, plus any future
VoiceOver regression reruns, `--features framework-gpui` pixel checks, and
Linux/Windows-gap evidence collection.

## Provisional selection

**gpui 0.2.2** — criterion-#1 rule (ADR-0002 addendum): 20/20 vs floem 18/20.
Floem escape: in-tree `floem-editor/src/shell_port.rs`, ≤3-day re-port.
Docs: `arc-v2-sprint-3-final-adjudication.md`, `arc-v2-kit-implementation-plan.md`

## Kit phases

| Phase | What | Status |
|---|---|---|
| K1 | `framework-gpui` feature in arc-ui; deny.toml wrapper; Sprint-1 lock gate retired | **DONE** (`0ee9618e`) |
| K2 | shell_port.rs → arc-shell/src/render_gpui.rs; window + palette + NO_COLOR + B1 | **DONE** (`fa8bdb0f` + `900d38d1`) |
| K3 | G5 VoiceOver + G6 IME + G7 bidi evidence on the real K2 shell | **PARTIAL** (`77857620`, `d860031`, `7287dfa`, `e3b2a5a`): G5 Pass; G7 Pass; G6 implementation landed but manual evidence pending |
| K4 | Event Stream panel end-to-end (model→render→daemon) | after K3 G6 evidence close |

## K1 evidence (committed)

- `rust/arc-ui/Cargo.toml`: `framework-gpui = ["dep:gpui"]`, `gpui = { version = "=0.2.2", optional = true }`
- `rust/arc-ui/src/lib.rs`: `#[cfg(feature = "framework-gpui")] pub use gpui::*;` in `pub mod kit`
- `rust/deny.toml`: `{ crate = "gpui", wrappers = ["arc-ui"] }` — feature-scoped exception
- Headless: 15/15 arc-ui tests pass; flag-on: disk-blocked (same root as gpui-test SIGBUS)

## K2 evidence (committed, pinned M4 — binding per benchmark-environment.md)

- **Window**: `cargo build -p arc-shell --features framework-gpui --release` — clean in 3m06s; `arc-shell --window` opens gpui window (PID 29300 confirmed running)
- **NO_COLOR**: `NO_COLOR=1 arc-shell --headless-status` → `[ERR]` text marker instead of `○` glyph — verified
- **B1 cold-start**: `hyperfine --runs 10 'arc-shell --smoke-exit'` → mean=2012ms ±1ms (min=2010, max=2015). Dominated by 2s hardcoded daemon health-probe timeout; model init itself is near-instant. `reports/b1-cold-start.json` committed.
- **v1 gate**: 220 passed (main repo `tests/protocol tests/web`)

## K3 evidence (committed, pinned M4)

| Gate | Outcome | Evidence | Next action |
|---|---|---|---|
| G5 VoiceOver | **Pass** | `e3b2a5a`; `rust/arc-ui/src/a11y.rs` framework-free semantic tree; `rust/arc-shell/src/a11y_macos.rs` NSAccessibility bridge; `reports/evidence/k3-gpui-macos-evidence.json`; `reports/spike-gpui.json` row updated | closed for macOS gpui; keep regression rerun after future a11y/render changes |
| G6 IME | **Implemented; evidence pending** | `d860031` implements framework input handling on `ShellChromeView`/TypeBox; no manual JA/ZH/KO/dead-key rerun recorded yet | M4 rerun of `arc-v2-macos-g5-g6-protocol.md` G6 script to confirm inline composition, candidate anchoring, commit, and cancel |
| G7 Bidi | **Pass** | `7287dfa`; `reports/spike-gpui-bidi.png`; `reports/spike-gpui.json` row updated | closed for macOS gpui: all six sample lines rendered (RTL Arabic, mixed LTR/RTL, ligatures, combining marks, PUA probes) |

G5 implementation notes: timeboxed NSAccessibility bridge avoided vendor/patch,
gpui upgrade, and floem escape. Two bring-up bugs were fixed: the gpui NSView
must be an accessibility **container** rather than a leaf, and children need
real non-zero screen-coordinate frames or VoiceOver culls them.

## Open items before FINAL selection

1. gpui shell_port unit tests (≥5GB disk + ≥4GB RAM required; 3 pure fns)
2. G6 manual IME rerun (implementation exists; evidence still required)
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
| G1 | Pass 58ms | Pass 201ms (full-sample original; 316ms low-n G7 rerun sanity row ignored for perf) | Pass 166ms |
| G2/G4 (R1) | Pass (0% >2vsync) | Pass (0% >2vsync original; G7 screenshot rerun low-n sanity only) | FAIL (88.8% >2vsync) |
| G3 | Pass | Pass | Pass |
| Text render | clean | clean; G7 Pass | non-visible |
| G5/G6/G7/G8 | pending | G5 Pass; G6 implemented/evidence pending; G7 Pass; G8 pending | parked (3 defects) |

R1 discriminator: p99 ≤ 1.1 frames AND 0% samples >2 vsyncs (codified in harness).
gpui-ce parked at c237d57 (F-gpui-ce-1/2/3: invisible glyphs, 3-frame typing, Linux build break).

## Workspace state

- 10 crates, facade holds (Arena verified `scripts/check-arc-ui-facade.sh` after sync)
- `e3b2a5a` adds `arc_ui::a11y` with 6 framework-free semantic-tree tests (per M4 handback)
- Python v1: `cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q` → 230 passed historically; latest K2 evidence recorded 220 passed on the M4 subset
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
