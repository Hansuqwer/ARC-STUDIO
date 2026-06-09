#!/usr/bin/env bash
# scripts/check-patches-freshness.sh
# Verifies that patch files in patches/ still apply cleanly against HEAD.
# Exit 0 = all patches still valid.
# Exit 1 = one or more patches have become stale (conflict or missing files).
#
# Usage:
#   bash scripts/check-patches-freshness.sh              # check all patches
#   bash scripts/check-patches-freshness.sh patches/r01/ # check specific dir
#
# CI gate: add as a job step. Stale patches must be either applied, updated,
# or removed from patches/ before merge.
#
# NOTE: uses `git apply --check --whitespace=nowarn` — read-only, no changes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PATCH_DIRS=()
if [[ $# -gt 0 ]]; then
    PATCH_DIRS=("$@")
else
    # Default: all .patch files under patches/
    while IFS= read -r -d '' d; do
        PATCH_DIRS+=("$d")
    done < <(find patches -name "*.patch" -print0 2>/dev/null | sort -z)
fi

if [[ ${#PATCH_DIRS[@]} -eq 0 ]]; then
    echo "check-patches-freshness: no patch files found under patches/ — OK"
    exit 0
fi

STALE=0
CHECKED=0

for item in "${PATCH_DIRS[@]}"; do
    # Accept either a directory or a direct .patch file
    if [[ -d "$item" ]]; then
        mapfile -d '' PATCH_FILES < <(find "$item" -name "*.patch" -print0 | sort -z)
    elif [[ -f "$item" && "$item" == *.patch ]]; then
        PATCH_FILES=("$item")
    else
        continue
    fi

    for patch in "${PATCH_FILES[@]}"; do
        CHECKED=$((CHECKED + 1))
        if git apply --check --whitespace=nowarn "$patch" 2>/dev/null; then
            echo "  [ok]   $patch"
        else
            echo "  [STALE] $patch  ← patch no longer applies cleanly"
            STALE=$((STALE + 1))
        fi
    done
done

echo ""
echo "Patches checked: $CHECKED  |  Stale: $STALE"

if [[ $STALE -gt 0 ]]; then
    echo "FAIL: $STALE stale patch(es) found. Apply, update, or remove them before merging."
    exit 1
fi

echo "PASS: all patches apply cleanly."
exit 0
