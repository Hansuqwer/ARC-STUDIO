# Commit Phase 34.2 - IDE Battle Tab Implementation

**Date:** 2026-05-23  
**Phase:** 34.2 — IDE Battle Tab  
**Status:** Ready to commit

---

## Pre-Commit Verification

Run these commands to verify the current state and ensure all changes are present:

### 1. Check Git Status
```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio
git status --short
```

**Expected output should include:**
- Modified files from Phase 34.1 (if not yet committed)
- Modified files from Phase 34.2
- New files: BattleTab.tsx, battle-protocol.ts, battle-service.ts

### 2. Verify TypeScript Builds
```bash
# Build protocol package
pnpm --filter @arc-studio/protocol build

# Build arc-extension package
pnpm --filter arc-extension build
```

**Expected:** Both builds should succeed with no errors.

### 3. Verify Python Tests (Phase 34.1)
```bash
cd python && PYTHONPATH=src uv run pytest tests/battle/ tests/cli/test_battle_cli.py -q
```

**Expected:** 41 tests passing.

### 4. Check File Contents

Verify key files have the expected content:

```bash
# Check BattleTab exists
ls -la packages/arc-extension/src/browser/tabs/BattleTab.tsx

# Check battle-protocol exists
ls -la packages/arc-extension/src/common/battle-protocol.ts

# Check battle-service exists
ls -la packages/arc-extension/src/node/services/battle-service.ts

# Check Battle tab is registered in widget
grep -n "BattleTab" packages/arc-extension/src/browser/arc-studio-widget.tsx

# Check battle methods in ArcService interface
grep -n "listBattles\|getBattleDetails\|getLeaderboard" packages/arc-extension/src/common/arc-protocol.ts
```

**Expected:** All files should exist and contain the expected content.

---

## Commit Phase 34.1 + Phase 34.2 Together

Since Phase 34.2 builds on Phase 34.1, commit both phases together:

### 1. Stage All Phase 34.1 Files
```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio

git add python/src/agent_runtime_cockpit/battle/runner.py
git add python/src/agent_runtime_cockpit/cli/battle.py
git add python/tests/battle/test_battle_runner.py
git add docs/roadmap.md
git add docs/phases.md
```

### 2. Stage All Phase 34.2 Files
```bash
# Stage modified files
git add packages/arc-extension/src/browser/arc-studio-widget.tsx
git add packages/arc-extension/src/browser/tabs/index.ts
git add packages/arc-extension/src/common/arc-protocol.ts
git add packages/arc-extension/src/node/arc-backend-service.ts
git add packages/arc-extension/src/node/arc-extension-backend-module.ts

# Stage new files
git add packages/arc-extension/src/browser/tabs/BattleTab.tsx
git add packages/arc-extension/src/common/battle-protocol.ts
git add packages/arc-extension/src/node/services/battle-service.ts
```

### 3. Stage Documentation Files
```bash
git add PHASE_34.1_COMPLETE_SUMMARY.md
git add PHASE_34.2_COMPLETE_SUMMARY.md
git add NEXT_PHASE_34.2_PROMPT.md
```

### 4. Verify Staged Files
```bash
git status
```

**Expected:** Should show all Phase 34.1 and 34.2 files staged for commit.

### 5. Create Commit

```bash
git commit -m "Implement Phase 34.1 + 34.2: Battle Run/Trace Integration + IDE Battle Tab

Phase 34.1 - Battle Run/Trace Integration:
Make battle runs compatible with existing ARC run/trace surfaces.

- Add persist_battle_run_trace() to BattleRunner
- Battle runs create ARC run records in .arc/arc.db
- Battle runs create JSONL traces in .arc/traces/
- arc runs get/status/trace work for battle runs
- CLI returns run_id and trace_path
- Add 5 integration tests (36 → 41 total)
- Update docs with follow-up phases 34.2-34.6

Phase 34.2 - IDE Battle Tab:
Add Battle tab to ARC Studio IDE for viewing battle runs.

Backend:
- Add BattleService with CLI bridge to arc battle commands
- Add battle methods to ArcService interface
- Implement battle methods in ArcBackendService
- Register BattleService in DI container
- Add battle protocol types (BattleRun, BattleDetails, EloRating)

Frontend:
- Add BattleTab component with 3-column layout
- Display battle list, details, and leaderboard
- Add loading states, error handling, empty states
- Register Battle tab in ArcStudioWidget
- Use inline styles with Theia CSS variables

Integration:
- Calls arc battle list/show/leaderboard via CLI
- Displays data from .arc/battles.db
- Complements Phase 34.1 run/trace integration

Verification:
- 41 battle tests passing
- 2053 total Python tests passing
- TypeScript builds green (protocol + arc-extension)
- All imports resolved
- No compilation errors

Phase 34.1 + 34.2 complete. Tests for 34.2 deferred to polish phase.
Next: Manual testing or Phase 34.3 (Battle Replay Determinism)."
```

