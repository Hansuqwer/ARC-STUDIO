# Parallel ARC Studio Work Plan

**Created:** 2026-05-26  
**Priority:** CLI first. Session 1 and Session 2 target R39 / Phase 41. Session 3 avoids CLI conflicts.

## Session 1 — Slash Command Foundation

**Branch:** `cli/session-1-slash-foundation`

**Goal:** Make `arc studio chat` expose key existing ARC capabilities through first-class slash commands.

**Scope:**
- Expand the `cli_repl` slash command registry.
- Add safe/read-only slash command adapters first.
- Avoid broad shell execution.
- Avoid destructive/write actions except through existing sandbox policy.
- Keep implementation small and testable.

**Candidate commands:**
- `/sandbox doctor`
- `/policy explain -- <cmd...>`
- `/runs list`
- `/runs show <id>`
- `/doctor`
- `/status`
- `/providers status`
- `/task list`
- `/task status <id>`

**Likely files:**
- `python/src/agent_runtime_cockpit/cli_repl/slash_commands.py`
- `python/src/agent_runtime_cockpit/cli_repl/commands/__init__.py`
- `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py`
- `python/tests/test_cli_repl.py`
- Shared helper extraction only if needed from `python/src/agent_runtime_cockpit/cli/*.py`.

**Acceptance:**
- `/help` shows new command groups.
- New slash commands return structured text, not raw Python reprs.
- `/policy explain -- curl https://example.com` works from REPL and does not execute the command.
- `/sandbox doctor` works from REPL and does not claim microVM execution.
- `/runs list` and `/task list` handle empty states.
- REPL does not crash on malformed slash command.
- Tests cover all new slash commands.

**Verification:**
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/test_cli_repl.py -q
cd python && uv run pytest tests/cli/test_cli_discoverability.py -q
cd python && uv run pytest tests/cli/test_cli_snapshots.py -q
```

**Risks:**
- Directly calling Typer command functions may trigger `typer.Exit` or output side effects.
- Prefer shared service helpers over shelling out to `arc`.
- Session 2 will conflict if both edit `slash_commands.py` simultaneously.

## Session 2 — Approval + Progress UX

**Branch:** `cli/session-2-approval-progress`

**Goal:** Make the interactive CLI feel like a real agent shell: approvals, progress, cancellation, clear errors.

**Scope:**
- Add reusable render states: `present`, `blocked`, `denied`, `degraded`, `error`, `absent`.
- Add per-command exception boundary so REPL never exits on command failure.
- Add progress rendering for `/run` events.
- Add `/sandbox run -- <cmd...>` with interactive approval using existing sandbox policy.
- Preserve destructive/privileged deny-by-default behavior.
- Do not add broad unsafe shell execution.

**Likely files:**
- `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py`
- `python/src/agent_runtime_cockpit/cli_repl/slash_commands.py`
- `python/src/agent_runtime_cockpit/security/sandbox.py`
- `python/src/agent_runtime_cockpit/cli/sandbox.py`
- `python/tests/test_cli_repl.py`
- `python/tests/test_cli_sandbox.py`

**Acceptance:**
- REPL catches command exceptions and renders useful errors.
- `/run` renders started/progress/completed/cancelled states where available.
- `/sandbox run -- ls -la` works under `local-safe`.
- `/sandbox run -- curl https://example.com` denies or asks according to policy.
- `/sandbox run -- rm -rf .` denies by default.
- Audit event emitted for allowed and denied sandbox runs.
- Output truncation and redaction behavior preserved.
- Tests cover approval, denial, progress, and error recovery.

**Verification:**
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/test_cli_repl.py tests/test_cli_sandbox.py -q
cd python && uv run pytest tests/isolation/test_isolation.py -q
cd python && uv run pytest tests/security/test_sandbox_policy.py -q
```

**Risks:**
- Must rebase on Session 1 before implementation if Session 1 lands first.
- Sandbox approval UX must not bypass existing deny defaults.
- MicroVM execution remains unimplemented; only preflight/design output is allowed.

## Session 3 — Parallel Roadmap Feature

**Branch:** `roadmap/session-3-memory-graph-research`

**Goal:** Progress a roadmap feature with minimal overlap with CLI files.

**Recommended choice:** R26 / Phase 33 Swarm Memory Graph research or prototype.

**Scope:**
- Research/design doc or minimal prototype only.
- Do not modify `cli_repl` or core CLI modules.
- Avoid provider/live calls.
- Avoid tenant/privacy overclaims.
- Keep it research/prototype unless tests prove implementation.

**Likely files:**
- `docs/research/swarm-memory-graph.md`
- `docs/roadmap.md`
- `docs/phases.md`
- If prototype: `python/src/agent_runtime_cockpit/memory/`, `python/tests/memory/`

**Acceptance:**
- Research doc includes schema, extraction strategy, privacy risks, and go/no-go criteria.
- If prototype: extracts memory candidates from stored local traces only.
- No provider calls.
- No cross-tenant/shared-server claims.
- Tests cover extraction from synthetic traces if code is added.

**Verification:**
Docs-only:
```bash
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md docs/research/swarm-memory-graph.md
```

If prototype:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/memory/ -q
cd python && uv run pytest tests/storage/ -q
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md docs/research/swarm-memory-graph.md
```

**Risks:**
- Memory graph may introduce privacy leakage or memory pollution.
- Keep status as research unless implementation and tests exist.

## Dependency Graph

```text
Session 1: slash registry + safe command adapters
        ↓
Session 2: approval/progress/error UX over the expanded registry

Session 3: memory graph research/prototype, parallel-safe if it avoids CLI files
```

## Merge Order

1. `cli/session-1-slash-foundation`
2. `cli/session-2-approval-progress`
3. `roadmap/session-3-memory-graph-research`

## Conflict Rules

- Session 1 and Session 2 both touch `cli_repl/slash_commands.py` and `python/tests/test_cli_repl.py`; do not merge Session 2 before rebasing on Session 1.
- Session 3 should not touch `cli_repl/`, `cli/sandbox.py`, or `tests/test_cli_repl.py`.
- Docs conflicts likely in `docs/roadmap.md` and `docs/phases.md`; update only the relevant section per branch.

## Docs Updates

- Session 1 may update R39/Phase 41 chunks 41.1 and 41.2 if implementation lands.
- Session 2 may update R39/Phase 41 chunks 41.3 and 41.4 if implementation lands.
- Session 3 may update R26/Phase 33 only if research/prototype genuinely changes status.
- Do not mark R39/R40 complete until acceptance and verification pass.

## Final Warnings

- CLI priority means Session 1 and Session 2 should land before broad UI/TUI polish.
- Do not claim OpenCode/Claude Code parity until slash commands, approvals, diffs, tool use, and session resume are implemented and tested.
- Do not claim microVM execution.
- Keep container fallback gated by `ARC_ENABLE_CONTAINER_SANDBOX=1`.
