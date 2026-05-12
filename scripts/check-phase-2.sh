#!/bin/bash
# Phase 2 Execution Script
# This script guides agents through Phase 2 research completion

set -e

echo "=================================================="
echo "Phase 2 - Research Lock Execution"
echo "=================================================="
echo ""
echo "Date: $(date)"
echo "Working Directory: $(pwd)"
echo ""

# Check if docs directory exists
if [ ! -d "docs" ]; then
    echo "❌ ERROR: docs/ directory not found"
    echo "Run: mkdir -p docs"
    exit 1
fi

echo "✅ Documentation directory exists"
echo ""

# Check required files
REQUIRED_FILES=(
    "docs/PHASE_2_EXECUTION_PROMPT.md"
    "docs/RESEARCH_NOTES.md"
    "docs/IMPLEMENTATION_DECISIONS.md"
    "docs/PHASE_2_STATUS.md"
)

echo "Checking required documentation files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (MISSING)"
        exit 1
    fi
done
echo ""

# Check research completion status
echo "=================================================="
echo "Research Area Status"
echo "=================================================="
echo ""

check_research_section() {
    local section="$1"
    local file="docs/RESEARCH_NOTES.md"
    
    if grep -q "Status: Complete" "$file" && grep -B5 "Status: Complete" "$file" | grep -q "$section"; then
        echo "  ✅ $section - Complete"
        return 0
    elif grep -q "Status: In Progress" "$file" && grep -B5 "Status: In Progress" "$file" | grep -q "$section"; then
        echo "  🔄 $section - In Progress"
        return 1
    else
        echo "  ⏳ $section - Pending"
        return 1
    fi
}

RESEARCH_AREAS=(
    "Eclipse Theia"
    "Context7"
    "GitHub Search API"
    "Vercel Grep"
    "LangGraph"
    "SwarmGraph Repository"
    "AG-UI Event Streaming"
    "Vercel Platform"
)

COMPLETED=0
TOTAL=${#RESEARCH_AREAS[@]}

for area in "${RESEARCH_AREAS[@]}"; do
    if check_research_section "$area"; then
        ((COMPLETED++))
    fi
done

echo ""
echo "Progress: $COMPLETED/$TOTAL research areas complete"
echo ""

# Check implementation decisions
echo "=================================================="
echo "Implementation Decisions Status"
echo "=================================================="
echo ""

DECISION_COUNT=$(grep -c "^|" docs/IMPLEMENTATION_DECISIONS.md | tail -1 || echo "0")
# Subtract header rows (2)
DECISION_COUNT=$((DECISION_COUNT - 2))

if [ "$DECISION_COUNT" -gt 0 ]; then
    echo "  ✅ $DECISION_COUNT implementation decisions documented"
else
    echo "  ⏳ No implementation decisions documented yet"
fi
echo ""

# Check for Phase 2 completion
echo "=================================================="
echo "Phase 2 Completion Check"
echo "=================================================="
echo ""

if [ -f "docs/PHASE_2_COMPLETE.md" ]; then
    echo "✅ Phase 2 is COMPLETE"
    echo ""
    echo "Sign-off document: docs/PHASE_2_COMPLETE.md"
    echo ""
    echo "You may proceed to Phase 3 - Discovery Lock"
    exit 0
else
    echo "⏳ Phase 2 is NOT COMPLETE"
    echo ""
    echo "Remaining work:"
    echo "  - Complete research for $((TOTAL - COMPLETED)) areas"
    echo "  - Document all major implementation decisions"
    echo "  - Agent 0 review and approval"
    echo "  - Create docs/PHASE_2_COMPLETE.md with sign-off"
    echo ""
    echo "Next steps:"
    echo "  1. Review docs/PHASE_2_EXECUTION_PROMPT.md for detailed instructions"
    echo "  2. Assign research tasks to agents"
    echo "  3. Update docs/RESEARCH_NOTES.md as research completes"
    echo "  4. Document decisions in docs/IMPLEMENTATION_DECISIONS.md"
    echo "  5. Run this script again to check progress"
    echo ""
    exit 1
fi
