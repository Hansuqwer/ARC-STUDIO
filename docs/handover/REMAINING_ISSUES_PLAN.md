# ARC Studio — Remaining Issues & Remediation Plan

> Handover document for genspark.ai. No local filesystem access required.
> Every issue cites exact file paths, line ranges, and CI evidence.
>
> **VERIFICATION ADDENDUM (2026-05-14)**: Original R-1 diagnosis was incorrect.
> Corrected below based on verification against commit e398827.

---

## Issue Summary Table

| # | Priority | Area | Symptom | Root Cause | Fix (file) |
|---|----------|------|---------|------------|------------|
| R-1 | P0 | CI | Node workflow fails: `arc-ag-ui` test exits 1 | Unquoted glob `./test/**/*.test.js` fails under POSIX sh (no globstar) | `packages/arc-ag-ui/package.json` line 11 |
| R-2 | P0 | CI | ARC Roadmap Gate fails: `native-keymap` gyp build crash | Missing `libx11-dev` + `libxkbfile-dev` apt packages | `.github/workflows/arc-roadmap-gate.yml` after line 16 |
| R-3 | P1 | Python tests | 2 AG2 adapter tests error: `DeprecationWarning: There is no current event loop` | `conftest.py` autouse fixture calls `get_event_loop()` for non-async tests on Python 3.12 | `python/tests/conftest.py` (delete fixture) |
| R-4 | P2 | Branch hygiene | 10 unmerged remote branches, 3 of which may contain salvageable work | No branch lifecycle policy | Decision per branch (see §Branches) |
| R-5 | P3 | Security | `.env` secrets still in git history (`git rm --cached` only) | History not rewritten | `git filter-repo` (≥7 days pre-public) |

---

## R-1: Node CI — `arc-ag-ui` test exits 1 ⚠️ CORRECTED

### Evidence
**CI log** (`.github/workflows/node.yml`, line 32):
```
pnpm -r --filter '!@arc-studio/e2e-tests' test
```
Fails at `packages/arc-ag-ui`:
```
packages/arc-ag-ui test: Could not find '.../packages/arc-ag-ui/test/**/*.test.js'
packages/arc-ag-ui test: Failed
ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL @arc/ag-ui@0.1.0 test: `node --test ./test/**/*.test.js`
Exit status 1
```

**Original diagnosis (INCORRECT)**: "The `packages/arc-ag-ui/` directory has no `test/` folder."

**Corrected diagnosis**: The `test/` directory **exists** and contains 4 real tests:
- `test/mapping.test.js` (1,869 bytes, 4 test cases)
- `test/fixtures/` (swarmgraph + langgraph golden files)

**Actual root cause** (`packages/arc-ag-ui/package.json`, line 11):
```json
"test": "node --test ./test/**/*.test.js"
```
The glob `./test/**/*.test.js` is **unquoted**. Per Node.js test runner docs and nodejs/node#50658:
- npm/pnpm run the script under POSIX `sh` (not interactive bash)
- POSIX `sh` has no `globstar` support (`**` is treated as `*`)
- The shell expands `./test/**/*.test.js` → `./test/*/*.test.js` (single-level)
- `test/mapping.test.js` is directly in `test/`, not in a subdirectory
- The pattern matches nothing; Node receives the literal string and exits 1

### Suggested Fix ✅ CORRECTED

**ONLY VALID FIX — Quote the glob**:
- File: `packages/arc-ag-ui/package.json`
- Line 11: Change test script to:
```json
"test": "node --test \"./test/**/*.test.js\""
```
This passes the glob to Node's internal globber, which supports `**` recursion.

**Alternative (also valid) — Drop the glob entirely**:
```json
"test": "node --test"
```
Node's default discovery includes `**/test/**/*.{cjs,mjs,js}`, which matches `test/mapping.test.js`.

**REJECTED OPTIONS** (from original plan):
- ❌ **Option A (`|| true`)** — Violates audit R-5 "no `|| true` in CI"; silently swallows real test failures
- ❌ **Option B (workspace filter)** — Skips 4 real tests that should run; regression in coverage
- ❌ **Option C (stub test)** — Already have 4 real tests; stub is meaningless

---

## R-2: ARC Roadmap Gate — `native-keymap` gyp build crash ✅ VERIFIED

### Evidence
**CI log** (`.github/workflows/arc-roadmap-gate.yml`, line 20 `pnpm install --frozen-lockfile`):
```
.../node_modules/native-keymap install: Package 'x11', required by 'virtual:world', not found
.../node_modules/native-keymap install: Package 'xkbfile', required by 'virtual:world', not found
.../node_modules/native-keymap install: gyp: Call to 'pkg-config x11 xkbfile --libs' returned exit status 1
 ELIFECYCLE  Command failed with exit code 1.
```

