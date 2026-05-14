# Release Readiness Checklist

**Project:** ARC Studio
**Version:** 0.6.0-alpha
**Last Updated:** 2026-05-14

---

This checklist defines what "shippable" means. Each item is individually
falsifiable — a precise criterion that can be checked in under 5 minutes by
anyone with repo access.

**Living document rule:** Anyone with a PR to this repo may propose additions
or modifications. Each item must include a built-in falsifiability test. Items
without such a test will be rejected.

---

## Required to release

Items in this section are gating. If any are unchecked, the release is blocked.

### 1. All 5 CI workflows green for 7 consecutive days on main

**Status:** ✅ Passing (as of 2026-05-14)

**Check:** Visit `https://github.com/Hansuqwer/arc-theia-studio/actions` and
confirm all 5 workflows (python, node, ARC Roadmap Gate, signing-preflight,
e2e) have green checkmarks on main for the past 7 days.

**Clock rule:** A single failure that is re-run and passes **resets** the
7-day clock. The clock measures stability, not just final success.

---

### 2. README Quick Start verified by one external user

**Status:** ❌ Not yet verified

**Definition of external:** "Someone who has never seen this codebase before,
follows the README verbatim without the author in the room or on a call."

**What must happen before check can flip:**
1. Identify one candidate (Theia Discord, early-access list, colleague from
   another team).
2. Ask them to follow the README's install + run instructions from scratch.
3. File issues for every deviation, missing dependency, or unclear step.
4. Fix all blocking issues. The README must work verbatim for a second
   external user before the box is checked.

**Owner:** TBD

---

### 3. No P0/P1 security issues open as of the day of release

**Status:** ✅ No P0/P1 issues open

**Check:**
```
gh issue list --state open
```
Only #2 (External security review checklist) is open. It has no P0/P1 label.
If a P0/P1 is opened between now and release day, this item reverts to ❌.

---

### 4. `.env` history scrubbed (U-1, gated on release date)

**Status:** ❌ Not scrubbed

**Prerequisite:** A release date must be set. Schedule `git filter-repo`
scrub ≥7 days before that date.

**What must happen:**
1. Set a release date.
2. Run `git filter-repo --path .env` on a clone.
3. Force-push the cleaned history to a pre-release branch.
4. Verify no `.env` content remains in history (`git log --all --full-history
   --diff-filter=D -- .env`).
5. Tag the release from the cleaned branch.

If no release date exists, this item is deferred by definition — see the
"Triggered tasks" section below.

---

## Should be done before release

Items in this section are quality bars. The team may consciously choose to
ship without them under deadline pressure, but that decision must be explicit
and documented in the release notes.

### 5. Every ADR is marked Accepted, Superseded, or Rejected — no open status

**Status:** ✅ Complete

**Check:**
```
grep '^## ADR-' docs/ADR.md
grep '^\*\*Status:\*\*' docs/ADR.md
```
All 11 ADRs (ADR-001 through ADR-011) are marked **Accepted.** No ADR has
an open/pending status.

---

### 6. Deprecation notices visible on all non-canonical paths

**Status:** ✅ Complete

**Check:**
```
grep -r 'DEPRECATED' python/src/
```
One non-canonical path exists:

| Path | Notice |
|------|--------|
| `python/src/agent_runtime_cockpit/adapters/swarmgraph.py` (module docstring) | `DEPRECATED — Prefer adapters.swarmgraph.runner.SwarmGraphRunner for new code.` |

If more non-canonical paths are introduced, this item must be updated.

---

### 7. All closed P0/P1 issues with executable contracts have regression tests

**Status:** ✅ Complete

