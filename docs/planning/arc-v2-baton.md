# arc-v2 baton state (update this file at every handback)

Last updated: 2026-06-13 (Arena M11–M13 prep) · Branch: `arc-v2/sprint-1-protocol-bridge` @ `cd0a9b0`

## Who holds the baton

**Arena (sandbox):** synced to remote `cd0a9b0`. macOS native path is Baseline
Complete through M10. This turn prepared M11/M12/M13 parallel execution artifacts
and evidence templates, but did not close those phases because M4 pixel,
VoiceOver, IME, performance, and Rust toolchain evidence are required.

New/updated Arena artifacts this turn:

- `docs/planning/arc-v2-macos-parallel-execution-pack.md`
- `reports/evidence/m11-ux-interaction-polish-2026-06-13.md`
- `reports/evidence/m12-a11y-ime-theme-polish-2026-06-13.md`
- `reports/evidence/m13-macos-certification-2026-06-13.md`
- `docs/planning/arc-v2-macos-evidence-ledger.md`
- `docs/planning/arc-v2-macos-dod-gap-matrix.md`

**M4/local CLI:** owns M11–M13 execution evidence. Linux remains deferred until
macOS polish is closed or explicitly accepted with residual gaps.

## Provisional selection

**gpui 0.2.2** — criterion-#1 rule (ADR-0002 addendum): 20/20 vs floem 18/20.
Floem escape: in-tree `floem-editor/src/shell_port.rs`, ≤3-day re-port.
Docs: `arc-v2-sprint-3-final-adjudication.md`, `arc-v2-kit-implementation-plan.md`.

## macOS kit + panel phases

| Item | Status |
|---|---|
| K1 feature flag | **DONE** (`0ee9618e`) |
| K2 window/pixel/B1 | **DONE** (`fa8bdb0f`, `900d38d1`) |
| K3 G5/G6/G7 | **DONE** — G5 VoiceOver Pass, G6 IME JA inline Pass, G7 Bidi Pass (`e3b2a5a`, `4e04bcde`, `7287dfa`) |
| K4 Event Stream panel | **DONE** (`a9f816c1`) |
| G8 sustainability | **DONE** (`276b0f60`) |
| M5 Editor in pixels | **Baseline Complete** (`b58c6a99`) |
| M6 Workspace + file open/search scaffold in pixels | **Baseline Complete** (`b58c6a99`) |
| M7 Terminal panel in pixels | **Baseline Complete** (`b58c6a99`) |
| M8 Editor polish baseline | **Baseline Complete** (`6578db8`) |
| M9 Workspace/Search polish baseline | **Baseline Complete** (`6578db8`) |
| M10 Terminal polish baseline | **Baseline Complete** (`6578db8`) |
| M11 UX states + interaction polish | **PREPARED; pending M4 evidence** |
| M12 Accessibility + IME + theme polish | **PREPARED; pending M4 evidence** |
| M13 macOS certification pass | **PREPARED; pending local CLI certification** |

## Current macOS evidence highlights

- K3: G5/G6/G7 pass with committed evidence (`reports/evidence/k3-gpui-macos-evidence.json`, `reports/evidence/g6-ime-ja-screenshot-2026-06-13.png`, `reports/spike-gpui-bidi.png`).
- K4: Event Stream panel uses the same `EventStreamPanel::on_event` path for fixture and live SSE; `arc-dock` tests reported green.
- M5–M7: `reports/evidence/m5-m6-m7-panels-2026-06-13.png` shows editor, workspace, terminal baseline in pixels.
- M8–M10: `reports/evidence/m8-editor-dirty-2026-06-13.png`, `reports/evidence/m9-workspace-expand-2026-06-13.png`, and `reports/evidence/m9-file-open-in-editor-2026-06-13.png` show editor keyboard routing, workspace expand/file open, and terminal prompt.

## M11–M13 prepared execution artifacts

| Phase | Artifact | Purpose |
|---|---|---|
| M11 | `reports/evidence/m11-ux-interaction-polish-2026-06-13.md` | Fill with UX-state and interaction evidence after M4 run |
| M12 | `reports/evidence/m12-a11y-ime-theme-polish-2026-06-13.md` | Fill with VoiceOver/IME/theme evidence after M4 run |
| M13 | `reports/evidence/m13-macos-certification-2026-06-13.md` | Fill with performance/reliability/security/certification evidence |
| Parallel pack | `docs/planning/arc-v2-macos-parallel-execution-pack.md` | Assign M11/M12/M13 local workstreams |
| Ledger | `docs/planning/arc-v2-macos-evidence-ledger.md` | Evidence index; update after M11–M13 |
| Gap matrix | `docs/planning/arc-v2-macos-dod-gap-matrix.md` | DoD closure tracking |

## Open items before FINAL selection

1. Finish macOS polish M11–M13 on the M4/local CLI.
2. **Linux session** (owner hardware): G1–G4 + Orca a11y + fcitx5/ibus IME.
3. **Windows-gap decision** recorded per os-sequencing doc.

Linux remains deferred until M11–M13 are closed or residual macOS gaps are explicitly accepted.

## Facade scores (criterion #1, binding)

| | floem 0.2.0 | gpui 0.2.2 |
|---|---|---|
| F-LOC | 5 (214) | 5 (190) |
| F-CONCEPT | 5 | 5 |
| F-EVENT | 4 (signal mirror) | 5 (direct) |
| F-SWAP | 4 | 5 |
| **Total** | **18** | **20** |

## Verification in this Arena turn

Arena ran headless-safe checks only:

- `bash scripts/check-arc-ui-facade.sh` → OK
- `bash scripts/check-banned-claims.sh docs/planning docs/prompts reports` subset → OK
- `git diff --check` → OK

Not run in Arena: Rust fmt/test/clippy and all M4 pixel/VoiceOver/IME/performance checks.

## Sync-loss rule

Arena often can't push. Always provide a **git bundle**. Never assume a bare
commit hash is in the remote. CLI verifies with `git bundle verify` then
`git fetch <bundle> && git merge --ff-only`.

## Standing constraints

Native-only v2 · v1 shippable · additive protocol · deterministic security · no
framework imports outside arc-ui and rust/spikes · no overclaiming (M4 IS pinned;
CI runners = compile evidence only) · facade rule (`arc_ui::kit` is the single
swap point).
