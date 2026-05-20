# Phase 3 Preparation Summary

**Date:** 2026-05-20  
**Status:** Foundation artifacts created, ready for Phase 3 execution

## What's Been Delivered

### 1. RuntimeMode Enum (✓ Complete)

**File:** `python/src/agent_runtime_cockpit/runtime/mode.py`

- Three canonical values: `FAKE`, `GATED_LOCAL`, `PROVIDER_BACKED`
- `from_legacy()` classmethod with deprecation warnings for legacy strings:
  - `offline` → `FAKE`
  - `local` → `GATED_LOCAL`
  - `gated` → `GATED_LOCAL`
  - `live` → `PROVIDER_BACKED`
- Helper methods: `is_paid()`, `requires_gate()`
- Full unit test coverage: 24 tests, all passing

**Test Results:**
```
tests/unit/test_runtime_mode.py::24 passed in 0.02s
```

### 2. RuntimeCapability Migration Contract Test (✓ Complete)

**File:** `python/tests/contract/test_runtime_capability_migration.py`

Comprehensive test skeleton covering:
- Schema version bump validation (v1 → v2)
- Migration idempotency
- Field preservation (no silent drops)
- v2 required fields presence
- Mode/capability consistency invariants
- Per-fixture and global default expectations

### 3. Test Fixtures (✓ Complete)

**Directory:** `python/tests/contract/fixtures/runtime-capability/`

Three v1 baseline fixtures created:
- `v1/fake_minimal_v1.json` - minimal fake runtime
- `v1/gated_local_default_v1.json` - local model execution
- `v1/provider_backed_anthropic_v1.json` - uses legacy "live" string

Empty v2 directory ready for migration outputs.

## What's Still Needed for Phase 3

### Immediate Next Steps

1. **RuntimeCapability Model** - Does not exist yet
   - Need to create `python/src/agent_runtime_cockpit/runtime/capability.py`
   - Must be a Pydantic model with `schema_version: int` field
   - Implement `migrate_v1_to_v2(payload: dict) -> dict` classmethod

2. **Run Migration Contract Tests** - Will fail until capability.py exists
   ```bash
   cd python && uv run pytest tests/contract/test_runtime_capability_migration.py -v
   ```

3. **Event Envelope Schema v2** - Phase 3 deliverable
   - Create `python/src/agent_runtime_cockpit/events/envelope.py`
   - Add schema_version, runtime_mode, cost, trust, otel fields

4. **ChatSession Schema v2** - Phase 3 deliverable
   - Locate existing ChatSession model
   - Add deferred Phase 2 fields: runtime_id, runtime_mode, profile_id, etc.
   - Bump version to 2, write migration

5. **RuntimeRegistry** - Phase 3 deliverable
   - Create `python/src/agent_runtime_cockpit/runtime/registry.py`
   - Map runtime_id → RuntimeCapability

6. **Capability-Aware Gates** - Phase 3 deliverable
   - Update `/run` gate to check `supports_cancellation`

7. **Slash Commands** - Phase 3 deliverable
   - Implement `/runtime` and `/mode` commands

## Phase 3 Execution Readiness

### Pre-flight Checklist Status

- [x] Phase 2 complete and merged? - **PENDING** (you said you're implementing Phase 2 now)
- [x] phase-2-complete tag exists? - **PENDING**
- [x] ADR-016 in Accepted status? - **NEED TO VERIFY**
- [x] RuntimeMode enum created and tested? - **YES** ✓
- [x] Migration contract test skeleton ready? - **YES** ✓
- [x] v1 fixtures created? - **YES** ✓

### Suggested Commit Order for Phase 3

When Phase 2 is complete and you're ready to start Phase 3:

**Commit 1: RuntimeMode foundation**
- `python/src/agent_runtime_cockpit/runtime/mode.py` (already done)
- `python/tests/unit/test_runtime_mode.py` (already done, 24 tests passing)
- Tag: `phase-3-slice-1-runtime-mode`

**Commit 2: RuntimeCapability v2 + migration**
- Create `python/src/agent_runtime_cockpit/runtime/capability.py`
- Implement `migrate_v1_to_v2()`
- Contract test should pass
- Generate v2 fixtures
- Tag: `phase-3-slice-2-capability-v2`

**Commit 3: Event envelope v2**
- Create envelope schema with all locked fields
- Migration function
- Contract tests
- Tag: `phase-3-slice-3-envelope-v2`

**Commit 4: ChatSession v2**
- Add deferred fields
- Migration function
- Contract tests
- Tag: `phase-3-slice-4-session-v2`

**Commit 5: RuntimeRegistry + gates**
- Registry implementation
- Capability-aware `/run` gate
- Tag: `phase-3-slice-5-registry-gates`

**Commit 6: Slash commands + CHANGELOG**
- `/runtime` and `/mode` commands
- CHANGELOG.md updates
- Banned claims updates
- Tag: `phase-3-complete`

## Files Created in This Session

```
python/src/agent_runtime_cockpit/runtime/mode.py
python/tests/unit/test_runtime_mode.py
python/tests/contract/test_runtime_capability_migration.py
python/tests/contract/fixtures/runtime-capability/v1/fake_minimal_v1.json
python/tests/contract/fixtures/runtime-capability/v1/gated_local_default_v1.json
python/tests/contract/fixtures/runtime-capability/v1/provider_backed_anthropic_v1.json
python/tests/contract/fixtures/runtime-capability/v2/ (empty, ready for migration outputs)
```

## Key Design Decisions Locked

1. **Three runtime modes only** - ADR-011 locked, no additions without amendment
2. **gated_local uses snake_case** - backward compatibility with Phase 0/1/2 sessions
3. **Legacy string support** - with deprecation warnings pointing to Phase 6 removal
4. **Migration idempotency** - migrate(v1) → v2, migrate(v2) → v2 unchanged
5. **Invariants enforced** - allow_paid_calls only valid with PROVIDER_BACKED mode

## Next Action

**If you're still in Phase 2:** Continue Phase 2 work. These Phase 3 artifacts are ready and waiting.

**If Phase 2 is complete:** Run the Phase 3 execution prompt with:
- PHASE_NUMBER: 3
- PHASE_NAME: Runtime Semantics Unification
- BRANCH: phase-3-runtime-semantics
- baseline: HEAD of main at phase-2-complete tag

The RuntimeMode enum and migration test skeleton are your foundation. Everything else builds on these two pieces.
