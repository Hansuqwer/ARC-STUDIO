#!/usr/bin/env bash
# Fail if forbidden build artifacts are tracked in git.
# Some "generated" files are intentionally tracked (Theia src-gen, lockfiles);
# they are explicitly allow-listed below.
set -euo pipefail

echo "Checking for accidental generated artifacts..."

# Paths that look like artifacts but are required to be tracked.
ALLOWLIST_PATTERNS=(
  '^packages/arc-browser-app/src-gen/'   # Theia-generated, required for browser build
  '^\.env\.example$'                     # template, no secrets
)

violations=0
while IFS= read -r f; do
  # Skip allowlisted paths
  skip=0
  for allow in "${ALLOWLIST_PATTERNS[@]}"; do
    if [[ "$f" =~ $allow ]]; then skip=1; break; fi
  done
  [[ $skip -eq 1 ]] && continue

  # Check against forbidden patterns
  if echo "$f" | grep -E \
    '(^|/)(\.venv|\.venv2|node_modules|dist|lib|src-gen|test-results)(/|$)' \
    || echo "$f" | grep -E '(^|/)\.cache/' \
    || echo "$f" | grep -E '^python/\.arc/traces/.*\.jsonl$' \
    || echo "$f" | grep -E '^applications/.*/(gen-webpack(\.node)?\.config|webpack\.config)\.js$' \
    || echo "$f" | grep -E '(^|/)\.env(\..*)?$' \
    || echo "$f" | grep -E '\.(pem|key)$' \
    || echo "$f" | grep -E '(^|/)id_rsa$'; then
    echo "  $f"
    violations=$((violations + 1))
  fi
done < <(git ls-files)

if [[ $violations -gt 0 ]]; then
  echo "ERROR: $violation forbidden artifact(s) tracked in git."
  echo "Remove with: git rm --cached <file> and add to .gitignore."
  exit 1
fi

echo "Artifact check passed. No prohibited files tracked."
