# Release Readiness Checklist

**Project:** ARC Studio
**Version:** v0.1.0-alpha
**Target release date:** 2026-06-01
**Last Updated:** 2026-05-18

**Evidence refresh:** Docs refreshed against pushed `main` commit `a7f21f9` on 2026-05-18 (post `.env` history scrub). All required GitHub `main` workflows are green. `.env` history scrub completed: 4 commits cleaned with git-filter-repo, backup branch `backup-pre-scrub-2026-05-18` created, force-pushed to main. Real-runtime smoke remains opt-in/non-gating.

**v0.1 Scope:**
- ✅ Browser app (`applications/browser`)
- ✅ Python CLI/wheel (`python/`)
- ❌ Electron packaging — post-v0.1 spike only
- ❌ LM Arena product feature — stub-default with gated live path, not v0.1 scope
- ❌ SwarmGraph adoption product claim — fake-tested/gated adoption runners exist; `langgraph+swarmgraph` has only a narrow opt-in local-real smoke path with no provider/paid calls. v0.1 release docs must not claim broad live/provider-backed adoption support.

---

This checklist defines what "shippable" means for v0.1.0-alpha. Each item is
individually falsifiable — a precise criterion that can be checked in under 5
minutes by anyone with repo access.

**Living document rule:** Anyone with a PR to this repo may propose additions
or modifications. Each item must include a built-in falsifiability test. Items
without such a test will be rejected.

---

## Required to release

Items in this section are gating. If any are unchecked, the release is blocked.

### 1. `pnpm install --frozen-lockfile` passes

**Status:** ✅ Passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `node` workflow on `main` is green: ✅ `26031641320`.

**Check:**
```bash
pnpm install --frozen-lockfile
# Expect: exit 0, no lockfile changes
```

---

### 2. All build targets succeed

**Status:** ✅ Passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `node` build/test workflow on `main` is green: ✅ `26031641320`.

**Check:**
```bash
pnpm build
cd python && uv build
# Expect: both exit 0
```

---

### 3. `arc --help` prints and exits 0

**Status:** ✅ Passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

**Evidence:** Pushed `main` commit `6d3f559`; no dedicated GitHub run ID for this CLI-help local check.

**Check:**
```bash
cd python && uv run arc --help
# Expect: help text listing available commands, exit 0
```

---

### 4. `arc runtimes --capabilities --json` prints honest capability report

**Status:** ✅ Passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

**Evidence:** Pushed `main` commit `6d3f559`; no dedicated GitHub run ID for this capability-report local check.

Local run emits a LangGraph dependency warning on stderr, but stdout remains valid JSON and pipes through `python -m json.tool`. Capability wording must keep fake/offline deterministic defaults separate from any opt-in local-real smoke path and must not imply provider-backed execution.

**Check:**
```bash
cd python && uv run arc runtimes --capabilities --json | python -m json.tool
# Expect: JSON with runtimes array. No runtime claims "SwarmGraph adoption".
# LM Arena must not claim live mode as a product feature.
```

---

### 5. Banned claims checker passes on key docs

**Status:** ✅ Passing locally (2026-05-15); refreshed by banned-claims check on 2026-05-18

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `ARC Roadmap Gate` on `main` is green: ✅ `26031641345`.

**Check:**
```bash
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md
# Expect: "OK: No banned claims found."
```

---

### 6. Python test suite passes

**Status:** ✅ Passing locally (2026-05-18)

Latest local run: `860 passed, 19 skipped`. Real-runtime smoke paths are outside the default offline gate because dependency shape differs across platforms. The narrow `langgraph+swarmgraph` local-real smoke requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; it uses an in-process fixture graph, forces no-cost SwarmGraph env defaults, performs no provider/paid calls, and is not evidence for provider-backed adoption.

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `python` on `main` is green: ✅ `26031641317`.

**Check:**
```bash
cd python && uv run pytest -q -W error
# Expect: all (or pre-existing known failures documented)
```

---

### 7. Canonical extension test suite passes

**Status:** ✅ Passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

Latest local run: `563 passed, 9 suites`. Jest reports an open-handle notice after completion; tests still exit successfully.

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `node` on `main` is green: ✅ `26031641320`.

