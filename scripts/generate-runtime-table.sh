#!/usr/bin/env bash
# generate-runtime-table.sh
#
# Runs `arc runtimes --capabilities --json` and regenerates the Markdown table
# in README.md between <!-- RUNTIMES:START --> and <!-- RUNTIMES:END --> markers.
#
# Usage:
#   bash scripts/generate-runtime-table.sh          # update README.md in place
#   bash scripts/generate-runtime-table.sh --check   # exit 1 if README differs

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
README="$REPO_ROOT/README.md"

CHECK_MODE=false
if [[ "${1:-}" == "--check" ]]; then
  CHECK_MODE=true
fi

# 1. Snapshot current README for check mode
if $CHECK_MODE; then
  ORIGINAL=$(cat "$README")
fi

# 2. Collect JSON from arc runtimes
JSON=$(cd "$REPO_ROOT/python" && uv run arc runtimes --capabilities --json 2>/dev/null)

# 3. Pipe JSON into the Python generator to update README
# 3. Pipe JSON into the Python generator to update README
if $CHECK_MODE; then
  # Quiet mode for check
  echo "$JSON" | python3 "$HERE/generate-runtime-table.py" --quiet "$README"
else
  echo "$JSON" | python3 "$HERE/generate-runtime-table.py" "$README"
fi

# 4. Check mode: verify README is unchanged
if $CHECK_MODE; then
  if diff -q <(echo "$ORIGINAL") "$README" >/dev/null 2>&1; then
    echo "README runtime table is up to date."
  else
    # Restore original and report error
    echo "$ORIGINAL" > "$README"
    echo "ERROR: README.md runtime table is stale. Run: bash scripts/generate-runtime-table.sh"
    exit 1
  fi
fi
