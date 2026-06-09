# R-PROC3 / R-PROC5 / R-PROC6 — Release Hygiene Plan

Date: 2026-06-09
Auditor: Agentic Auditor
Repository: Hansuqwer/ARC-STUDIO @ e2526c3
Scope: Three process improvements with highest governance ROI per line of code. Eliminates
the exact failure modes that produced the stale PDF (arc-studio-unified-release-intel.pdf):
backdated timestamps, stale patch index, no locked release artifacts.

---

## 1. R-PROC3: Release Snapshot Generator

**Problem:** The stale PDF claimed baseline `788dbc9` (2026-06-04) but was re-dated to
2026-06-09. There is no automated snapshot that locks the release state at a point in time.

**Solution: `scripts/generate-release-snapshot.sh`**

```bash
#!/usr/bin/env bash
# scripts/generate-release-snapshot.sh
# Generates a dated, locked markdown snapshot of the current release state.
# Run immediately after tagging a release (or before generating any external deliverable).

set -euo pipefail

DATE=$(date +%Y-%m-%d)
COMMIT=$(git rev-parse HEAD)
SHORT_COMMIT=$(git rev-parse --short HEAD)
TAG=${1:-"untagged"}
OUT_DIR="docs/RELEASE_SNAPSHOTS"
OUT_FILE="${OUT_DIR}/snapshot-${TAG}-${DATE}-${SHORT_COMMIT}.md"

mkdir -p "${OUT_DIR}"

cat > "${OUT_FILE}" <<EOF
# ARC Studio Release Snapshot — ${TAG}

**Generated:** ${DATE}
**Commit:** \`${COMMIT}\`
**Tag:** ${TAG}
**Generator:** scripts/generate-release-snapshot.sh
**LOCKED:** This file is immutable. Do not edit. If the date on this file is newer than the
commit date, the deliverable was backdated.

---

## Git Summary (last 20 commits)

\`\`\`
$(git log --oneline -20)
\`\`\`

## Test Counts

\`\`\`
$(cd python && uv run pytest --collect-only -q 2>/dev/null | tail -5 || echo "pytest not available")
$(cd packages/arc-extension && npx jest --listTests 2>/dev/null | wc -l || echo "jest not available") TypeScript test files
\`\`\`

## Python LOC

\`\`\`
$(find python/src -name '*.py' | xargs wc -l | tail -1)
\`\`\`

## Roadmap Tail (v0.9)

\`\`\`
$(grep -A 20 'v0.9' docs/roadmap.md | head -25 || echo "v0.9 not found in roadmap")
\`\`\`

## Patch Index Freshness

\`\`\`
$(head -5 patches/INDEX.md)
\`\`\`

**WARNING:** If this snapshot's generated date (${DATE}) is significantly later than
the commit date ($(git log -1 --format=%ci)), investigate backdating.
EOF

echo "Snapshot written to: ${OUT_FILE}"
```

**CI Integration** — add to `.github/workflows/release.yml`:

```yaml
- name: Generate release snapshot
  run: bash scripts/generate-release-snapshot.sh ${{ github.ref_name }}
- name: Upload snapshot
  uses: actions/upload-artifact@v4
  with:
    name: release-snapshot-${{ github.ref_name }}
    path: docs/RELEASE_SNAPSHOTS/
```

---

## 2. R-PROC5: Date-Fabrication Detection in `check-banned-claims.sh`

**Problem:** The stale PDF contained `Generated: 2026-06-09` but actual content was from
`788dbc9` (2026-06-04). No automated check detects "Generated date > commit date of the file
containing it."

**Solution: Add `check_date_fabrication()` to `scripts/check-banned-claims.sh`**

```bash
check_date_fabrication() {
    local target="$1"
    local found=0

    for file in $(find "$target" -type f \( -name '*.md' -o -name '*.html' \) 2>/dev/null); do
        local gen_line
        gen_line=$(grep -n -i -E "(generated|date|created):\s*[0-9]{4}-[0-9]{2}-[0-9]{2}" \
            "$file" 2>/dev/null | head -1)
        [[ -z "$gen_line" ]] && continue

        local gen_date
        gen_date=$(echo "$gen_line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)

        local file_commit_date
        file_commit_date=$(git log -1 --format=%ci -- "$file" 2>/dev/null || echo "")
        [[ -z "$file_commit_date" ]] && continue

        local commit_date
        commit_date=$(echo "$file_commit_date" | cut -d' ' -f1)

        if [[ "$gen_date" > "$commit_date" ]]; then
            local line_num
            line_num=$(echo "$gen_line" | cut -d: -f1)
            echo "FABRICATED_DATE: $file:$line_num"
            echo "  Generated date: $gen_date"
            echo "  Commit date:    $commit_date"
            echo "  Suggestion: Update generated date to match commit date, or regenerate from HEAD."
            echo ""
            found=$((found + 1))
        fi
    done

    return $found
}
```

Add at the end of the main `check-banned-claims.sh` loop (before the final exit):

```bash
if [[ $# -gt 0 ]]; then
    DATE_OUTPUT=$(check_date_fabrication "$1" 2>&1) || DATE_FOUND=$?
    if [[ -n "$DATE_OUTPUT" ]]; then
        echo "$DATE_OUTPUT"
        TOTAL_MATCHES=$((TOTAL_MATCHES + ${DATE_FOUND:-0}))
    fi
fi
```

---

## 3. R-PROC6: `patches/INDEX.md` Freshness CI Gate

**Problem:** `patches/INDEX.md` claims baseline `788dbc9` (2026-06-04). HEAD is `e2526c3`
(2026-06-09), 437 commits ahead. No CI gate detects this.

**Solution: `scripts/check-patches-freshness.sh`**