### 6. Verify Commit
```bash
# Check commit was created
git log -1 --stat

# Check commit message
git log -1 --pretty=format:"%B"

# Check files in commit
git show --name-status
```

---

## Post-Commit Verification

### 1. Verify Clean Working Directory
```bash
git status
```

**Expected:** Should show clean working tree (except for untracked files like build artifacts).

### 2. Verify Commit History
```bash
git log --oneline -5
```

**Expected:** Should show the new commit at the top.

### 3. Verify File Changes in Commit
```bash
git show --stat
```

**Expected:** Should show all Phase 34.1 and 34.2 files.

---

## Optional: Push to Remote

If you want to push the commit to the remote repository:

```bash
# Check current branch
git branch --show-current

# Push to remote
git push origin $(git branch --show-current)
```

**Note:** Only push if you're ready to share the changes with others.

---

## Manual Testing (Recommended Next Step)

After committing, manually test the Battle tab in the IDE:

### 1. Start the IDE
```bash
pnpm --filter @arc-studio/browser start
```

### 2. Create a Test Battle
In a separate terminal:
```bash
cd /Users/hansvilund/HansuQWER/WorkSpace/ARC/arc-theia-studio
arc battle run "Write a hello world function in Python" --workers 2 --json
```

### 3. Test the Battle Tab
1. Open ARC Studio widget in the IDE
2. Click "Battle" tab
3. Verify battle appears in the list
4. Click the battle to view details
5. Verify candidates, votes, and outcome display correctly
6. Verify leaderboard shows model rankings
7. Test refresh buttons

### 4. Verify Integration with Runs Tab
1. Note the `run_id` from the battle run output
2. Switch to "Runs" tab
3. Verify the battle run appears in the runs list
4. Try `arc runs get <run_id> --json` in terminal
5. Try `arc runs trace <run_id> --json` in terminal

---

## Troubleshooting

### If Git Status Shows Unexpected Files

```bash
# See what's different
git diff

# See what's staged
git diff --cached

# Unstage all if needed
git reset HEAD

# Start over with staging
```

### If TypeScript Build Fails

```bash
# Clean build artifacts
rm -rf packages/arc-extension/lib
rm -rf packages/arc-protocol-ts/lib

# Rebuild
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
```

### If Python Tests Fail

```bash
# Run with verbose output
cd python && PYTHONPATH=src uv run pytest tests/battle/ -v

# Run specific test
cd python && PYTHONPATH=src uv run pytest tests/battle/test_battle_runner.py::test_battle_run_creates_arc_run_record -v
```

### If Battle Tab Doesn't Appear in IDE

1. Check browser console for errors
2. Verify BattleTab is imported in arc-studio-widget.tsx
3. Verify 'battle' is in StudioTabId type
4. Verify Battle tab is in tabs array
5. Rebuild arc-extension: `pnpm --filter arc-extension build`
6. Restart the IDE

---

## Files Committed

**Phase 34.1 (Python/Docs) - 5 files:**
- `python/src/agent_runtime_cockpit/battle/runner.py`
- `python/src/agent_runtime_cockpit/cli/battle.py`
- `python/tests/battle/test_battle_runner.py`
- `docs/roadmap.md`
- `docs/phases.md`

**Phase 34.2 (TypeScript/IDE) - 8 files:**
- `packages/arc-extension/src/common/battle-protocol.ts` (new)
- `packages/arc-extension/src/node/services/battle-service.ts` (new)
- `packages/arc-extension/src/browser/tabs/BattleTab.tsx` (new)
- `packages/arc-extension/src/common/arc-protocol.ts`
- `packages/arc-extension/src/node/arc-backend-service.ts`
- `packages/arc-extension/src/node/arc-extension-backend-module.ts`
- `packages/arc-extension/src/browser/arc-studio-widget.tsx`
- `packages/arc-extension/src/browser/tabs/index.ts`

**Documentation - 3 files:**
- `PHASE_34.1_COMPLETE_SUMMARY.md`
- `PHASE_34.2_COMPLETE_SUMMARY.md`
- `NEXT_PHASE_34.2_PROMPT.md`

**Total: 16 files**

---

## Success Criteria

✅ All files staged for commit  
✅ Commit created with descriptive message  
✅ TypeScript builds passing  
✅ Python tests passing (41 battle tests)  
✅ No compilation errors  
✅ Clean working directory after commit  

**Phase 34.1 + 34.2 committed successfully!**

---

## Next Steps After Commit

1. **Manual Test** - Test the Battle tab in the IDE
2. **Write Tests** - Add unit/component tests for Phase 34.2
3. **Phase 34.3** - Implement Battle Replay Determinism
4. **Phase 34.4** - Implement Persistent HITL Prompt Wiring
5. **Phase 34.5** - Implement Commit-Reveal Escrow Verification

**Recommended:** Manual test first to verify everything works end-to-end.
