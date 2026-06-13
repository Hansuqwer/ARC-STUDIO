# ARC v2 — macOS Evidence Ledger

Date: 2026-06-13
Branch: `arc-v2/sprint-1-protocol-bridge`
Current synced baseline: `6578db8`

This ledger indexes committed macOS evidence. It is a navigation aid, not a new
source of truth that overrides the underlying reports.

## Framework selection / K phases

| Area | Evidence |
|---|---|
| K1 gpui feature flag | `0ee9618e`; `rust/arc-ui/Cargo.toml`; `rust/deny.toml` |
| K2 window / NO_COLOR / B1 | `900d38d1`; `reports/b1-cold-start.json`; baton K2 evidence |
| G5 VoiceOver | `e3b2a5a`; `reports/evidence/k3-gpui-macos-evidence.json`; `reports/spike-gpui.json` |
| G6 IME | `4e04bcde`; `reports/evidence/g6-ime-ja-screenshot-2026-06-13.png`; `reports/spike-gpui.json` |
| G7 Bidi | `7287dfa`; `reports/spike-gpui-bidi.png`; `reports/spike-gpui.json` |
| K4 Event Stream panel | `a9f816c1`; `rust/arc-dock/src/event_stream.rs`; baton K4 evidence |
| G8 sustainability | `276b0f60`; `reports/spike-gpui.json` G8 row |

## M5–M7 baseline evidence

| Area | Evidence |
|---|---|
| M5 Editor visible baseline | `b58c6a99`; `reports/evidence/m5-m6-m7-panels-2026-06-13.png` |
| M6 Workspace visible baseline | `b58c6a99`; same screenshot |
| M7 Terminal visible baseline | `b58c6a99`; same screenshot |
| Controller scaffolds/tests | `e1406d80`; 83 tests reported by local CLI; clippy/facade clean |

## M8–M10 baseline evidence

| Area | Evidence |
|---|---|
| M8 editor keyboard routing | `6578db8`; `reports/evidence/m8-editor-dirty-2026-06-13.png` |
| M9 workspace expand | `6578db8`; `reports/evidence/m9-workspace-expand-2026-06-13.png` |
| M9 file open into editor | `6578db8`; `reports/evidence/m9-file-open-in-editor-2026-06-13.png` |
| M10 terminal running prompt | `6578db8`; terminal prompt visible in all three M8/M9 screenshots |
| M8–M10 code/tests | `c663f61b`; 31 arc-shell + 57 other tests reported by local CLI; clippy/facade clean |

## Remaining macOS polish evidence to add

| Future phase | Evidence expected |
|---|---|
| M11 UX/interaction polish | interaction screenshots, UX-state table, command outputs |
| M12 a11y/IME/theme polish | VoiceOver/IME/theme screenshots, a11y tests |
| M13 certification | performance/reliability/security report, final macOS evidence summary |

## Deferred final-selection evidence

| Area | Status |
|---|---|
| Linux session | deferred until macOS polish is complete |
| Windows-gap decision | deferred until macOS polish is complete |