```bash
#!/usr/bin/env bash
# scripts/check-patches-freshness.sh
# CI gate: fails if patches/INDEX.md baseline is > 24h older than HEAD.

set -euo pipefail

INDEX_FILE="patches/INDEX.md"
MAX_AGE_HOURS=24

[[ ! -f "$INDEX_FILE" ]] && { echo "ERROR: $INDEX_FILE not found."; exit 1; }

INDEX_BASELINE=$(grep -oE 'HEAD `[a-f0-9]+`' "$INDEX_FILE" | grep -oE '[a-f0-9]+' | head -1)
if [[ -z "$INDEX_BASELINE" ]]; then
    echo "WARNING: Could not parse baseline commit from $INDEX_FILE."
    exit 0
fi

HEAD_COMMIT=$(git rev-parse HEAD)
[[ "$INDEX_BASELINE" == "$HEAD_COMMIT" ]] && { echo "OK: patches/INDEX.md matches HEAD."; exit 0; }

if ! git merge-base --is-ancestor "$INDEX_BASELINE" "$HEAD_COMMIT" 2>/dev/null; then
    echo "ERROR: $INDEX_FILE baseline ($INDEX_BASELINE) is NOT an ancestor of HEAD."
    exit 1
fi

INDEX_DATE=$(git log -1 --format=%ci "$INDEX_BASELINE" 2>/dev/null || echo "")
HEAD_DATE=$(git log -1 --format=%ci "$HEAD_COMMIT")
[[ -z "$INDEX_DATE" ]] && { echo "WARNING: Could not get date for baseline commit."; exit 0; }

# macOS-compatible date arithmetic
INDEX_TS=$(date -j -f "%Y-%m-%d %H:%M:%S %z" "$INDEX_DATE" +%s 2>/dev/null \
    || date -d "$INDEX_DATE" +%s)
HEAD_TS=$(date -j -f "%Y-%m-%d %H:%M:%S %z" "$HEAD_DATE" +%s 2>/dev/null \
    || date -d "$HEAD_DATE" +%s)
DIFF_HOURS=$(( (HEAD_TS - INDEX_TS) / 3600 ))

if [[ $DIFF_HOURS -gt $MAX_AGE_HOURS ]]; then
    echo "ERROR: $INDEX_FILE is stale (${DIFF_HOURS}h old, max ${MAX_AGE_HOURS}h)."
    echo "  Baseline: $INDEX_BASELINE ($INDEX_DATE)"
    echo "  HEAD:     $HEAD_COMMIT ($HEAD_DATE)"
    echo "  Action:   Run bash scripts/regenerate-patches-index.sh or archive patches/."
    exit 1
fi

echo "OK: $INDEX_FILE is ${DIFF_HOURS}h old (within ${MAX_AGE_HOURS}h limit)."
```

**Companion: `scripts/regenerate-patches-index.sh`**

```bash
#!/usr/bin/env bash
# scripts/regenerate-patches-index.sh
# Updates the baseline in patches/INDEX.md to current HEAD.

set -euo pipefail
HEAD=$(git rev-parse HEAD)
DATE=$(date +%Y-%m-%d)
sed -i.bak "s/Generated: .*/Generated: ${DATE} against HEAD \`${HEAD}\`./" patches/INDEX.md
rm -f patches/INDEX.md.bak
echo "Updated patches/INDEX.md to HEAD ${HEAD} (${DATE})."
```

**CI Integration** — add to `.github/workflows/ci.yml`:

```yaml
jobs:
  patches-freshness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check patches freshness
        run: bash scripts/check-patches-freshness.sh
```

---

## 4. Summary

| ID | Script | Lines | CI Gate | Risk Prevented |
|---|---|---|---|---|
| R-PROC3 | `scripts/generate-release-snapshot.sh` | ~50 | Release workflow | Backdated/stale release artifacts |
| R-PROC5 | `scripts/check-banned-claims.sh` (date mode) | ~35 | Pre-commit + CI | Date-fabricated documents |
| R-PROC6 | `scripts/check-patches-freshness.sh` | ~45 | CI every PR | Stale patch index misinforming auditors |

Total: ~130 lines of bash. Eliminates the exact failure modes that produced the stale PDF.

---

## 5. Kiro Session Prompts

**R-PROC3:**
> Create `scripts/generate-release-snapshot.sh` that generates an immutable markdown snapshot
> in `docs/RELEASE_SNAPSHOTS/` containing: `git log --oneline -20`, pytest collect counts, jest
> test file counts, Python/TS LOC, roadmap v0.9 tail, and patch index header. The snapshot
> filename must include tag + date + short commit. The file must contain a LOCKED warning and
> a backdating detection note. Add a CI step to `.github/workflows/release.yml`. All existing
> CI must pass.

**R-PROC5:**
> Extend `scripts/check-banned-claims.sh` with a `check_date_fabrication()` function. For every
> `.md`/`.html` file, extract `Generated:`/`Date:`/`Created:` lines, compare the date to
> `git log -1 --format=%ci -- <file>`. If the extracted date is later than the commit date,
> report `FABRICATED_DATE`. Must be part of the normal `./scripts/check-banned-claims.sh docs/`
> run. The existing 23 banned phrases and their tests must still pass.

**R-PROC6:**
> Create `scripts/check-patches-freshness.sh` that: (1) parses the baseline HEAD from
> `patches/INDEX.md`, (2) verifies it is an ancestor of current HEAD, (3) computes age in hours,
> (4) exits 1 if > 24h. Also create `scripts/regenerate-patches-index.sh`. Add a CI job to
> `.github/workflows/ci.yml` that runs `check-patches-freshness.sh` on every PR. Use
> macOS-compatible `date` syntax. All existing CI must pass.