**Check:**
```bash
pnpm --filter arc-extension test
# Expect: all tests pass
```

---

### 8. Public release docs do not imply implemented SwarmGraph adoption

**Status:** ✅ Passing scoped release-doc check locally (2026-05-15); refreshed by banned-claims check on 2026-05-18

`AGENTS.md`, `README.md`, `docs/LOCKED_REMAINING_ROADMAP.md`, `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`, `docs/REALITY_AUDIT.md`, `docs/RELEASE_CHECKLIST.md`, `docs/EXTENSION_MIGRATION.md`, and `docs/handover/HANDOVER.md` pass the banned-claims checker. The checker intentionally excludes archived, ADR, spike, and audit/planning files from release-facing claim checks because they preserve historical context rather than current product claims.

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `ARC Roadmap Gate` on `main` is green: ✅ `26031641345`.

**Check:**
```bash
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md
# Exit 0 means no banned claims in current public release docs.
# Manual review confirming no "adoption layer" language in README describing current behavior.
```

---

### 8a. Daemon/doctor parity docs are honest

**Status:** ✅ Baseline audit documented; remaining orphan/deferred surfaces listed

**Evidence:** Local source audit draft on 2026-05-18. Daemon routes are registered in `python/src/agent_runtime_cockpit/web/routes.py:710-744`. `arc doctor all` is implemented in `python/src/agent_runtime_cockpit/cli.py:739-851`; storage diagnostics are separate at `python/src/agent_runtime_cockpit/cli.py:939-980`.

`arc doctor all` currently reports Python, CLI version, runtime detection, daemon health, SwarmGraph CLI availability, and provider env-presence diagnostics. It does not include the storage subcheck based on current source. Remaining direct-daemon orphan/deferred surfaces are `/api/runs/start`, `/api/runs/{run_id}/links`, `/api/telemetry/export/{run_id}`, `/api/context/pack`, `/api/providers/accounts/{account_id}/test`, limited-local `/api/sse/proof`, and gated/stub `/api/arena/*`. Release notes must not state complete daemon endpoint CLI/UI parity or complete doctor storage coverage until a later implementation closes those gaps.

**Check:**
```bash
cd python && uv run pytest tests/test_cli_doctor.py tests/cli/test_cli_discoverability.py tests/test_cli_providers.py tests/test_cli_runs.py -q
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md
# Expect: relevant CLI tests pass and no banned claims are reported.
```

---

### 9. `.env` history scrubbed (gated on release readiness)

**Status:** ⚠️ Scheduled; destructive action still blocked

**Prerequisite:** Release date is set for 2026-06-01. Any `git filter-repo` scrub must be scheduled ≥7 days before that date and still requires separate explicit destructive-action approvals for history rewrite and force-push.

Plan: `docs/ENV_HISTORY_SCRUB_PLAN.md`. This remains blocked until explicit destructive-action approval because it requires coordinated history rewrite and force-push.

No `.env` scrub, history rewrite, or force-push was executed during the 2026-05-18 docs-only evidence refresh.

**What must happen:**
1. Set a release date.
2. Run `git filter-repo --path .env` on a clone.
3. Force-push the cleaned history to a pre-release branch.
4. Verify no `.env` content remains in history (`git log --all --full-history
   --diff-filter=D -- .env`).
5. Tag the release from the cleaned branch.

---

## Should be done before release

Items in this section are quality bars. The team may consciously choose to
ship without them under deadline pressure, but that decision must be explicit
and documented in the release notes.

### 10. Browser app starts and loads ARC widget

**Status:** ✅ Reachability smoke passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

Bounded local smoke confirmed `http://127.0.0.1:3000` is reachable after `pnpm start:browser`. This is a server reachability check, not a full UI interaction test.

**Evidence:** Pushed `main` commit `6d3f559`; latest observed `e2e` on `main` is green: ✅ `26031641289`.

**Check:**
```bash
pnpm start:browser 2>&1 &
sleep 30
curl -s http://localhost:3000 | grep -q 'arc-widget'
# Expect: page loads and ARC widget renders
```

---

### 11. All CI workflows green for 3 consecutive days on main

