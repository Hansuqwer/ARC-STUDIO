#!/usr/bin/env bash
# ARC Studio — pre-commit check script
# Run: bash scripts/check.sh

set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

PASS=0; FAIL=0

run_check() {
  local name="$1"; shift
  echo -n "  $name... "
  if "$@" &>/dev/null; then
    echo "✓"; ((++PASS))
  else
    echo "✗ FAILED"; ((++FAIL))
  fi
}

echo ""
echo "ARC Studio — Check"
echo "==================="

echo ""
echo "Python:"
run_check "pytest (81 tests)"     bash -c "cd python && .venv/bin/python -m pytest tests/ -q 2>&1 | grep -q 'passed'"
run_check "arc --help"            bash -c "cd python && .venv/bin/arc --help" 
run_check "arc inspect --json"    bash -c "cd python && .venv/bin/arc inspect --json | python3 -c 'import sys,json; d=json.load(sys.stdin); exit(0 if d[\"ok\"] else 1)'"
run_check "conformance swarmgraph" bash -c "cd python && .venv/bin/arc adapter test swarmgraph --json | python3 -c 'import sys,json; d=json.load(sys.stdin); exit(0 if d[\"data\"][\"ok\"] else 1)'"

echo ""
echo "Node.js:"
run_check "fixtures unit test"    node tests/unit/arc-protocol.test.js
run_check "test fixtures OK"      node packages/arc-test-fixtures/src/index.js

echo ""
echo "Files:"
run_check "python/pyproject.toml" test -f python/pyproject.toml
run_check "applications/browser"  test -f applications/browser/package.json
run_check "applications/electron" test -f applications/electron/package.json
run_check "arc-extension protocol" test -f packages/arc-extension/src/common/arc-protocol.ts
run_check "docs/IMPLEMENTATION_PLAN.md" test -f docs/IMPLEMENTATION_PLAN.md

echo ""
if [[ $FAIL -eq 0 ]]; then
  echo "  ✓ All $PASS checks passed."
  exit 0
else
  echo "  ✗ $FAIL checks failed, $PASS passed."
  exit 1
fi
