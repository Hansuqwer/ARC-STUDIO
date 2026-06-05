# Policy: Honesty Over Polish

> **Status:** Authoritative for ARC Studio sprint reporting + commit messages + CHANGELOG entries.
> **Owner:** Spec authors + agents executing sprints + reviewers.
> **Last updated:** 2026-06-04
> **Companion to:** `docs/policy/cosai-llm-in-path.md`, `docs/policy/local-first.md`, `docs/policy/protocol-additive-only.md`
> **Origin:** Lock the "Built = tested + green; run `uv run pytest -q` before claiming green" rule that's been repeated in every spec preamble since v0.3.0-alpha. Future specs reference this policy by ID instead of restating.

---

## The rule

**"Built" means: code written + tests written + tests pass + linter clean + claim verified by command output.**

Anything less requires explicit qualifier language:
- "Drafted" — code exists, tests don't or didn't pass
- "Sketched" — incomplete; structure shown but logic stubbed
- "In progress" — currently running; outcome unknown
- "Deferred" — explicitly punted to later tag with tracking note

The default for an unqualified claim is the strict definition. The agent (or human) MUST run the verification command and observe success before saying "shipped," "complete," "done," "green," "passing," or any synonym.

---

## Specific anti-patterns this policy forbids

| Anti-pattern | Example | Why forbidden |
|---|---|---|
| **Claim-without-run** | "Tests pass" without `uv run pytest` output in the report | Falsifiable claim presented as verified |
| **Optimistic gerund** | "Passing" / "compiling" / "building" as ongoing state when not verified | Hides whether the command actually ran |
| **Test-count handwave** | "About 30 tests" without exact number | Either you ran them or you didn't |
| **Selective output** | Reporting only the `passed` count, omitting `failed` / `xfailed` / `skipped` | Skewed signal |
| **Pre-emptive CHANGELOG** | Adding `### Added — X feature` before X is committed + tested | Future-tense disguised as past-tense |
| **Vague invariants** | "No LLM in path" without import-guard test or grep proof | Trust-me security claim |
| **Phantom file:line citations** | Referencing `budget/schema.py:162` without verifying the line exists today | Stale spec assumptions surface mid-task |
| **"Should pass" / "will pass"** | Future tense for what's claimed shipped | If it should pass, run it and confirm |
| **Bundled commit message lies** | "feat: X + Y + Z" when only X tested green | Commit message overstates evidence |
| **Re-running until green, claiming "always green"** | Suppressing flake reports | Flakes are evidence; don't hide them |

---

## The required report format

Every sprint completion report (`spec §7 report-back template`) MUST include verifiable evidence per claim:

| Claim type | Required evidence |
|---|---|
| "All tests pass" | Exact pre/post count + 0 failures (or named pre-existing failures) |
| "Specific commit landed" | Commit SHA |
| "File touches LOC" | `git diff --stat` output or explicit LOC count |
| "All gates green" | One line per gate with PASS/FAIL |
| "Invariant verified" | Test name (`tests/path::test_name`) that asserts the invariant |
| "Behavior smoke pass" | One sentence per smoke describing observable outcome |
| "No regression" | If pre-existing failure: cite the SHA where it was first observed |

A report that says "all gates green" without per-gate breakdown is **not compliant**.

---

## Verification commands of record

These commands are the source of truth for "green":

```bash
# Python tests
cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration

# Python lint
cd python && uv run ruff check src/agent_runtime_cockpit/<dirs> tests/<dirs>

# TS tests
pnpm --filter arc-protocol-ts test

# TS coverage gate
pnpm --filter arc-protocol-ts test --coverage

# Full workspace build
pnpm build

# Full workspace typecheck
pnpm typecheck

# Banned claims (catches "complete" / "production-ready" / etc. in docs)
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md \
                                    docs/phases.md docs/release/checklist.md

# GitHub Actions (post-push)
gh run list --branch main --limit 8 --json conclusion,name,status \
  --jq '.[] | "\(.conclusion // .status)\t\(.name)"'
```

A claim of "green" requires the actual output of these commands, not paraphrased summaries.

**Pre-existing acceptable failures (only these allowed):**
- `tests/auth/test_auth_manager.py::test_provider_statuses_fallback_to_stored_creds`
- `tests/tasks/test_task_executor.py::test_concurrent_task_execution`
- `openai.api_key_configured` (CI-runner env config; passes locally)
- `kvm=True` (CI-runner env config; passes locally)

Any other failure is **not** "pre-existing"; it's a regression requiring triage.

---

## Honest qualifier vocabulary

Use these when full verification isn't done:

| Word | Meaning | When to use |
|---|---|---|
| **Drafted** | Code written; tests not yet written or not yet passing | Mid-task progress reports |
| **Sketched** | Pseudo-code or skeleton; not executable | Early-stage spec drafts |
| **In progress** | Currently running; outcome pending | While CI is mid-run |
| **Locally verified** | Tests pass on the author's machine; CI not yet confirmed | Pre-push reports |
| **CI verified** | All required workflows green on the SHA | Post-push readiness |
| **Tag-ready** | All gates green; report-back complete; awaiting human go | Pre-tag handoff |
| **Shipped** | Tag exists; pushed to origin; CI green on tag SHA | Post-tag |
| **Deferred** | Explicitly punted with tracking note in MERGE_NOTES | Always with target tag and reason |
| **Known flaky** | Test passes locally; intermittent in CI; tracking issue filed | Never use to dismiss a real failure |

**Avoid:** "passing" (ongoing state), "complete" (vague), "production-ready" (banned by `check-banned-claims.sh`), "ready to ship" (without specifying what gate).

---

## Specific report-back checks

When filling in a spec's §7 report-back template:

- [ ] Did you run `uv run pytest -q` in `python/`? If yes, paste the last 5 lines of output.
- [ ] Is the test delta number from actual `pytest` output, not estimated?
- [ ] Did each invariant gate get a PASS or FAIL line? Vague "green" is non-compliant.
- [ ] If a behavior smoke is listed PASS, can you describe the observable evidence in one sentence?
- [ ] If a behavior smoke is listed SKIP, did you say why?
- [ ] Are commit SHAs real (7+ chars) or placeholder `<SHA>`?
- [ ] Does the patch LOC count match `wc -l patches/<sprint>/<TAG>/*.patch`?
- [ ] Are pre-existing failures named individually, not just "the usual pre-existing ones"?

---

## What this policy does NOT prohibit

The rule is about **truthfulness of claims**, not about how cautious work has to be:

- **Drafting commits before tests pass is fine** — just don't claim "tests pass" until they do
- **Reporting in-progress state is fine** — just qualify it ("currently running CI on <SHA>")
- **Citing prior tags as "shipped" is fine** — they are; that's a verifiable fact
- **Optimism in commit messages is fine** if the message describes the intent ("feat: add X with N tests" when N is real)

The rule is: **the words you use must match the verification you did.**

---

## Failure modes this prevents

The patterns this policy locks down are not hypothetical:

1. **Agent claims "all tests pass" then user runs CI and 12 fail.** The agent had run a subset that excluded the failures. Honest reporting would say "tests/<scope> pass: 47/0; full suite not run."

2. **CHANGELOG ships claiming "added X feature" but the feature is only partially implemented.** Future-you reads the CHANGELOG, can't find the feature, distrusts all future CHANGELOGs.

3. **Spec says "test_foo exists" but it doesn't.** Next sprint depends on test_foo as evidence; discovers absence mid-task; sprint stalls.

4. **Invariant claim "no LLM in budget path" without import-guard test.** Future PR adds an import; nobody catches it; policy is silently violated.

5. **"All gates green" hides one yellow.** User merges; CI fails on main; everyone scrambles.

Each of these has happened in real software. The policy is the cheap insurance against them.

---

## Enforcement

Compliance with this policy is checked by:

1. **Spec template §7 format** — the report-back template forces per-claim evidence
2. **`check-banned-claims.sh`** — greps docs for forbidden vague claims ("production-ready," "complete," etc.)
3. **Code review** — reviewers reject reports lacking the required evidence per §"The required report format"
4. **Post-tag retrospective** — when a tag's CHANGELOG claim doesn't match reality, the gap is logged and policy is referenced

This policy has no formal automated test (unlike CoSAI's import-guard or local-first's network-call audit) because the test is **the report itself**. The agent or human writing the report is the test; the policy is the rubric the reviewer uses.

---

## Resolution procedure for ambiguous reporting cases

If you're uncertain how to honestly describe what's done:

1. **Default to the more conservative qualifier.** "Drafted" beats "shipped" when in doubt.
2. **Specify what's missing.** "Tests pass except test_X which is flaky; tracking issue #N."
3. **Cite commands run.** "Ran `uv run pytest tests/budget`: 47/0. Did not run full suite."
4. **Ask for review.** If a claim seems too strong for the evidence, surface it for a second opinion before publishing.

The cost of over-qualifying is a slightly verbose report. The cost of over-claiming is broken trust. Always choose the verbose report.

---

## Cross-references

- Companion policy: `docs/policy/cosai-llm-in-path.md` (no LLM in decisions)
- Companion policy: `docs/policy/local-first.md` (deployment topology)
- Companion policy: `docs/policy/protocol-additive-only.md` (protocol evolution)
- Spec template reference: `docs/spec/TEMPLATE.md` §7 enforces this policy
- Banned-claims grep: `scripts/check-banned-claims.sh` (the automated half of enforcement)
- Project rules: `AGENTS.md`
- Origin: every spec since v0.3.0-alpha has carried "Honesty over polish" in its constraints block; this is the canonical statement.
