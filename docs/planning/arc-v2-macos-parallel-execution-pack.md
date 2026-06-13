# ARC v2 — M11/M12/M13 Parallel Execution Pack

Date: 2026-06-13  
Baseline: `cd0a9b0`  
Scope: execute macOS-native polish work in parallel before Linux.

This pack splits M11/M12/M13 into non-conflicting workstreams. It is designed for
local CLI/M4 execution because pixel, VoiceOver, IME, terminal, and performance
evidence cannot be produced in the Arena sandbox.

## Workstream A — M11 UX states + interaction polish

Primary owner: local CLI with M4 display.

Files likely touched:

- `rust/arc-shell/src/render_gpui.rs`
- `rust/arc-shell/src/editor_controller.rs`
- `rust/arc-shell/src/workspace_controller.rs`
- `rust/arc-shell/src/search_controller.rs`
- `rust/arc-shell/src/terminal_controller.rs`
- `rust/arc-dock/src/event_stream.rs`

Outputs:

- `reports/evidence/m11-ux-interaction-polish-2026-06-13.md`
- screenshots/recordings referenced by that report

Acceptance:

- F6/Shift-F6 cycles all landmarks.
- Workspace/editor/terminal receive only focused keys.
- Palette opens/closes globally without corrupting focused surface state.
- Editor/workspace/search/terminal/event stream/status rail all expose explicit UX states.
- Palette actions and direct interactions call the same controller paths.

## Workstream B — M12 Accessibility + IME + theme polish

Primary owner: local CLI with M4 display and VoiceOver/IME input sources.

Files likely touched:

- `rust/arc-ui/src/a11y.rs`
- `rust/arc-shell/src/a11y_macos.rs`
- `rust/arc-shell/src/render_gpui.rs`
- `rust/arc-shell/src/render_editor_gpui.rs`
- `rust/arc-shell/src/render_workspace_gpui.rs`
- `rust/arc-shell/src/render_terminal_gpui.rs`

Outputs:

- `reports/evidence/m12-a11y-ime-theme-polish-2026-06-13.md`
- VoiceOver/IME/theme screenshots or recordings referenced by that report

Acceptance:

- VoiceOver sees editor, workspace selected row, search field/results, event stream row, terminal status/current line.
- Editor inline IME commit/cancel is confirmed.
- Palette IME regression still passes.
- NO_COLOR and high-contrast evidence covers editor/workspace/search/terminal/event stream/status.
- `arc_ui::a11y` remains the semantic source of truth; macOS bridge stays a thin translation layer.

## Workstream C — M13 macOS certification

Primary owner: local CLI. Can run partly in parallel, but final report depends on
M11/M12 evidence paths.

Files likely touched:

- `docs/planning/arc-v2-macos-evidence-ledger.md`
- `docs/planning/arc-v2-macos-dod-gap-matrix.md`
- `docs/planning/arc-v2-baton.md`
- `reports/evidence/m13-macos-certification-2026-06-13.md`

Outputs:

- `reports/evidence/m13-macos-certification-2026-06-13.md`
- updated evidence ledger and DoD gap matrix

Acceptance:

- Editor large-file viewport evidence recorded.
- Workspace/search row boundedness or virtualization evidence recorded.
- Terminal scrollback bound evidence recorded.
- File IO/search/terminal/daemon reliability states recorded.
- Search snippet redaction evidence recorded.
- Evidence ledger links every macOS claim to screenshot/recording/test/report.

## Integration order

1. M11 and M12 may run in parallel if they avoid editing the same `render_gpui.rs`
   sections simultaneously.
2. M13 may prepare reports in parallel, but final certification must wait for
   M11/M12 evidence paths.
3. Serialize final edits to `docs/planning/arc-v2-baton.md` and evidence ledger.

## Verification bundle

Run after each workstream and again after integration:

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock
cargo clippy -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

Do not start Linux until M11/M12/M13 are closed or explicitly accepted with
residual macOS gaps.
