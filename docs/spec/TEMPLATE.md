# vX.Y.Z-alpha — <ONE-LINE SUMMARY>

> **Release type:** <patch | feature | breaking>
> **Scope:** <one paragraph describing what ships and what doesn't>
> **Source / origin:** <link to research deliverable or prior tag's MERGE_NOTES>
>
> **Replace this whole blockquote** with one paragraph the reader can scan in 10 seconds.

---

## 0. Execution prompt (paste into your CLI session)

```text
<SPRINT-NAME> off origin/main HEAD (post-<PRIOR-TAG>).

Scope: <restate from header in agent-friendly terms>

Constraints (carry-over from prior tags):
  - Local-first, single-user. No public HTTP, no telemetry leaving the box.
  - No LLM in budget/security/eviction decisions (CoSAI — see
    docs/policy/cosai-llm-in-path.md).
  - EnforcementContext is @dataclass(frozen=True); use ContextVar.
  - Fail-closed on cost: unknown / exhausted budget → deny.
  - Additive protocol only. New typed events go in 3 Python sites
    (KnownRunEvent union, is_known_event set, parse_typed_event type_map in
    protocol/typed_events.py) AND 1 TS site (KnownRunEvent +
    KNOWN_RUN_EVENT_TYPES in packages/arc-protocol-ts/src/run-events.ts).
    Honor Pydantic extra="ignore" convention.
  - BudgetEnforcer in budget/schema.py is authoritative; legacy budget.py
    untouched.
  - Don't edit theia-extensions/* (legacy/archived).
  - One commit per logical change (conventional-commits). Each commit ships
    its own tests + CHANGELOG entry.
  - Honesty over polish — run `uv run pytest -q` before claiming green.
  - Do NOT tag or push <TAG> without explicit user go-ahead.
  - File:line citations for every repo claim.

Branch: spec/<SLUG> off origin/main HEAD (which is <SHA-OR-DESCRIPTION>).

Workflow:
  1. Task 0 — gap audit (~<N> min). See spec §2.
  2. Task 1 — <first feature> (~<N>h, ~<N> LOC).
  3. Task 2 — <next feature> (~<N>h, ~<N> LOC).
  ...
  N. Task N — Verify, export patches, CHANGELOG, commit per logical change.
  N+1. Task N+1 — Report back; await user go.

Report back template (paste filled-in):
  [ ] Task 0 audit (<N> lines)
  [ ] Tests: <BASELINE> → N (delta +M)
  [ ] Task 1 commit SHA + LOC
  [ ] Task 2 commit SHA + LOC
  ...
  [ ] Patches in patches/<sprint>/<TAG>/ (<N> files + LOC)
  [ ] All <N> verification gates green
  [ ] Pre-existing-acceptable failures only (≤2 + env)
  [ ] CHANGELOG updated with <N> bullets
  [ ] Roadmap row added
  Do NOT tag yet. Wait for my go.
```

---

## 1. Branch + base commit

| | |
|---|---|
| **Branch** | `spec/<SLUG>` |
| **Base** | `origin/main` @ `<SHA>` (post-`<PRIOR-TAG>`) |
| **Target tag** | `<TAG>` (after green-light) |
| **Expected commit count** | <N> (one per logical change) |
| **Expected duration** | <range> |

---

## 2. Repo facts to verify in Task 0

| Claim | File:line | Why it matters |
|---|---|---|
| <Surface stable from prior tag> | <path>:<line> | <consumer in this sprint> |
| <Helper/util exists> | <path> | <new code depends on it> |
| <Hook point grep-findable> | <path>:<func> | <where the new feature plugs in> |
| <No conflicting code already present> | <grep pattern> | gap confirmed |

**Task 0 commands:**

```bash
cd python

# <Repeat the verification claim from the table>
grep -n "<pattern>" src/agent_runtime_cockpit/<path>

# <Confirm hook point>
grep -rn "<pattern>" src/agent_runtime_cockpit/<dir>/ | head -10

# <Confirm gap>
grep -rn "<thing-that-should-not-exist-yet>" src/agent_runtime_cockpit/ | head -5
# expect: 0 hits
```

**STOP if** <any specific divergence>. Report finding before coding.

---

## 3. Files this release will touch

### Created

