# Release Readiness Checklist

**Project:** ARC Studio
**Version:** v0.1.0-alpha
**Last Updated:** 2026-05-14

**v0.1 Scope:**
- ✅ Browser app (`packages/arc-browser-app`)
- ✅ Python CLI/wheel (`python/`)
- ❌ Electron packaging — post-v0.1
- ❌ LM Arena product feature — stub-default with gated live path, not v0.1 scope
- ❌ SwarmGraph adoption — not implemented; only standalone adapters exist

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

**Status:** ❌ Not verified

**Check:**
```bash
pnpm install --frozen-lockfile
# Expect: exit 0, no lockfile changes
```

---

### 2. All build targets succeed

**Status:** ❌ Not verified

**Check:**
```bash
pnpm build
cd python && uv build
# Expect: both exit 0
```

---

### 3. `arc --help` prints and exits 0

**Status:** ❌ Not verified

**Check:**
```bash
cd python && uv run arc --help
# Expect: help text listing available commands, exit 0
```

---

### 4. `arc runtimes --capabilities --json` prints honest capability report

**Status:** ❌ Not verified

**Check:**
```bash
cd python && uv run arc runtimes --capabilities --json | python -m json.tool
# Expect: JSON with runtimes array. No runtime claims "SwarmGraph adoption".
# LM Arena must not claim live mode as a product feature.
```

---

### 5. Banned claims checker passes on key docs

**Status:** ✅ Passing (as of 2026-05-14)

**Check:**
```bash
bash scripts/check-banned-claims.sh README.md docs/IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md
# Expect: "OK: No banned claims found."
```

---

### 6. Python test suite passes

**Status:** ❌ Not verified

**Check:**
```bash
cd python && uv run pytest -q -W error
# Expect: all (or pre-existing known failures documented)
```

---

### 7. Canonical extension test suite passes

**Status:** ❌ Not verified

**Check:**
```bash
pnpm --filter arc-extension test
# Expect: all tests pass
```

---

### 8. No document implies implemented SwarmGraph adoption

**Status:** ❌ Not verified

**Check:**
```bash
bash scripts/check-banned-claims.sh docs/
# Exit 0 means no banned claims in any doc.
# Manual review confirming no "adoption layer" language in README describing current behavior.
```

---

### 9. `.env` history scrubbed (gated on release date)

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

---

## Should be done before release

Items in this section are quality bars. The team may consciously choose to
ship without them under deadline pressure, but that decision must be explicit
and documented in the release notes.

### 10. Browser app starts and loads ARC widget

**Status:** ❌ Not verified

**Check:**
```bash
pnpm start:browser 2>&1 &
sleep 30
curl -s http://localhost:3000 | grep -q 'arc-widget'
# Expect: page loads and ARC widget renders
```

---

### 11. All CI workflows green for 3 consecutive days on main

**Status:** ❌ Not verified

**Check:** Visit CI dashboard and confirm workflows (python, node, lint)
have green checkmarks on main for the past 3 days.

---

### 12. No P0/P1 security issues open

**Status:** ❌ Not verified

**Check:**
```bash
gh issue list --state open --label security
# Expect: no P0/P1 issues
```

---

### 13. README advertises only honest claims

**Status:** ❌ Not verified

**Check:** Manual review of README.md:
- Does not claim SwarmGraph adoption as implemented
- Does not claim active-run event delivery (says "SSE trace replay" if applicable)
- Does not claim HMAC-keyed audit trails
- LM Arena described as "stub-default with gated live path"
- No mention of Electron as current release path
- AG2 described honestly ("not registered")
- OpenAI Agents described honestly ("partial, hardcoded agent")
- LlamaIndex described honestly ("detection only")

---

## Triggered tasks

These items are not on the active checklist. They become active when a
specific event occurs.

| Task | Trigger | Owner |
|------|---------|-------|
| `.env` history scrub | Release date is set (≥7 days before) | TBD |
| Electron packaging spike | Canonical extension wiring + v0.1.0-alpha release | TBD |
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
bash scripts/check-banned-claims.sh README.md docs/IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md

echo "=== Item 6: Python tests ==="
cd python && uv run pytest -q -W error 2>&1 | tail -3

echo "=== Item 7: Extension tests ==="
pnpm --filter arc-extension test 2>&1 | tail -3

echo "=== Item 8: Banned claims (full docs) ==="
bash scripts/check-banned-claims.sh docs/ 2>&1 | tail -3
```