**Root cause**: The `node.yml` workflow installs native build deps at line 15-16:
```yaml
- name: Native build dependencies
  run: sudo apt-get update && sudo apt-get install -y build-essential pkg-config libx11-dev libxkbfile-dev libsecret-1-dev
```
The `arc-roadmap-gate.yml` workflow is **missing this step**. Theia depends on `native-keymap` which requires X11 development headers to compile.

**Verification notes**:
- `libsecret-1-dev` is included (likely for `keytar` or `@vscode/vsce` transitive deps)
- Keeping package list identical to `node.yml` prevents future drift bugs
- Eclipse Theia upstream uses the same inline `apt-get` pattern across workflows

### Suggested Fix ✅ VERIFIED
- File: `.github/workflows/arc-roadmap-gate.yml`
- After line 17 (`uses: astral-sh/setup-uv@v5`), before line 19 (`- name: Install`), insert:
```yaml

      - name: Native build dependencies
        run: sudo apt-get update && sudo apt-get install -y build-essential pkg-config libx11-dev libxkbfile-dev libsecret-1-dev
```
This mirrors the same step in `node.yml` (lines 15-16).

**Local verification** (Docker):
```bash
docker run --rm -v "$PWD":/repo -w /repo ubuntu:24.04 bash -c '
  apt-get update -qq &&
  apt-get install -y -qq build-essential pkg-config libx11-dev libxkbfile-dev libsecret-1-dev curl ca-certificates &&
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &&
  apt-get install -y -qq nodejs &&
  npm install -g pnpm@9.15.9 &&
  pnpm install --frozen-lockfile
'
# Expect: Install succeeds (60-90s)
```

---

## R-3: AG2 adapter tests — event loop DeprecationWarning ⚠️ CORRECTED

### Evidence
**CI log** (`python.yml`, step `Tests (strict warnings)`):
```
ERROR tests/adapters/ag2/test_adapter.py::test_detect - DeprecationWarning: There is no current event loop
ERROR tests/adapters/ag2/test_adapter.py::test_mapping_basic - DeprecationWarning: There is no current event loop
```

**Test file**: `python/tests/adapters/ag2/test_adapter.py`
- `test_detect` (line 9): synchronous, calls `is_ag2_workspace()`, no async
- `test_mapping_basic` (line 14): synchronous, calls `_map()`, no async
- `test_runner_with_fake_team` (line 19): uses `asyncio.run()`, works fine

**Conftest** (`python/tests/conftest.py`, lines 6-17):
```python
@pytest.fixture(autouse=True)
def close_pytest_asyncio_fallback_loop():
    """Close pytest-asyncio's fallback loop before -W error unraisable checks."""
    yield
    policy = asyncio.get_event_loop_policy()
    try:
        loop = policy.get_event_loop()
    except RuntimeError:
        return
    if not loop.is_closed():
        loop.close()
    policy.set_event_loop(None)
```

**pyproject.toml** config (`python/pyproject.toml`, line 51):
```toml
asyncio_mode = "auto"
```

**Root cause**: With `asyncio_mode = "auto"`, pytest-asyncio ≥0.23 owns the event loop lifecycle for async tests but does not create loops for purely synchronous tests. The `close_pytest_asyncio_fallback_loop` autouse fixture calls `asyncio.get_event_loop()` during teardown. On Python 3.12, when no loop exists on the current thread (the case for synchronous tests), this call emits `DeprecationWarning: There is no current event loop`. With `-W error`, this becomes an ERROR.

**Verification notes**:
- The fixture was added in commit 8d0be3c (2026-05-12) bundled with unrelated runtime-routing changes
- Original rationale: "Close pytest-asyncio's fallback loop before -W error unraisable checks"
- pytest-asyncio ≥0.23 in `auto` mode already handles loop cleanup; the fixture is now redundant
- Python 3.13 will remove `asyncio.get_event_loop()` entirely when no loop exists (currently deprecated → future-removed)

### Suggested Fix ✅ CORRECTED

**PRIMARY FIX — Option D: Delete the fixture** (recommended):
- File: `python/tests/conftest.py`
- Replace entire file with documenting stub:
```python
# Intentionally empty.
#
# A prior autouse fixture (close_pytest_asyncio_fallback_loop) was removed
# because pytest-asyncio >=0.23 in asyncio_mode = "auto" owns the event loop
# lifecycle and cleans it up itself. The fixture's call to
# asyncio.get_event_loop() emitted DeprecationWarning on Python 3.12 for
# synchronous tests (no loop on current thread), which became an error under
# -W error. See R-3 in the 2026-05-14 audit follow-up.
```
Or delete the file entirely: `git rm python/tests/conftest.py`

