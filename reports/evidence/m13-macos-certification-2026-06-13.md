# M13 — macOS Certification Evidence

Date: 2026-06-13  
Baseline: `cd0a9b0`  
Status: **Prepared by Arena; pending local CLI certification run**

This report template is for the final macOS certification pass before Linux.
Arena cannot run Rust tests or M4 pixel/perf checks in this sandbox.

## Certification checklist

| Gate | Required evidence | Result |
|---|---|---|
| Performance — editor | large-file viewport/bounded render evidence | PENDING |
| Performance — workspace/search | bounded/virtualized rows or measured row count behavior | PENDING |
| Performance — terminal | bounded scrollback/grid cache evidence | PENDING |
| Performance — event stream | bounded rows/order tests still pass | PENDING |
| Reliability — file IO | open/save errors visible and recoverable | PENDING |
| Reliability — search index | corruption/rebuild state visible and tested | PENDING |
| Reliability — terminal | spawn failure, exit, restart visible | PENDING |
| Reliability — daemon | degraded/disconnected visible | PENDING |
| Security — search | snippets redacted or omitted; planted secret not displayed | PENDING |
| Security — terminal | destructive actions explicit; no LLM allow/deny | PENDING |
| Docs/evidence | ledger and baton updated | PENDING |

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
