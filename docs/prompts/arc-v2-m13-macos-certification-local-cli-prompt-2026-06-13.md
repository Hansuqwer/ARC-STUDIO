# ARC v2 M13 — macOS Certification Local CLI Prompt

## Goal

Close macOS performance, reliability, security, docs, and evidence-ledger gaps before Linux.

## Read first

- `AGENTS.md`, `docs/planning/arc-v2-baton.md`
- `docs/planning/arc-v2-macos-dod-gap-matrix.md`
- `docs/planning/arc-v2-macos-evidence-ledger.md`

## Required work

1. Performance: editor large-file viewport; bounded workspace/search rows; bounded terminal scrollback; event stream rows remain bounded.
2. Reliability: file IO errors visible; search index corruption/rebuild explicit; terminal spawn failure/restart visible; daemon degraded visible.
3. Security: search snippets redaction-safe; terminal destructive actions explicit; no secrets in evidence.
4. Evidence ledger: `docs/planning/arc-v2-macos-evidence-ledger.md` updated with M11–M13 artifacts.
5. Final macOS report: `reports/evidence/m13-macos-certification-2026-06-13.md`.

## Verification

```bash
cd rust && cargo fmt --all --check
cargo test -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock
cargo clippy -p arc-shell -p arc-ui -p arc-editor -p arc-workspace -p arc-index -p arc-terminal -p arc-dock --all-targets -- -D warnings
cd .. && bash scripts/check-arc-ui-facade.sh
bash scripts/check-banned-claims.sh docs/planning docs/prompts reports
cd python && PYTHONPATH=src uv run pytest tests/protocol tests/web -q
```