**FALLBACK FIX — Option A: Suppress the deprecation** (if Option D regresses):
- File: `python/tests/conftest.py`
- Wrap `get_event_loop()` with narrowly-scoped warning filter:
```python
import asyncio
import warnings

import pytest


@pytest.fixture(autouse=True)
def close_pytest_asyncio_fallback_loop():
    """Close pytest-asyncio's fallback loop before -W error unraisable checks."""
    yield
    policy = asyncio.get_event_loop_policy()
    # Python 3.12 deprecated asyncio.get_event_loop() when no loop is set on
    # the current thread, which is the case for purely synchronous tests under
    # asyncio_mode = "auto". Narrowly suppress that one DeprecationWarning so
    # other deprecations are still surfaced under -W error.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=DeprecationWarning, module=r"asyncio.*"
        )
        try:
            loop = policy.get_event_loop()
        except RuntimeError:
            return
    if not loop.is_closed():
        loop.close()
    policy.set_event_loop(None)
```

**REJECTED OPTIONS** (from original plan):
- ❌ **Option B (`@pytest.mark.filterwarnings` on fixture)** — Per pytest docs and issue #5677, `filterwarnings` does not apply to fixtures; silently ignored
- ❌ **Option C (nested conftest override)** — Per pytest issue #1601, overriding autouse fixtures via subdirectory conftest is unreliable and can raise `ValueError`

**Local verification**:
```bash
cd python

# Verify Option D (or A) fixes the two AG2 errors:
uv run pytest -W error tests/adapters/ag2/ -v
# Expect: 3 passed, 0 errors

# Verify no regressions elsewhere:
uv run pytest -W error
# Expect: same pass/skip count as before, no new errors or failures
# Watch for "ResourceWarning: unclosed event loop" — if seen, use Option A fallback

# Python 3.12 specific (where deprecation surfaces):
uv run --python 3.12 pytest -W error
```

---

## R-4: Unmerged remote branches (10 total)

### Branch Inventory
```
origin/handoff/no-mockups-github-ready   2026-05-11  HansuQWER  Prepare ARC Studio handoff
origin/recovered/troubleshooting-docs    2026-05-14  Agent      docs: add troubleshooting guides
origin/roadmap/pr-h2-web-coverage        2026-05-12  HansuQWER  Add implementation summary
origin/roadmap/pr1-pr3-ag-ui-foundation  2026-05-12  HansuQWER  test(sse): cover missing run events
origin/roadmap/pr10-health-monitor       2026-05-12  HansuQWER  feat(health): Python daemon health monitor
origin/roadmap/pr11-real-swarmgraph      2026-05-12  HansuQWER  feat(adapters): Phase 3 real execution
origin/roadmap/pr7-virtualized-list      2026-05-12  HansuQWER  docs: add Phase 2 execution prompt
origin/roadmap/pr8-event-filtering       2026-05-12  HansuQWER  feat(event-stream): event type filtering
origin/roadmap/pr9-otel-export           2026-05-12  HansuQWER  fix(telemetry): align OTLP export
origin/runtime/api-runs-start-field      2026-05-12  HansuQWER  theia: pin local daemon calls to loopback
```

### Suggested Actions
1. **`handoff/no-mockups-github-ready`** — stale handoff branch. Safe to delete (handoff content already archived in `docs/archive/`).
2. **`recovered/troubleshooting-docs`** — contains troubleshooting guides. Worth reviewing and merging if value-add.
3. **`runtime/api-runs-start-field`** — pins daemon to loopback. May contain security hardening. Worth reviewing.
4. **`roadmap/pr*` (7 branches)** — all ~3 days old, intentionally parked. If >60 days without activity, each needs either rebase-forward or formal abandonment.

### `git push origin --delete` candidates (safe now):
- `handoff/no-mockups-github-ready` (content already archived)

---

## R-5: `.env` history scrub (U-1)

### Evidence
`.env` was tracked in git history. It was removed from the index via `git rm --cached .env` (commit `b95f216`), but the file content remains in prior commits.

### Suggested Fix
```bash
# Run ≥7 days before public release (key already rotated)
git filter-repo --path .env --invert-paths
```
This rewrites all SHAs. Coordinate with all collaborators before doing so.

---

## Appendix A: CI workflow dependency map

