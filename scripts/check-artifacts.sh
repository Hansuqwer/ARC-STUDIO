#!/usr/bin/env bash
set -euo pipefail

echo "Checking for accidental generated artifacts..."

if git ls-files | grep -E '(^|/)(\.venv|\.venv2|node_modules|dist|lib|src-gen)(/|$)|(^|/)\.cache/|^python/\.arc/traces/.*\.jsonl$'; then
  echo "ERROR: Generated artifacts are tracked in git."
  echo "See .gitignore and docs/MOCK_POLICY.md."
  exit 1
fi

echo "Artifact check passed. No prohibited files tracked."