| Path | Purpose | Est LOC |
|---|---|---|
| `<src path>` | <one-line purpose> | ~<N> |
| `<test path>` | <one-line purpose> | ~<N> |
| `patches/<sprint>/<TAG>/001_<name>.patch` | Exported | ~<N> |
| `MERGE_NOTES.md` (overwrite) | Release notes for `<TAG>` | ~<N> |

### Modified

| Path | Change | Est LOC |
|---|---|---|
| `<existing path>` | <one-sentence delta> | ~<N> |
| `CHANGELOG.md` (`[Unreleased]`) | <N> bullets under <section> | ~<N> |
| `docs/roadmap.md` | <Row name> | ~5 |

### Not touched (out of scope, deliberately)

- <Path / module>: <why deliberately out>
- <Same>: <reason>

---

## 4. Task-by-task

### Task 1 — <Name> (~<N>h, ~<N> LOC)

<One paragraph describing what this task accomplishes.>

#### §A. <Sub-item>

<Code skeleton or implementation note>:

```python
# python/src/agent_runtime_cockpit/<path>.py
# ... pseudo or real ...
```

#### §B. <Sub-item>

<Test target>:

| File | New tests | Topic |
|---|---|---|
| `<test file>` | <N> | <comma-separated test purposes> |

### Task 2 — <Name> (~<N>h, ~<N> LOC)

<Repeat structure for each task>

### Task N — Verify, export patches, CHANGELOG, commit

```bash
cd python
uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -5
# expect: <BASELINE> + <N> new = <TARGET> passed; 0 failures

uv run ruff check src/agent_runtime_cockpit/<dirs> tests/<dirs> 2>&1 | tail -3

cd ..
pnpm --filter arc-protocol-ts test 2>&1 | tail -3
pnpm build && pnpm typecheck 2>&1 | tail -3
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md \
                                    docs/phases.md docs/release/checklist.md

# Export patches
mkdir -p patches/<sprint>/<TAG>
git format-patch -1 <SHA-1> --stdout > patches/<sprint>/<TAG>/001_<name>.patch
# ... repeat per logical commit ...

# Commit sequence (one per logical change, conventional-commits)
git add <files for commit 1>
git commit -m "feat(<scope>): <short description> (<TAG> 1/N)

<longer description with file:line citations + test count>"
# ... repeat per commit ...
```

### CHANGELOG.md entries (append under `[Unreleased]`)

```md
### Added
- <One-line user-visible improvement>. <Source / commit reference if useful>.
- <...>

### Changed
- <Behavior change that's not new, e.g., default value adjustments>.

### Deprecated
- <If applicable>.

### Fixed
- <If patch release>.
```

---

## 5. Verification gates

| Gate | Command | Expected |
|---|---|---|
| Python suite | `cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration` | <BASELINE> + <N> = <TARGET> passed / 0 failed |
| Python ruff | `uv run ruff check src/agent_runtime_cockpit/<dirs> tests/<dirs>` | clean |
| TS unit + coverage | `pnpm --filter arc-protocol-ts test --coverage` | green; ≥ thresholds |
| Workspace build | `pnpm build` | clean |
| Workspace typecheck | `pnpm typecheck` | clean |
| Banned claims | `bash scripts/check-banned-claims.sh ...` | clean |
| GitHub Actions | all green on push | ✅ |
| **Invariant 1: <name>** | `<test path>::<test name>` | passes |
| **Invariant 2: <name>** | `<test path>::<test name>` | passes |
| **Invariant 3 (CoSAI): No LLM in <path>** | import-guard test + runtime mock | passes |

**Pre-existing acceptable failures (only these allowed):**
- `tests/auth/test_auth_manager.py::test_provider_statuses_fallback_to_stored_creds`
- `tests/tasks/test_task_executor.py::test_concurrent_task_execution`
- openai.api_key_configured / kvm=True (CI-runner env only — pass locally)

Any other red → STOP and report.

---

## 6. (OPTIONAL) Behavior smoke tests

> Include this section if the feature changes user-observable behavior
> (compaction, eviction, routing changes, etc). Skip for pure plumbing/test
> patches.

### Smoke 1 — <Name>
```
1. <Step>
2. <Step>
3. Verify: <observable>
```

### Smoke 2 — <Name>
<...>

**Required for tag:** Smokes <list> pass.

---

## 7. Report-back template

