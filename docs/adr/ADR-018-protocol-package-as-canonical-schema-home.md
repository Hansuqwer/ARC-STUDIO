# ADR-018 — `protocol/` Package as Canonical Schema Home

**Status**: Accepted
**Date**: 2026-05-20
**Refines**: ADR-011 (transport parity)

## Context

Phase 3 introduced `RuntimeCapability` under `runtime/capability.py` and the
event envelope under `protocol/schemas.py`. Phase 4 Slice 3 introduced
`CostRecord` under `protocol/cost_record.py`. The placements diverged
because each was decided in isolation.

ADR-011 requires Python and TypeScript to share fixture-level parity for
all transport schemas. The sync script iterates source directories; adding
a new schema requires updating the script.

Without a canonical home, two predictable failures occur:

1. The next schema gets placed by intuition and continues the drift.
2. The TS mirror's directory layout has no obvious correspondence to
   the Python source layout.

## Decision

`python/src/agent_runtime_cockpit/protocol/` is the canonical home for
all cross-language schemas. The TS mirror lives at the equivalent path
under `packages/arc-studio-protocol/`.

Migration logic (`migrate_v1_to_v2`, etc.) stays alongside its schema.

Existing schemas that belong under `protocol/` but currently live elsewhere
will be moved in a Phase 4.0.1 cleanup commit:

- `runtime/capability.py` → `protocol/runtime_capability.py`
- The event envelope lives in `protocol/schemas.py` (already in protocol/)
  and `protocol/events.py` — these are already canonical.

## Policy

A schema belongs under `protocol/` when it satisfies **both** criteria:

1. It is exchanged across the Python↔TypeScript language boundary
2. It has a v1/v2 fixture directory under `tests/contract/fixtures/`

A schema stays in its domain package when it satisfies **either** criterion:

1. It is Python-only (not mirrored to TypeScript)
2. It does not participate in the contract test fixture regime

## Out of scope

Python-only schemas that are never mirrored to TS (e.g., `ChatSession` v3,
budget internal state) stay in their domain packages.

## Acceptance

- [ ] Move `runtime/capability.py` → `protocol/runtime_capability.py`
      with import updates and a contract test asserting v2 fixtures
      still validate. (Deferred to Phase 4.1.)
- [ ] Create `scripts/sync-protocol-fixtures.sh` to iterate `protocol/`.
      (Deferred to Phase 4.1 — no sync script exists yet.)
- [x] `protocol/__init__.py` carries a comment stating this policy.
      (Done — ADR-018.)

## Migration Plan (Phase 4.1)

1. `git mv runtime/capability.py protocol/runtime_capability.py`
2. Update all imports: `git grep 'from agent_runtime_cockpit.runtime.capability\|from agent_runtime_cockpit.runtime import.*capability'`
3. Update `runtime/__init__.py` exports
4. Create `scripts/sync-protocol-fixtures.sh` that iterates all `protocol/*.py` with matching v1/v2 fixture directories
5. Run full pytest to verify
6. Event envelope: `protocol/schemas.py` and `protocol/events.py` are already in `protocol/` — no move needed

## Sync script design (deferred)

The sync script should:
- Iterate `python/src/agent_runtime_cockpit/protocol/*.py`
- For each module with a matching `tests/contract/fixtures/<module_name>/` directory,
  generate TypeScript types in `packages/arc-protocol-ts/src/protocol/`
- Verify generated TS compiles via `pnpm --filter @arc-studio/protocol build`
- Fail if any v1/v2 fixture pair in `tests/contract/` lacks a TS counterpart

## Consequences

Positive: schema sync becomes mechanical. New cross-language schemas
have an obvious placement. The TS mirror layout matches Python.

Negative: a directory move that touches imports across the codebase.
Risk of merge conflicts with in-flight Phase 4 work.
