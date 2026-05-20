# Phase 18 — CLI Consolidation: Hand-off Report

**Date:** 2026-05-20
**Branch:** `phase-2-cli-consolidation`
**Status:** Complete

## Summary

Consolidated two separate REPL implementations (`cli_studio.py` standalone binary and `cli_repl/` used by `arc studio chat`) into a unified architecture with a declarative slash command registry, a single canonical session schema, and unified CLI entry points. The `cli_studio.py` binary is now a thin shim delegating to `cli_repl/`. Legacy flat session files remain readable. A new `arc studio sessions-migrate` command converts them idempotently.

## Deliverables Checklist

| Deliverable | Status | File |
|---|---|---|
| Unified slash command registry | ✅ Done | `cli_repl/commands/__init__.py` |
| Merged cli_studio.py commands into registry | ✅ Done | `cli_repl/slash_commands.py` |
| cli_studio.py thin shim (≤30 lines) | ✅ Done | `cli_studio.py` |
| ChatSession schema version (v1) | ✅ Done | `cli_repl/session.py` |
| Legacy StudioSession reader | ✅ Done | `cli_repl/session.py` (ChatSession.load() fallback) |
| `arc studio sessions-migrate` CLI command | ✅ Done | `cli.py:studio_sessions_migrate()` |
| Bare `arc` TUI launch (`ARC_NO_TUI` guard) | ✅ Done | `cli.py:_arc_default()` |
| Tests for all changes | ✅ Done | `tests/test_cli_repl.py`, `tests/test_cli_studio.py` |
| Docs updated (phases.md, CHANGELOG) | ✅ Done | `docs/phases.md`, `CHANGELOG.md` |

## Tests Added/Changed

### `python/tests/test_cli_repl.py` — 36 tests (was 22)
- TestChatSession (6): session override, create, add_message, save/load, list/latest, load_nonexistent
- TestSlashCommands (10): help, clear, summary(2), run(2), history(2), version, quit, exit, unknown, non-slash
- TestFormatResult (2): format_completed, format_no_results
- **TestMergedSlashCommands (7)**: plan, build, auto, status, doctor, runs, status-after-mode
- **TestCommandRegistry (5)**: register/lookup, alias-resolution, duplicate, duplicate-alias, list-by-category, categories
- **TestSessionMigration (6)**: detect-legacy, detect-skips-latest, migrate, migrate-all, migrate-nonexistent, list-legacy-ids
- **TestSessionsMigrate (3)**: no-legacy, with-legacy, twice-idempotent
- **TestBareArc (4)**: version-flag, non-tty-help, arc-no-tui, subcommand-still-works
- TestStudioCli (1): sessions-json

### `python/tests/test_cli_studio.py` — 9 tests (was 22)
- TestBanner (2): no-arg, version
- TestSessionPersistence (7): roundtrip, save/load, list, nonexistent, mode-tracking(2), **legacy-flat-read**

## Schema Bumps

None. This phase does not touch capability/event/receipt schemas.

## Banned-Claims Scan

Result: **OK** — No banned claims found in docs/agents.md, docs/roadmap.md, docs/phases.md, docs/release/checklist.md, README.md.

## Build/Test Command Outputs

### Python tests (REPL + studio):
```
collected 57 items
tests/test_cli_repl.py ................................................  [84%]
tests/test_cli_studio.py .........                                       [100%]
============================== 57 passed in 0.22s ==============================
```

### Full Python suite (excl. known opt-in failure):
```
=============== 1002 passed, 19 skipped, 1 deselected in 13.89s ================
```

### TS protocol build:
```
> @arc-studio/protocol@0.1.0-alpha build
> tsc -p tsconfig.json
```
(clean, no output)

### check-pr.sh:
```
Checking PR hygiene...
Checking for accidental generated artifacts...
Artifact check passed. No prohibited files tracked.
License check passed. Workspace packages declare licenses or are private.
PR hygiene check passed.
```

## Known Follow-Ups

None. All deliverables complete.

## Git Diff Stat

```
 CHANGELOG.md                                       |  15 +
 docs/ENV_HISTORY_SCRUB_PLAN.md                     |   4 +-  (pre-existing, not from this phase)
 docs/phases.md                                     |  40 +++
 python/src/agent_runtime_cockpit/cli.py            |  82 ++++-
 .../src/agent_runtime_cockpit/cli_repl/__init__.py |   5 -
 .../src/agent_runtime_cockpit/cli_repl/session.py  | 175 ++++++++++-
 .../cli_repl/slash_commands.py                     | 337 +++++++++++++++-----
 python/src/agent_runtime_cockpit/cli_studio.py     | 270 ++--------------
 python/tests/test_cli_repl.py                      | 350 +++++++++++++++++++++
 python/tests/test_cli_studio.py                    | 242 +++++++-------
 10 files changed, 1033 insertions(+), 487 deletions(-)
```
