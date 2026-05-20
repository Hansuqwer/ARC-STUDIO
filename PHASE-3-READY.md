# Phase 3 Foundation: Ready for Execution

**Date:** 2026-05-20  
**Current Branch:** phase-2-cli-consolidation  
**Status:** Phase 3 Slice 1 (RuntimeMode) complete and tested

---

## ✓ Completed Artifacts

### 1. RuntimeMode Enum
**Location:** `python/src/agent_runtime_cockpit/runtime/mode.py`

Three canonical runtime modes with full legacy string support:
- `FAKE` - deterministic stubs, zero cost
- `GATED_LOCAL` - local model execution (snake_case preserved for backward compatibility)
- `PROVIDER_BACKED` - external provider calls

**Features:**
- `from_legacy()` with deprecation warnings for: offline, local, gated, live
- Helper methods: `is_paid()`, `requires_gate()`
- Case and whitespace tolerant
- Proper stacklevel for debugging

**Test Coverage:** 24 tests, all passing
```bash
cd python && uv run pytest tests/unit/test_runtime_mode.py -q
# 24 passed in 0.02s
```

### 2. Migration Contract Test Skeleton
**Location:** `python/tests/contract/test_runtime_capability_migration.py`

Comprehensive test suite for RuntimeCapability v1→v2 migration:
- Schema version bump validation
- Migration idempotency checks
- Field preservation enforcement
- Consistency invariants (mode vs allow_paid_calls, cost_source)
- Per-fixture and global default expectations

**Status:** Ready to run once RuntimeCapability model is created

### 3. Test Fixtures
**Location:** `python/tests/contract/fixtures/runtime-capability/`

Three v1 baseline fixtures:
- `v1/fake_minimal_v1.json` - minimal fake runtime
- `v1/gated_local_default_v1.json` - local model execution  
- `v1/provider_backed_anthropic_v1.json` - uses legacy "live" string to test migration

Empty `v2/` directory ready for migration outputs.

### 4. Verification Script
**Location:** `scripts/verify-phase-3-prep.sh`

Pre-flight checks for Phase 3 readiness (checks RuntimeMode, fixtures, tests, git status).

---

## Phase 3 Execution Plan

### Slice 1: RuntimeMode ✓ COMPLETE
- [x] Create `runtime/mode.py` with three canonical values
- [x] Implement `from_legacy()` with deprecation warnings
- [x] Write 24 unit tests covering all edge cases
- [x] All tests passing

**Commit ready:** RuntimeMode foundation is complete and can be committed as Phase 3 Slice 1

### Slice 2: RuntimeCapability v2 (Next)
- [ ] Create `runtime/capability.py` as Pydantic model
- [ ] Add v2 fields: mode, profile_id, isolation_id, allow_paid_calls, cost_source_default, supports_cancellation, supports_streaming
- [ ] Implement `migrate_v1_to_v2(payload: dict) -> dict`
- [ ] Run contract tests (should pass)
- [ ] Generate v2 fixtures from v1 via migration

### Slice 3: Event Envelope v2
- [ ] Create `events/envelope.py` with schema_version=2
- [ ] Add fields: runtime_mode, runtime_id, profile_id, isolation_id, cost, trust, otel
- [ ] Write migration function
- [ ] Add contract tests
- [ ] Regenerate TS fixtures via `scripts/sync-protocol-fixtures.sh`

### Slice 4: ChatSession v2
- [ ] Locate existing ChatSession model
- [ ] Add deferred Phase 2 fields: runtime_id, runtime_mode, profile_id, isolation_id, allow_paid_calls, cwd, project_id
- [ ] Bump version to 2
- [ ] Write `migrate_v1_to_v2()`
- [ ] Add contract tests

### Slice 5: RuntimeRegistry + Gates
- [ ] Create `runtime/registry.py` mapping runtime_id → RuntimeCapability
- [ ] Register default fake runtime at CLI bootstrap
- [ ] Update `/run` gate to check `supports_cancellation`
- [ ] Return `blocked` with `runtime_lacks_capability` reason if check fails

### Slice 6: Slash Commands + Finalization
- [ ] Implement `/runtime` command (list available runtimes)
- [ ] Implement `/mode` command (show/switch runtime mode)
- [ ] Update CHANGELOG.md with Unreleased entries
- [ ] Add banned claims #51-#60 to `scripts/banned-claims.txt`
- [ ] Run full test suite
- [ ] Tag `phase-3-complete`

---

## Pre-Execution Checklist

Before starting Phase 3 execution:

- [ ] Phase 2 merged to main
- [ ] `phase-2-complete` tag exists
- [ ] ADR-016 in Accepted status
- [x] RuntimeMode enum created and tested ✓
- [x] Migration contract test skeleton ready ✓
- [x] v1 fixtures created ✓
- [ ] Create `phase-3-runtime-semantics` branch from main

---

## Key Design Locks (ADR-011)

1. **Exactly three runtime modes** - no additions without ADR amendment
2. **gated_local is snake_case** - backward compatibility requirement
3. **Legacy strings deprecated** - removed in Phase 6
4. **Migration must be idempotent** - migrate(v2) → v2 unchanged
5. **Invariants enforced:**
   - `allow_paid_calls=True` only valid with `PROVIDER_BACKED`
   - `cost_source_default="measured"` only valid with `PROVIDER_BACKED`
   - All non-fake runtimes must support cancellation

---

## Files Created This Session

```
python/src/agent_runtime_cockpit/runtime/mode.py
python/tests/unit/test_runtime_mode.py
python/tests/contract/test_runtime_capability_migration.py
python/tests/contract/fixtures/runtime-capability/v1/fake_minimal_v1.json
python/tests/contract/fixtures/runtime-capability/v1/gated_local_default_v1.json
python/tests/contract/fixtures/runtime-capability/v1/provider_backed_anthropic_v1.json
python/tests/contract/fixtures/runtime-capability/v2/ (empty directory)
scripts/verify-phase-3-prep.sh
docs/phase-3-prep-summary.md
```

---

## Next Action

**Current Status:** You are still on `phase-2-cli-consolidation` branch implementing Phase 2.

**When Phase 2 is complete:**
1. Merge Phase 2 to main
2. Tag `phase-2-complete`
3. Create branch `phase-3-runtime-semantics` from main
4. Cherry-pick or re-create the Phase 3 Slice 1 artifacts (RuntimeMode + tests)
5. Continue with Slice 2 (RuntimeCapability)

**Phase 3 Slice 1 is ready to commit** - the RuntimeMode enum and its 24 passing tests are production-ready foundation code.

---

## Test Commands

```bash
# Run RuntimeMode unit tests
cd python && uv run pytest tests/unit/test_runtime_mode.py -v

# Run migration contract tests (will fail until capability.py exists)
cd python && uv run pytest tests/contract/test_runtime_capability_migration.py -v

# Verify Phase 3 prep status
./scripts/verify-phase-3-prep.sh

# Full Python test suite
cd python && uv run pytest -q
```

---

**Phase 3 foundation is solid. RuntimeMode enum is complete, tested, and ready for production.**
