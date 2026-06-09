#!/usr/bin/env bash
# scripts/generate-release-snapshot.sh
# Generates a machine-readable release snapshot: version, test counts, git info.
#
# Usage:
#   bash scripts/generate-release-snapshot.sh              # print to stdout
#   bash scripts/generate-release-snapshot.sh --json       # JSON output
#   bash scripts/generate-release-snapshot.sh --out FILE   # write to file
#
# Output fields:
#   version          - Python package version from __init__.py
#   internal_track   - Internal release track from README.md (e.g. v0.8-r-ux5)
#   git_commit       - Full git commit SHA
#   git_short        - Short git commit SHA (8 chars)
#   git_branch       - Current branch or HEAD
#   git_dirty        - "true" if working tree has uncommitted changes
#   date_utc         - ISO-8601 UTC timestamp
#   python_tests     - Number of Python tests collected (uv run pytest --collect-only)
#   ruff_clean       - "true" if ruff check passes
#   banned_clean     - "true" if check-banned-claims passes on docs/roadmap.md + docs/phases.md
#   patches_stale    - Number of stale patch files
#
# Exit 0 always (snapshot is informational; use release_check.sh to gate).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

JSON_MODE=false
OUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)   JSON_MODE=true; shift ;;
        --out)    OUT_FILE="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 [--json] [--out FILE]"
            exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

# ── Version ──────────────────────────────────────────────────────────────────
VERSION=$(python3 -c "
import re, pathlib
src = pathlib.Path('python/src/agent_runtime_cockpit/__init__.py').read_text()
m = re.search(r'__version__\s*=\s*[\"\\x27]([^\"\\x27]+)[\"\\x27]', src)
print(m.group(1) if m else 'unknown')
" 2>/dev/null || echo "unknown")

INTERNAL_TRACK=$(grep -o 'v[0-9]\+\.[0-9]\+-r-[a-z0-9]\+' README.md 2>/dev/null | head -1 || echo "unknown")

# ── Git ───────────────────────────────────────────────────────────────────────
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_SHORT=${GIT_COMMIT:0:8}
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GIT_DIRTY="false"
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    GIT_DIRTY="true"
fi
DATE_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── Python test count ────────────────────────────────────────────────────────
PYTHON_TESTS="unknown"
if command -v uv &>/dev/null; then
    PYTHON_TESTS=$(cd python && uv run pytest --collect-only -q 2>/dev/null | \
        grep -o '^[0-9]\+ tests\? collected' | grep -o '^[0-9]\+' || echo "unknown")
fi

# ── Ruff clean? ───────────────────────────────────────────────────────────────
RUFF_CLEAN="false"
if command -v uv &>/dev/null; then
    if (cd python && uv run ruff check src tests --quiet 2>/dev/null); then
        RUFF_CLEAN="true"
    fi
fi

# ── Banned claims clean? ──────────────────────────────────────────────────────
BANNED_CLEAN="false"
if bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md &>/dev/null; then
    BANNED_CLEAN="true"
fi

# ── Stale patches ─────────────────────────────────────────────────────────────
PATCHES_STALE=0
if [[ -d patches ]]; then
    PATCHES_STALE=$(bash scripts/check-patches-freshness.sh 2>/dev/null | \
        grep -c '\[STALE\]' || true)
fi

# ── Output ────────────────────────────────────────────────────────────────────
if $JSON_MODE; then
    SNAPSHOT=$(cat <<EOF
{
  "version": "$VERSION",
  "internal_track": "$INTERNAL_TRACK",
  "git_commit": "$GIT_COMMIT",
  "git_short": "$GIT_SHORT",
  "git_branch": "$GIT_BRANCH",
  "git_dirty": $GIT_DIRTY,
  "date_utc": "$DATE_UTC",
  "python_tests": "$PYTHON_TESTS",
  "ruff_clean": $RUFF_CLEAN,
  "banned_clean": $BANNED_CLEAN,
  "patches_stale": $PATCHES_STALE
}
EOF
)
else
    SNAPSHOT=$(cat <<EOF
ARC Studio Release Snapshot
===========================
Version        : $VERSION
Internal track : $INTERNAL_TRACK
Git commit     : $GIT_SHORT ($GIT_BRANCH)$([ "$GIT_DIRTY" = "true" ] && echo " [dirty]" || true)
Date (UTC)     : $DATE_UTC
Python tests   : $PYTHON_TESTS
Ruff clean     : $RUFF_CLEAN
Banned clean   : $BANNED_CLEAN
Stale patches  : $PATCHES_STALE
EOF
)
fi

if [[ -n "$OUT_FILE" ]]; then
    echo "$SNAPSHOT" > "$OUT_FILE"
    echo "Snapshot written to: $OUT_FILE"
else
    echo "$SNAPSHOT"
fi

exit 0