```
node.yml (.github/workflows/node.yml)
├── checkout + pnpm setup + node setup
├── apt-get install libx11-dev libxkbfile-dev libsecret-1-dev  ← has native deps
├── pnpm install --frozen-lockfile
├── Bootstrap tests (arc-protocol.test.js)
├── PR hygiene (check-pr.sh)
├── pnpm -r build
└── pnpm -r --filter '!@arc-studio/e2e-tests' test  ← fails at arc-ag-ui

arc-roadmap-gate.yml (.github/workflows/arc-roadmap-gate.yml)
├── checkout + pnpm setup + node setup + uv setup
├── pnpm install --frozen-lockfile  ← MISSING: apt-get for native deps  ← CRASHES
├── pnpm lint
├── pnpm typecheck
├── AG-UI unit tests (cd arc-ag-ui && pnpm test)  ← also fails here
├── Protocol fixture tests
├── Python lint + type-check + tests
├── PR hygiene
└── No-live-provider regression check

python.yml (.github/workflows/python.yml)
├── checkout + uv setup
├── uv sync --all-extras --dev
├── ruff check
├── Artifact guard
├── pytest -q -W error  ← 245 pass, 2 AG2 errors
└── CLI smoke tests

e2e.yml (.github/workflows/e2e.yml)
├── depends on full Theia browser build
└── pre-existing failure (slow/test environment)
```

## Appendix B: Fix ordering & commit plan

Recommended order of execution:

1. **R-2 first** (ARC Roadmap Gate) — one line addition, unblocks a whole CI workflow
2. **R-1 second** (arc-ag-ui test) — quote one glob, unblocks Node CI
3. **R-3 third** (AG2 event loop) — delete conftest fixture, gets Python CI to 100% green
4. **R-4** (branches) — low effort, good hygiene. Delete handoff branch at minimum
5. **R-5** (git filter-repo) — schedule before public launch, not urgent now

### Suggested commits

**Commit 1: R-2**
```
fix(ci): install native build deps in arc-roadmap-gate workflow

Mirrors the apt-get step from node.yml (lines 15-16). Without this,
pnpm install fails when building native-keymap (requires libx11-dev
and libxkbfile-dev).

Closes R-2.
```
Files: `.github/workflows/arc-roadmap-gate.yml`

**Commit 2: R-1**
```
fix(arc-ag-ui): quote glob in test script for portable file discovery

The unquoted glob ./test/**/*.test.js fails under POSIX sh (no globstar
support). Shell expands ** as * (single-level), so test/mapping.test.js
is not matched. Quoting the glob passes it to Node's internal globber,
which supports ** recursion.

Refs: Node.js test runner docs, nodejs/node#50658
Closes R-1.
```
Files: `packages/arc-ag-ui/package.json`

**Commit 3: R-3**
```
test: remove conftest fixture that emits DeprecationWarning on Python 3.12

The autouse close_pytest_asyncio_fallback_loop fixture calls
asyncio.get_event_loop() during teardown. On Python 3.12, when no loop
exists on the current thread (the case for synchronous tests under
asyncio_mode = "auto"), this emits DeprecationWarning, which becomes
an ERROR under -W error.

pytest-asyncio >=0.23 in auto mode owns the loop lifecycle and doesn't
need this fixture. Removing it resolves the 2 AG2 adapter test errors.

Closes R-3.
```
Files: `python/tests/conftest.py` (replace with stub or delete)

### PR sequencing

**Option A — Single PR** (recommended):
- Title: `fix(ci): resolve 3 CI workflow failures (R-1, R-2, R-3)`
- All 3 commits in one PR
- Rationale: R-2 unblocks arc-roadmap-gate, R-1 unblocks node.yml, R-3 unblocks python.yml. All three required for fully green main. Reviewing together gives end-to-end context.

**Option B — Two PRs** (if review process prefers smaller units):
- PR 1: R-2 alone (smallest, safest, mechanically trivial)
- PR 2: R-1 + R-3 together

**Cross-PR dependencies**: None. Each fix is independent.

## Appendix C: Verification summary

| Issue | Original diagnosis | Verification result |
|-------|-------------------|---------------------|
| R-1 | "test/ folder does not exist" | ❌ **WRONG** — test/ exists with 4 real tests. Actual cause: unquoted glob under POSIX sh |
| R-1 fix | A/B/C (silence/exclude/stub) | ❌ **ALL WRONG** — Would suppress or skip 4 real tests. Correct fix: quote the glob |
| R-2 | Missing apt-get for native deps | ✅ **CORRECT** — Verified against node.yml and CI logs |
| R-2 fix | Add apt-get step | ✅ **CORRECT** — Mirrors node.yml verbatim |
| R-3 | conftest fixture + asyncio_mode interaction | ✅ **CORRECT** — Verified against pytest-asyncio docs and Python 3.12 deprecation |
| R-3 fix ordering | A/B/C/D | ⚠️ **REORDERED** — D first (delete), A as fallback. B/C rejected (invalid per pytest docs) |
