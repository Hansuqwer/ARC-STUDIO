#!/usr/bin/env bash
# Audit enforcement surfaces for ungated syscalls (Phase 23.2)
#
# Scans Python source for security-sensitive syscall patterns and verifies
# that each site has an enforcement annotation:
#   # enforcement: gated - Protected by enforcement helper
#   # enforcement: not-applicable - Safe context (e.g., internal logging, tests)
#
# Exit codes:
#   0 - All syscalls properly annotated
#   1 - Found ungated syscalls

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Syscall patterns to detect (security-sensitive operations)
PATTERNS=(
    "subprocess\."           # Shell execution
    "requests\."             # HTTP requests
    "httpx\."                # HTTP requests (httpx library)
    "urllib\.request"        # HTTP requests (urllib)
    "socket\.socket"         # Raw socket operations
    "\.bind\("               # Socket binding
    "\.connect\("            # Socket connections
    "open\("                 # File operations (may access workspace files)
)

# Directories to scan
SCAN_DIRS=(
    "python/src/agent_runtime_cockpit"
)

# Directories to exclude
EXCLUDE_PATTERNS=(
    "test"
    "__pycache__"
    ".pyc"
    ".venv"
)

echo "=== Enforcement Surface Audit ==="
echo "Scanning for ungated syscalls in Python source..."
echo ""

VIOLATIONS=0
TOTAL_MATCHES=0

for pattern in "${PATTERNS[@]}"; do
    echo "Checking pattern: $pattern"
    
    # Build exclude arguments for grep
    EXCLUDE_ARGS=""
    for exclude in "${EXCLUDE_PATTERNS[@]}"; do
        EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-dir=$exclude"
    done
    
    # Find matches
    matches=$(grep -rn "$pattern" "${SCAN_DIRS[@]}" \
        --include="*.py" \
        $EXCLUDE_ARGS \
        2>/dev/null || true)
    
    if [[ -n "$matches" ]]; then
        while IFS= read -r line; do
            TOTAL_MATCHES=$((TOTAL_MATCHES + 1))
            
            file=$(echo "$line" | cut -d: -f1)
            lineno=$(echo "$line" | cut -d: -f2)
            
            # Check for enforcement annotation within 5 lines before or after
            annotation=$(sed -n "$((lineno-5)),$((lineno+5))p" "$file" 2>/dev/null | \
                grep -E "# enforcement: (gated|not-applicable)" || true)
            
            if [[ -z "$annotation" ]]; then
                echo "  ❌ UNGATED: $file:$lineno"
                echo "     $(sed -n "${lineno}p" "$file" | sed 's/^[[:space:]]*//')"
                VIOLATIONS=$((VIOLATIONS + 1))
            fi
        done <<< "$matches"
    fi
done

echo ""
echo "=== Audit Summary ==="
echo "Total syscall sites found: $TOTAL_MATCHES"
echo "Ungated violations: $VIOLATIONS"
echo ""

if [[ $VIOLATIONS -gt 0 ]]; then
    echo "❌ FAILED: Found $VIOLATIONS ungated syscalls"
    echo ""
    echo "To fix, add one of these annotations near each syscall:"
    echo "  # enforcement: gated - Protected by enforcement helper"
    echo "  # enforcement: not-applicable - Safe context (explain why)"
    echo ""
    echo "Example:"
    echo "  # enforcement: gated"
    echo "  subprocess.run(['ls', '-la'], check=True)"
    exit 1
fi

echo "✅ PASSED: All syscalls properly annotated"
exit 0
