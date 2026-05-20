# Phase 3 Slice 1 - Stash Recovery Instructions

**Date:** 2026-05-20  
**Status:** Phase 3 Slice 1 artifacts safely stashed, Phase 2 branch clean

## What Happened

Phase 3 Slice 1 (RuntimeMode enum + tests) was built on the `phase-2-cli-consolidation` branch as untracked files. To prevent scope drift in Phase 2 review, all Phase 3 artifacts have been stashed.

## Stash Contents

**Stash ID:** `stash@{0}`  
**Message:** "phase-3-slice-1: RuntimeMode enum + migration test skeleton + prep docs"

**Files in stash:**
- `python/src/agent_runtime_cockpit/runtime/mode.py` (116 lines)
- `python/tests/unit/test_runtime_mode.py` (171 lines, 24 tests)
- `python/tests/contract/test_runtime_capability_migration.py` (300 lines)
- `python/tests/contract/fixtures/runtime-capability/v1/*.json` (3 fixtures)
- `python/tests/contract/fixtures/runtime-capability/v2/` (empty dir)
- `scripts/verify-phase-3-prep.sh`
- `PHASE-3-READY.md`
- `PHASE-3-HANDOFF.txt`
- `docs/phase-3-prep-summary.md`

## Recovery Procedure

### After Phase 2 Merges to Main

```bash
# 1. Verify Phase 2 is merged and tagged
git checkout main
git pull
git tag | grep phase-2-complete
# Expected: phase-2-complete tag exists

# 2. Create Phase 3 branch from main
git checkout -b phase-3-runtime-semantics

# 3. Apply the stashed Phase 3 Slice 1 work
git stash apply stash@{0}
# Or if you want to pop (apply + delete): git stash pop stash@{0}

# 4. Verify Slice 1 artifacts restored
ls python/src/agent_runtime_cockpit/runtime/mode.py
ls python/tests/unit/test_runtime_mode.py
ls python/tests/contract/fixtures/runtime-capability/v1/

# 5. Run Slice 1 tests to verify integrity
cd python && uv run pytest tests/unit/test_runtime_mode.py -v
# Expected: 24 passed in 0.02s

# 6. Commit Slice 1 as the first Phase 3 commit
git add python/src/agent_runtime_cockpit/runtime/
git add python/tests/unit/test_runtime_mode.py
git add python/tests/contract/test_runtime_capability_migration.py
git add python/tests/contract/fixtures/runtime-capability/
git commit -m "phase-3 slice-1: RuntimeMode enum with legacy support

- Three canonical modes: FAKE, GATED_LOCAL, PROVIDER_BACKED
- from_legacy() with deprecation warnings for offline/local/gated/live
- Helper methods: is_paid(), requires_gate()
- 24 unit tests, all passing
- Migration contract test skeleton for RuntimeCapability v2
- 3 v1 baseline fixtures (fake, gated_local, provider_backed)

Lock: ADR-011 (three modes exactly, gated_local snake_case preserved)
Phase: 3 Slice 1 (Runtime Semantics Unification)
Tests: 24 passed in 0.02s"

# 7. Optionally commit prep docs separately
git add scripts/verify-phase-3-prep.sh
git add PHASE-3-READY.md
git add docs/phase-3-prep-summary.md
git commit -m "phase-3: add prep docs and verification script"

# 8. Delete PHASE-3-HANDOFF.txt (redundant with PHASE-3-READY.md)
rm PHASE-3-HANDOFF.txt

# 9. Tag Slice 1 complete
git tag phase-3-slice-1-complete

# 10. Continue with Slice 2 (RuntimeCapability model)
```

## Emergency Recovery (If Stash is Lost)

The stash is local only. If it's lost before Phase 3 starts, the work can be reconstructed from the documentation:

1. **RuntimeMode enum:** Full implementation is documented in `PHASE-3-READY.md` (which is also in the stash, but the kickoff brief in your conversation history has the same content)
2. **Unit tests:** Test skeleton is in the kickoff brief
3. **Migration contract test:** Full skeleton is in the kickoff brief
4. **Fixtures:** Simple JSON files, easy to recreate from the examples in the kickoff brief

Estimated reconstruction time: ~30 minutes (vs. 2 hours original implementation).

## Verification Commands

```bash
# Check stash still exists
git stash list | grep "phase-3-slice-1"

# Preview stash contents without applying
git stash show -p stash@{0} | head -50

# List files in stash
git stash show --name-only stash@{0}
```

## Current Status

- **Phase 2 branch:** Clean, no Phase 3 artifacts
- **Phase 3 Slice 1:** Safely stashed, ready for recovery
- **Next:** Complete Phase 2 review, merge, tag, then recover Slice 1 onto phase-3-runtime-semantics branch

---

**Stash created:** 2026-05-20  
**Recovery target:** After phase-2-complete tag exists
