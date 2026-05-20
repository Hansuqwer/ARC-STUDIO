#!/usr/bin/env bash
# Phase 3 Pre-flight Verification Script
# Run this before starting Phase 3 execution to verify all foundation artifacts are in place

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Phase 3 Pre-flight Verification ==="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

# Check 1: RuntimeMode enum exists
echo "Checking RuntimeMode enum..."
if [ -f "$PROJECT_ROOT/python/src/agent_runtime_cockpit/runtime/mode.py" ]; then
    check_pass "RuntimeMode enum file exists"
else
    check_fail "RuntimeMode enum file missing"
fi

# Check 2: RuntimeMode unit tests exist
echo "Checking RuntimeMode unit tests..."
if [ -f "$PROJECT_ROOT/python/tests/unit/test_runtime_mode.py" ]; then
    check_pass "RuntimeMode unit tests exist"
else
    check_fail "RuntimeMode unit tests missing"
fi

# Check 3: RuntimeMode tests pass
echo "Running RuntimeMode unit tests..."
cd "$PROJECT_ROOT/python"
if uv run pytest tests/unit/test_runtime_mode.py -q > /dev/null 2>&1; then
    check_pass "RuntimeMode unit tests pass (24 tests)"
else
    check_fail "RuntimeMode unit tests failing"
fi

# Check 4: Migration contract test exists
echo "Checking migration contract test..."
if [ -f "$PROJECT_ROOT/python/tests/contract/test_runtime_capability_migration.py" ]; then
    check_pass "Migration contract test exists"
else
    check_fail "Migration contract test missing"
fi

# Check 5: v1 fixtures exist
echo "Checking v1 fixtures..."
V1_DIR="$PROJECT_ROOT/python/tests/contract/fixtures/runtime-capability/v1"
if [ -d "$V1_DIR" ]; then
    FIXTURE_COUNT=$(find "$V1_DIR" -name "*.json" | wc -l | tr -d ' ')
    if [ "$FIXTURE_COUNT" -ge 3 ]; then
        check_pass "v1 fixtures directory exists with $FIXTURE_COUNT fixtures"
    else
        check_warn "v1 fixtures directory exists but only has $FIXTURE_COUNT fixtures (expected 3+)"
    fi
else
    check_fail "v1 fixtures directory missing"
fi

# Check 6: v2 fixtures directory exists
echo "Checking v2 fixtures directory..."
V2_DIR="$PROJECT_ROOT/python/tests/contract/fixtures/runtime-capability/v2"
if [ -d "$V2_DIR" ]; then
    check_pass "v2 fixtures directory exists (ready for migration outputs)"
else
    check_fail "v2 fixtures directory missing"
fi

# Check 7: RuntimeCapability model exists (expected to fail until Phase 3 starts)
echo "Checking RuntimeCapability model..."
if [ -f "$PROJECT_ROOT/python/src/agent_runtime_cockpit/runtime/capability.py" ]; then
    check_pass "RuntimeCapability model exists"
else
    check_warn "RuntimeCapability model not yet created (expected - create in Phase 3 Slice 2)"
fi

# Check 8: Phase 2 status
echo "Checking Phase 2 status..."
cd "$PROJECT_ROOT"
if git tag | grep -q "phase-2-complete"; then
    check_pass "phase-2-complete tag exists"
else
    check_warn "phase-2-complete tag not found (Phase 2 must complete before Phase 3)"
fi

# Check 9: Current branch
echo "Checking git branch..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "phase-2-cli-consolidation" ]; then
    check_warn "Still on phase-2-cli-consolidation branch (switch to phase-3-runtime-semantics when ready)"
elif [ "$CURRENT_BRANCH" = "phase-3-runtime-semantics" ]; then
    check_pass "On phase-3-runtime-semantics branch"
else
    check_warn "On branch: $CURRENT_BRANCH"
fi

# Check 10: ADR-016 exists
echo "Checking ADR-016..."
if [ -f "$PROJECT_ROOT/docs/adr/ADR-016-cli-consolidation.md" ]; then
    check_pass "ADR-016 exists"
else
    check_warn "ADR-016 not found (verify ADR numbering)"
fi

echo ""
echo "=== Summary ==="
echo -e "${GREEN}Passed: $PASS${NC}"
if [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $WARN${NC}"
fi
if [ $FAIL -gt 0 ]; then
    echo -e "${RED}Failed: $FAIL${NC}"
fi

echo ""
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ Phase 3 foundation artifacts are in place${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Complete Phase 2 and merge to main"
    echo "  2. Tag phase-2-complete"
    echo "  3. Create phase-3-runtime-semantics branch"
    echo "  4. Run Phase 3 execution prompt"
    echo ""
    echo "Phase 3 Slice 1 (RuntimeMode) is already complete and tested."
    echo "Phase 3 Slice 2 (RuntimeCapability) is next."
    exit 0
else
    echo -e "${RED}✗ Some foundation artifacts are missing${NC}"
    echo "Fix the failures above before starting Phase 3."
    exit 1
fi
