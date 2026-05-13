#!/usr/bin/env bash
set -euo pipefail

echo "Checking for accidental generated artifacts..."

if git ls-files | grep -v '\.env\.example$' | grep -E '(^|/)(\.venv|\.venv2|node_modules|dist|lib|src-gen|test-results)(/|$)|(^|/)\.cache/|^python/\.arc/traces/.*\.jsonl$|^applications/.*/(gen-webpack(\.node)?\.config|webpack\.config)\.js$|(^|/)\.env(\..*)?$|\.(pem|key)$|(^|/)id_rsa'; then
  echo "ERROR: Generated artifacts are tracked in git."
  echo "See .gitignore and docs/MOCK_POLICY.md."
  exit 1
fi

echo "Artifact check passed. No prohibited files tracked."