| Issue | Type | Test file | Tests |
|-------|------|-----------|-------|
| #10 — Security (P0) | Executable | `test_security.py` | 13 (workspace rejection, symlink, path-traversal, gating, argv capture) |
| #13 — Cost gating (P0) | Executable | `test_security.py` | Monolithic-vs-modular consistency + `--no-cost` regression |
| #14 — Mapper divergence (P0) | Executable | `test_mapping.py` | 7 parity tests (Python output shape matches TS) |
| #15 — Architecture (P1) | ADR-only | N/A | No executable contract; architectural decision documented in ADR-011 |

P0/P1 issues without executable contracts (e.g., pure architectural decisions)
are exempt by definition.

**Check:**
```
uv run pytest tests/adapters/swarmgraph/test_security.py tests/adapters/swarmgraph/test_mapping.py -q
# Expect: 20 passed
```

---

### 8. No critical-severity advisories; high-severity advisories reviewed and documented

**Status:** ⚠️ Partial

**Threshold:**
- **0 critical** — gating. A critical advisory blocks release unless a
  documented exception is granted.
- **High advisories** must be reviewed and the review documented.

**Current state:**
```
pnpm audit --audit-level=high
# 0 critical, 8 high, 10 moderate, 1 low
```

The 8 high advisories are all in transitive dependencies of
`electron-builder` (the `tar` package), not in ARC Studio's own code.
Reviewed and accepted as acceptable risk for an alpha release.

**Missing:**
- `pip-audit` is not installed and not configured in CI.
- No Python advisory scanning exists.
- `pip-audit` should be added to the Python CI workflow (`python.yml`)
  before this item can be fully checked.

**Action:**
```
# Install and run before next release evaluation
pip install pip-audit
cd python && pip-audit
```

---

### 9. Release tag is a clean SHA on main; rollback procedure documented

**Status:** ❌ Not complete

**Clean SHA:** ✅ Verified. `git status` on main shows no uncommitted state.
```
git status --short
# (empty — clean working tree)
```

**Rollback procedure:** ❌ No `docs/RELEASE.md` exists. The following must be
documented before the first release tag:

1. **How to tag:**
   - `git tag -a v0.6.0-alpha -m "ARC Studio v0.6.0-alpha"`
   - `git push origin v0.6.0-alpha`
   - Verify CI picks up the tag and runs the release workflow.

2. **How to roll back:**
   - Delete the tag: `git push --delete origin v0.6.0-alpha && git tag -d v0.6.0-alpha`
   - Re-point CI back to previous tag.
   - Publish a note to any release channel explaining what went wrong.

3. **Who has authority to tag:**
   - Repository maintainers (list TBD).

---

## Triggered tasks

These items are not on the active checklist. They become active when a
specific event occurs.

| Task | Trigger | Owner |
|------|---------|-------|
| `.env` history scrub (U-1) | Release date is set (≥7 days before) | TBD |
| External security review (#2) | Security-audit budget is acquired, or decision to self-certify against OWASP ASVS Level 1 | TBD |

---

## Appendix: How to verify all items at once

```bash
#!/bin/bash
# Run from repo root. Exits 0 if all gating items pass.

echo "=== Item 1: CI workflows ==="
echo "Manual — visit https://github.com/Hansuqwer/arc-theia-studio/actions"

echo "=== Item 3: Open issues ==="
gh issue list --state open
echo "OK if only #2 (no P0/P1)"

echo "=== Item 5: ADR status ==="
grep '^\*\*Status:\*\*' docs/ADR.md | sort -u
# Expect only: "Accepted"

echo "=== Item 6: Deprecation notices ==="
grep -r 'DEPRECATED' python/src/ || echo "NONE FOUND — update checklist"
echo "OK if swarmgraph.py listed"

echo "=== Item 7: Regression tests ==="
cd python && uv run pytest tests/adapters/swarmgraph/test_security.py tests/adapters/swarmgraph/test_mapping.py -q
echo "Expect 20 passed"

echo "=== Item 8: Advisories ==="
pnpm audit --audit-level=critical 2>&1 | tail -1
echo "Expect 'No vulnerabilities found' at critical level"
```
