# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-13 (Kiro CLI sync) · Branch: `arc-v2/sprint-1-protocol-bridge` @ `276b0f60`

## Who holds the baton

**Kiro CLI (local):** synced to remote `276b0f60`. K4 + G8 are committed. G6 CJK
manual evidence is the sole remaining open gate before FINAL selection. All headless
tests pass; Python v1 gate confirmed 220 passed.

**M4 (local CLI):** owns remaining OS/display evidence: G6 manual CJK IME rerun
(JA/ZH/KO — implementation exists at `d860031`, only manual confirmation required),
plus Linux session (G1–G4 + Orca + fcitx5/ibus) and Windows-gap decision.

## Provisional selection

**gpui 0.2.2** — criterion-#1 rule (ADR-0002 addendum): 20/20 vs floem 18/20.
Floem escape: in-tree `floem-editor/src/shell_port.rs`, ≤3-day re-port.
Docs: `arc-v2-sprint-3-final-adjudication.md`, `arc-v2-kit-implementation-plan.md`

## Kit phases

| Phase | What | Status |
|---|---|---|
| K1 | `framework-gpui` feature in arc-ui; deny.toml wrapper; Sprint-1 lock gate retired | **DONE** (`0ee9618e`) |
| K2 | shell_port.rs → arc-shell/src/render_gpui.rs; window + palette + NO_COLOR + B1 | **DONE** (`fa8bdb0f` + `900d38d1`) |
| K3 | G5 VoiceOver + G6 IME + G7 bidi evidence on the real K2 shell | **G5 Pass; G7 Pass; G6 impl done, manual CJK rerun pending** |
| K4 | Event Stream panel end-to-end (model→render→daemon) | **DONE** (`a9f816c1`) |
| G8 | Sustainability evidence (Zed Industries backing, release cadence) | **DONE** (`276b0f60`) |

## K4 evidence (committed `a9f816c1`)

- `rust/arc-shell/Cargo.toml`: `arc-dock = { path = "../arc-dock" }` added
- `rust/arc-shell/src/render_gpui.rs`:
  - `events: arc_dock::EventStreamPanel` + `live_rx: Option<Receiver<RunEvent>>` fields on `ShellChromeView`
  - `new()`: replay-seeds the panel from `protocol/fixtures/run-event-seq/tool-use-streaming` (18 events; `replay_dir` path)
  - `new()`: if `ARC_RUN_ID` set, spawns background `tokio` thread → `DaemonClient::stream_run_events` → `std::sync::mpsc` → `live_rx`
  - `render()`: drains `live_rx.try_iter()` via same `on_event` path as fixture replay (parity oracle holds); renders last 12 event rows with `display_line()` fixed-width discipline, surface-state header, and footer
  - `spawn_live_feed()`: pure fn, graceful no-op if daemon unreachable
- Facade: `arc-dock` has no `gpui`/`floem` Cargo dep; `check-arc-ui-facade.sh` passes
- arc-dock tests: 30 total (event_stream 3 + hitl 10 + runs 5 + state 3 + diff_review 9)
- Python v1: 220 passed (`tests/protocol tests/web`, confirmed 2026-06-13)

## G8 evidence (committed `276b0f60`)

- `reports/spike-gpui.json` G8Sustainability row updated: Pass
- Zed Industries: VC-funded company, 85k stars, full engineering team; not single-maintainer
- Release cadence: 0.2.0→0.2.1→0.2.2 in 2 weeks (Oct 2025)
- Vendoring cost: ~10 Zed sub-crates, 1 sprint per adjudication §3 plan, pre-approved
- G8 score: 9/20 vs floem 14/20 — factored in; criterion-#1 (facade) still governs selection

## K1–K3 evidence (see prior baton, unchanged)

- K2 B1 cold-start: 2012ms ±1ms (M4 pinned); `reports/b1-cold-start.json`
- G5 VoiceOver: Pass — `arc_ui::a11y` 6-test framework-free semantic tree + `arc-shell::a11y_macos` NSAccessibility bridge; VoiceOver navigates all 4 landmarks on M4
- G7 Bidi: Pass — `reports/spike-gpui-bidi.png`; all 6 sample lines rendered
- G6 dead-key: confirmed (é via Option+e in palette TypeBox on M4); full CJK pending

## Open items before FINAL selection

1. **G6 manual CJK rerun** (M4 required):
   - Add JA input source: System Settings → Keyboard → Text Input → Edit → + → Japanese → Romaji
   - Switch: Ctrl+Space → open `arc-shell --window` → Ctrl+Shift+P opens palette → type in Romaji → expect hiragana inline with underline
   - Record: inline vs floating, candidate anchoring, commit (Enter), cancel (Esc)
   - Repeat for ZH (Pinyin) and KO (2-Set) per `docs/planning/arc-v2-macos-g5-g6-protocol.md`
2. **gpui shell_port unit tests** (needs ≥5GB free disk): disk-blocked on current M4 (~28Gi free)
3. **Linux session** (owner hardware): G1–G4 + Orca a11y + fcitx5/ibus IME
4. **Windows-gap decision** recorded per os-sequencing doc

## Facade scores (criterion #1, binding)

| | floem 0.2.0 | gpui 0.2.2 |
|---|---|---|
| F-LOC | 5 (214) | 5 (190) |
| F-CONCEPT | 5 | 5 |
| F-EVENT | 4 (signal mirror) | 5 (direct) |
| F-SWAP | 4 | 5 |
| **Total** | **18** | **20** |

## Workspace state

- 10 crates, 30+ arc-dock tests, facade holds (check-arc-ui-facade.sh)
- Branch `arc-v2/sprint-1-protocol-bridge` @ `276b0f60` — ahead of stale baton (`e3b2a5a`)
- Python v1: 220 passed (2026-06-13, `tests/protocol tests/web`)
- arc-dock 30 tests; arc-shell headless tests pass; deny.toml clean

## Sync-loss rule

Arena often can't push. Always provide a **git bundle**. Never assume a bare
commit hash is in the remote. CLI verifies with `git bundle verify` then
`git fetch <bundle> && git merge --ff-only`.

## Standing constraints

Native-only v2 · v1 shippable (220 passed confirmed) · additive protocol · deterministic
security · no framework imports outside arc-ui and rust/spikes · no overclaiming
(M4 IS pinned; CI runners = compile evidence only) · facade rule (arc_ui::kit
is the single swap point).