```text
<TAG> readiness report:

[ ] Task 0 audit (<N> lines)
[ ] Tests: <BASELINE> → N (delta +M)
[ ] Task 1 commit SHA + LOC
[ ] Task 2 commit SHA + LOC
[ ] Patches in patches/<sprint>/<TAG>/ (<N> files + LOC)
[ ] All <N> verification gates green
[ ] Behavior smokes (if applicable):
    [ ] Smoke 1: PASS — <evidence>
    [ ] Smoke 2: PASS — <evidence>
[ ] Pre-existing-acceptable failures only (≤2 + env)
[ ] No EnforcementContext mutation
[ ] No LLM imports in <relevant files> (per CoSAI policy)
[ ] CHANGELOG [Unreleased] updated with <N> bullets
[ ] Roadmap row added

Branch spec/<SLUG> ready to merge.
Do NOT tag yet. Awaiting your go.
```

---

## 8. Merge + tag sequence (after green-light only)

```bash
cat > MERGE_NOTES.md <<'EOF'
# <TAG> — <SHORT TITLE>

<One paragraph summary.>

## What shipped
1. <Feature 1 — short description>
2. <Feature 2 — short description>

## Still deferred (tracked)
- <Item>: <why deferred + where to fix>

## Invariants verified
- <Invariant 1>
- <Invariant 2>
- No LLM in <path> per docs/policy/cosai-llm-in-path.md

## Verification
- Python: <COUNT> passed / 0 failed (+<DELTA> from <PRIOR-TAG>)
- TS: <COUNT> passed
- pnpm build + typecheck + banned-claims: clean
- GitHub Actions: all green on spec branch

## Commits
- <SHA> <commit message>
- <SHA> <commit message>
EOF

git add MERGE_NOTES.md
git commit -m "docs: MERGE_NOTES for <TAG>"

git checkout main && git pull --ff-only
git merge --no-ff spec/<SLUG> -m "$(cat MERGE_NOTES.md)"

git tag -a <TAG> -m "<headline one-liner>.

<2-3 sentences of detail.>
See MERGE_NOTES.md for full delta."

git push origin main <TAG>
```

---

## 9. What lands AFTER this tag

| Candidate | Source | Notes |
|---|---|---|
| <Next sprint candidate> | <research deliverable / prior MERGE_NOTES> | <why pick> |

---

## 10. Cross-references

- Plan / origin: <`TOKEN_SAVING_PLAN-2.md` or whichever>
- Research: <list relevant `docs/research/*.md`>
- Prior tag base: <relevant file:line for state inherited from last release>
- CoSAI policy: `docs/policy/cosai-llm-in-path.md`
- Redaction must compose with: `packages/arc-protocol-ts/src/run-diff.ts:redactDict`
- Project rules: `AGENTS.md`

---

## Template authoring notes (delete this section in real specs)

This template is derived from the v0.3.0-alpha → v0.5.0-alpha spec series.
Patterns enforced:

1. **§0 execution prompt is paste-ready.** Agent gets full context in one
   block without scrolling. Constraints repeated each time — agent doesn't
   need to remember.
2. **§2 forces a Task 0 audit BEFORE any code.** Cheapest way to catch
   stale assumptions. If `file:line` claims have drifted, stop and re-spec.
3. **§3 separates Created / Modified / Not-touched.** "Not touched" is
   explicit; prevents scope creep. LOC estimates set expectations.
4. **§4 task numbering matches commit numbering.** Each task → one
   conventional commit → one patch. Reviewers can cross-reference.
5. **§5 invariant gates make CoSAI auditable.** Import-guard tests +
   runtime mocks are first-class. Not "we reviewed it carefully."
6. **§6 behavior smokes are OPTIONAL.** Don't pad pure-plumbing tags;
   include for behavior-changing tags.
7. **§7 report-back is checklist format.** Easier for the agent to fill in;
   easier for the reviewer to scan; harder to fudge.
8. **§8 merge sequence is paste-ready** and includes MERGE_NOTES heredoc.
9. **"Do NOT tag without user go-ahead"** appears in §0 AND §7. Belt and
   suspenders.

When authoring a new spec from this template:
- Replace EVERY `<placeholder>` (search for `<`)
- Delete §11 "Template authoring notes"
- Adjust the §6 smoke section based on whether the feature changes behavior
- Update the Task 0 verification commands to match the actual repo state
