# Phase 3 Execution Prompt

**Date:** 2026-05-12T20:06:26Z  
**Phase:** 3 - Discovery Lock  
**Status:** Ready for Execution  
**Previous Phase:** Phase 2 - Research Lock (COMPLETE)

---

## Objective

Phase 3 is a **discovery lock** where all agents inspect their owned files and document the current state. This phase establishes a baseline understanding of what exists before making any changes.

**Critical Rule:** No code changes except command verification and documentation recording.

---

## Phase 3 Definition (from arc_prompt.txt:794-796)

> Phase 3 — Discovery lock All agents inspect their owned files and write a short status note.
> 
> No code changes except command verification and docs recording.

---

## Deliverables

1. **docs/PHASE_3_DISCOVERY.md** - Discovery findings for all agents
2. **File inventory** - List of files owned by each agent
3. **Status assessment** - Current state of each file/component
4. **Command verification** - Verify all commands from arc_prompt.txt work

---

## Agent Responsibilities

### Agent 0 (Orchestrator)
- Coordinate discovery across all agents
- Verify project structure
- Check environment setup
- Document overall project state

### Agent 1 (Build/CI)
- Inspect build configuration files
- Verify package.json, dependencies
- Check CI/CD setup (if exists)
- Document build commands

### Agent 2 (Protocol)
- Inspect API/protocol files
- Check routes, endpoints
- Document protocol contracts
- Verify communication patterns

### Agent 3 (Theia Integration)
- Inspect Theia extension files
- Check frontend components
- Document widget structure
- Verify Theia configuration

### Agent 4 (Runtime Adapters)
- Inspect runtime execution files
- Check adapter implementations
- Document graph detection logic
- Verify execution patterns

### Agent 5 (Security)
- Inspect security-related files
- Check authentication/authorization
- Document security boundaries
- Verify credential handling

### Agent 6 (UX)
- Inspect UI components
- Check user-facing features
- Document UX patterns
- Verify event handling

### Agent 7 (Documentation)
- Inspect existing documentation
- Check README, guides
- Document documentation gaps
- Verify accuracy

---

## Discovery Process

### Step 1: File Inventory
Each agent lists all files they own or are responsible for.

### Step 2: Status Assessment
For each file, document:
- **Exists:** Does the file exist?
- **State:** Empty, stub, partial, complete?
- **Quality:** Working, broken, needs update?
- **Dependencies:** What does it depend on?

### Step 3: Command Verification
Verify commands from arc_prompt.txt:810-825:
```bash
git branch --show-current
bash scripts/check-env.sh
bash scripts/bootstrap-dev.sh
bash scripts/check-artifacts.sh
cd python && uv run pytest -q
cd python && uv run ruff check src tests
cd python && uv run mypy src tests || true
node tests/unit/arc-protocol.test.js
node packages/arc-test-fixtures/src/index.js
pnpm install
pnpm build
pnpm -r test
pnpm start:browser
pnpm test:e2e
```

### Step 4: Document Findings
Record all findings in `docs/PHASE_3_DISCOVERY.md`

---

## Current Project State (Known)

**Repository:** SwarmGraph (local)  
**Location:** `/Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph`  
**Git Status:** Not a git repository  

**Existing Files:**
- `swarmgraph` - Executable wrapper script
- `.venv/` - Python virtual environment with SwarmGraph installed
- `.arc/traces/` - 11 JSONL trace files
- `arc_prompt.txt` - Main project prompt (996 lines)
- `arc_prompt_test.txt` - Test prompt (31 lines)
- `docs/` - Phase 2 documentation (6 files)
- `scripts/` - Phase 2 check script

**Missing (Expected for ARC Studio):**
- Theia application structure
- Frontend/backend code
- Build configuration
- Tests
- CI/CD setup

---

## Expected Findings

Based on arc_prompt.txt, we expect to find (or not find):

1. **Build Files:**
   - `package.json` (monorepo root)
   - `packages/` directory
   - Build scripts

2. **Python Backend:**
   - `python/` directory
   - `src/` and `tests/`
   - `pyproject.toml` or `setup.py`

3. **Theia Extension:**
   - Extension package
   - Frontend components
   - Backend services

4. **Tests:**
   - Unit tests
   - Integration tests
   - E2E tests

5. **Scripts:**
   - `scripts/check-env.sh`
   - `scripts/bootstrap-dev.sh`
   - `scripts/check-artifacts.sh`

---

## Success Criteria

Phase 3 is complete when:

- [ ] All agents have inspected their owned files
- [ ] File inventory documented
- [ ] Status assessment complete
- [ ] Commands verified (or documented as missing)
- [ ] `docs/PHASE_3_DISCOVERY.md` created
- [ ] Agent 0 review complete
- [ ] No code changes made (except verification)

---

## Next Phase

Once Phase 3 is complete, proceed to:

**Phase 4 — Independent Fixes**
- Agents work in parallel on non-overlapping files
- Fix issues found during discovery
- Implement missing components

---

## Execution

Begin Phase 3 discovery now.
