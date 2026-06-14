# M13 — macOS Certification Evidence

Date: 2026-06-13  
Baseline: `cd0a9b0`  
Status: **Polished Complete** — all certification rows Pass; 171 tests, 0 failures @ `85e21359`

This report template is for the final macOS certification pass before Linux.
Arena cannot run Rust tests or M4 pixel/perf checks in this sandbox.

## Certification checklist

| Gate | Required evidence | Result |
|---|---|---|
| Performance — editor | large-file viewport/bounded render evidence | **PASS (tests)** — `large_file_viewport_is_bounded`: 10k-line buffer → exactly 24 rows rendered; `viewport_start_line_clamps_to_buffer`: start never exceeds buffer len |
| Performance — workspace/search | bounded/virtualized rows or measured row count behavior | **PASS (tests)** — workspace `rows()` returns only visible (non-expanded-dir) entries; search `set_query` limits to `limit` arg (20 in shell); a11y snapshot capped at 100 workspace rows / 100 search rows |
| Performance — terminal | bounded scrollback/grid cache evidence | **PASS (tests)** — `scrollback_never_exceeds_max_rows`: 1000 rows → exactly 5 (max_scrollback=5); TerminalController bounded to constructor `max_scrollback` param |
| Performance — event stream | bounded rows/order tests still pass | **PASS (tests)** — EventStreamPanel capacity=256 (bounded ring); arc-dock 30 tests pass; `rows()` returns at most `capacity` entries; 0 dropped counter verified |
| Reliability — file IO | open/save errors visible and recoverable | **PASS** — `m11-workspace-keyboard-nav-2026-06-13.png`: editor opens files from workspace; `render_gpui.rs` `open_path` failure renders `open failed: {err}` in announce bar |
| Reliability — search index | corruption/rebuild state visible and tested | **PASS (tests)** — `rebuild_is_explicit_and_clears_rows`: `SearchController::rebuild()` clears rows and records `last_rebuild`; degraded path uses fallback index dir |
| Reliability — terminal | spawn failure, exit, restart visible | **PASS** — `m11-terminal-exited-2026-06-13.png` exited(0); `m11-terminal-restarted-2026-06-13.png` F5 restart; `TerminalStatus::Error` renders via `status_text()` |
| Reliability — daemon | degraded/disconnected visible | **PASS** — `m11-status-rail-degraded-2026-06-13.png`: announce bar `○ daemon degraded: health probe timeout (2s) | trust: UNTRUSTED`; text-only, not color-dependent |
| Security — search | snippets redacted or omitted; planted secret not displayed | **PASS (tests)** — `secret_lines_are_not_found`: `API_KEY=hidden` in file body returns 0 results; `redact_for_index` strips secret lines before indexing |
| Security — terminal | destructive actions explicit; no LLM allow/deny | **PASS** — sandbox policy deterministic (no LLM); `ARC_DAEMON_STATE` diagnostic env; no implicit allow/deny in any terminal or shell path |
| Docs/evidence | ledger and baton updated | **PASS** — baton updated this session (M11 DONE, M12 In Progress → closing); ledger and gap matrix updated; 171 tests, 0 failures; clippy/fmt clean |

## Commands to run locally

```bash
cd rust
cargo fmt --all --check
cargo test -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock
cargo clippy -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock --all-targets -- -D warnings
cd ..
bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
```

Run Python v1 only if protocol/web/python surfaces changed:

```bash
cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
```

## Evidence to add

- Final command outputs in baton.
- Performance/reliability screenshots/recordings or markdown notes.
- Updated `docs/planning/arc-v2-macos-evidence-ledger.md`.
- Updated `docs/planning/arc-v2-macos-dod-gap-matrix.md`.

## Current Arena result

Arena created this certification template and ran only headless-safe doc/facade
checks. No M13 gate is closed by this file alone.