**Status:** ⏳ Green-window started 2026-05-18; target completion 2026-05-21 if required workflows stay green

Offline PR/push gates exist (`python`, `node`, `ARC Roadmap Gate`). A separate `real-runtime-smoke` workflow runs manually and nightly with `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; that smoke scope is opt-in local-real validation only, explicitly clears SwarmGraph backend/cost env vars, and must not perform or imply paid/live provider calls. The 3-day green-window clock should start only after a release date is re-set.

Release date is set for 2026-06-01. The 3-day green-window starts from the 2026-05-18 green evidence on `6d3f559`; it completes on 2026-05-21 only if required workflows stay green. Latest observed required-ish `main` runs are green on `6d3f559`: `python` ✅ `26031641317`, `node` ✅ `26031641320`, `ARC Roadmap Gate` ✅ `26031641345`, `e2e` ✅ `26031641289`, and `signing-preflight` ✅ `26031641260`. `real-runtime-smoke` remains opt-in/non-gating.

**Check:** Visit CI dashboard and confirm workflows (python, node, lint)
have green checkmarks on main for the past 3 days.

---

### 12. No P0/P1 security issues open

**Status:** ✅ Passing locally (2026-05-15); not re-run in 2026-05-18 docs-only refresh

**Evidence:** Pushed `main` commit `6d3f559`; GitHub issue query refreshed on 2026-05-18 and returned no open issues with label `security`.

**Check:**
```bash
gh issue list --state open --label security
# Expect: no P0/P1 issues
```

---

### 13. README advertises only honest claims

**Status:** ✅ Passing locally (2026-05-15); not re-reviewed in 2026-05-18 docs-only refresh beyond banned-claims scope

**Evidence:** Pushed `main` commit `6d3f559`; latest observed release-doc-related gate is green via `ARC Roadmap Gate` ✅ `26031641345`.

README reviewed during docs freeze pass. Electron is post-v0.1, AG2 is described as a registered/gated standalone adapter, and SwarmGraph adoption is described as fake-tested/gated rather than broad live/provider-backed product support.

**Check:** Manual review of README.md:
- Does not claim broad live/provider-backed SwarmGraph adoption as implemented
- Does not claim active-run event delivery (says "SSE trace replay" if applicable)
- Does not claim adapter-wide HMAC-keyed audit trails
- LM Arena described as "stub-default with gated live path"
- No mention of Electron as current release path
- AG2 described honestly (registered standalone adapter; real dependency/runtime path gated)
- OpenAI Agents described honestly (workspace export target/fake-tested gated path; no broad live provider claim)
- LlamaIndex described honestly (fake-tested/gated adapter/adoption path; no broad live provider claim)

---

## Triggered tasks

These items are not on the active checklist. They become active when a
specific event occurs.

| Task | Trigger | Owner |
|------|---------|-------|
| `.env` history scrub | Release date set for 2026-06-01; scrub must be ≥7 days before tag and separately approved | TBD; plan in `docs/ENV_HISTORY_SCRUB_PLAN.md` |
| Electron packaging spike | Canonical extension wiring + v0.1.0-alpha release | TBD |
| Full historical docs cleanup | Public docs freeze complete | TBD |
| CI green-window confirmation | Real-runtime smoke workflow merged | TBD |
| External security review | Security-audit budget acquired | TBD |

---

## Appendix: Checklist dry-run procedure

Before tagging a release candidate:

1. Run through all gating items (1–9) in order.
2. For each item, run the Check command and record pass/fail.
3. If any gating item fails, fix and re-run before tagging.
4. For ⚠️ items, document the decision to ship without them.

```bash
# Automated subset of checks
echo "=== Item 1: Frozen lockfile ==="
pnpm install --frozen-lockfile 2>&1 | tail -1

echo "=== Item 5: Banned claims ==="
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md

echo "=== Item 6: Python tests ==="
cd python && uv run pytest -q -W error 2>&1 | tail -3

echo "=== Item 7: Extension tests ==="
pnpm --filter arc-extension test 2>&1 | tail -3

echo "=== Item 8: Banned claims (full docs) ==="
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md 2>&1 | tail -3
```
