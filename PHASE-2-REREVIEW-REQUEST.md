# Phase 2 (Phase 18) CLI Consolidation - Re-Review Request

**Date:** 2026-05-20  
**Branch:** phase-2-cli-consolidation  
**Commit:** 862e18d  
**Baseline:** e61db62 (Phase 1 merge point)  
**Status:** Ready for re-review after ADR-016 scope fix-up

---

## Context

Phase 18 (CLI Consolidation) was previously reviewed and received a REJECT verdict due to scope ambiguity. The reviewer correctly identified that the Phase 0 inventory files could be read as claiming full CLI target completion, when Phase 18 only delivered a subset.

**Actions taken since previous review:**
1. Created ADR-016 to explicitly scope Phase 2 as a CLI consolidation subset
2. Documented deferred items (runtime semantics → Phase 3, full slash inventory → later phases)
3. Cleaned branch of Phase 3 artifacts that were accidentally included
4. Phase 3 work moved to separate `phase-3-prep` branch (commit 58d8882)

---

## Scope Per ADR-016

### In-Scope Commands
- `/help`, `/version`, `/exit`, `/quit`, `/clear`, `/summary`
- `/sessions`, `/history`
- `/run` (mode-gated, cancellation-aware)
- `/plan`, `/build`, `/auto` (mode switches only; full planning semantics deferred)
- `/status`, `/doctor`, `/runs`

### In-Scope Session Fields
- `version`, `id`, `mode`, `created_at`, `updated_at`, `history`, `metadata`
- Legacy flat session migration via `arc studio sessions migrate`
- Workspace-trust metadata on legacy content

### Explicitly Deferred to Later Phases
- Full `/plan` semantics (Phase 4.7)
- `/graph`, `/timeline`, `/topology` (Phase 4)
- `/providers`, `/quota`, `/provider-action` (Phase 4)
- `/budget`, `/audit`, `/receipt`, `/contract` (Phase 5)
- `/hitl` (Phase 5)
- `/memory` commands (Phase 4.5)
- `/context` and `@` picker (Phase 4.5)
- `/search`, `/fetch` (Phase 5.5)
- `/mcp` commands (Phase 5.6)
- `/skill` commands (Phase 5.7)
- Session runtime fields: `runtime_id`, `runtime_mode`, `profile_id`, `isolation_id`, `allow_paid_calls` (Phase 3)
- Session project fields: `cwd`, `project_id`, `attached_context`, `last_run_id`, `active_workflow`, `runtime_model` (Phase 3)
- `ARC_STUDIO_HISTORY_FILE`, `ARC_STUDIO_DEFAULT_SCOPE` env vars (Phase 3)

---

## Deliverables

### 1. Unified Command Registry
- Single source of truth: `cli_repl/commands/` package
- Declarative `CommandRegistry` and `CommandDef` dataclass
- Explicit metadata: category, gates, mode, trust, privilege, render, event

### 2. CLI Consolidation
- Merged 8 `cli_studio.py` slash commands into unified registry
- `cli_studio.py` reduced to thin shim (≤30 lines) delegating to `arc studio chat`
- Bare `arc` TTY behavior: launches ARC Studio REPL (respects `ARC_NO_TUI=1`)

### 3. Session Schema v1
- Added `version=1` field to `ChatSession`
- Legacy `StudioSession` flat JSON reader with fallback
- Workspace-trust metadata on legacy content
- `arc studio sessions migrate` command for one-shot conversion

### 4. Mode/Cancellation Handling
- `/run` is mode-gated and cancellation-aware
- Registry metadata supports future gate enforcement

---

## Verification

### Tests
```bash
cd python && uv run pytest -q
# Expected: 989 passed, 19 skipped (current baseline)

pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
# Expected: clean builds

bash scripts/check-pr.sh
# Expected: pass
```

### Branch Status
```bash
git log --oneline phase-2-cli-consolidation -5
# 862e18d phase-2: remove Phase 3 recovery doc (moved to phase-3-prep branch)
# 6bb5316 docs: add Phase 3 Slice 1 stash recovery instructions
# 336a48f phase-2: add sessions migrate compatibility checks
# 0b8655d phase-2: address CLI consolidation review blockers
# eb62d40 phase-2: CLI consolidation subset
```

**No Phase 3 artifacts on branch.** Phase 3 work (RuntimeMode enum, migration tests) moved to `phase-3-prep` branch.

---

## ADR-016 Acceptance Criteria

- [x] `docs/phases.md` references ADR-016 and describes this as a subset
- [x] `arc studio sessions migrate` exists and is tested
- [x] Every registered command has explicit metadata
- [x] `/run` is mode-gated and cancellation-aware
- [x] Legacy flat session reads attach workspace-trust metadata
- [x] Deferred items listed in ADR-016

---

## Expected Verdict

**APPROVE_WITH_FOLLOWUPS**

Followups documented in ADR-016:
- Phase 3: Runtime semantics unification (runtime_id, runtime_mode, profile_id, etc.)
- Phase 4+: Full slash command inventory
- Phase 5+: Budget/audit/HITL/MCP/skill commands

---

## Review Parameters

```
BRANCH_OR_PR: phase-2-cli-consolidation
BASELINE: e61db62
COMMIT: 862e18d
```

---

**Phase 2 branch is clean, scoped per ADR-016, and ready for re-review.**
