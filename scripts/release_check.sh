#!/usr/bin/env bash
# release_check.sh — Run every verification gate from docs/spec/TEMPLATE.md §5
#                    in one command. Returns 0 if release-ready; nonzero
#                    with a per-gate report otherwise.
#
# Usage:
#     bash scripts/release_check.sh
#     bash scripts/release_check.sh --skip-ts      # skip TS gates
#     bash scripts/release_check.sh --skip-banned  # skip banned-claims grep
#     bash scripts/release_check.sh --json         # machine-readable output
#     bash scripts/release_check.sh --help
#
# Exit codes:
#     0   All gates green; release-ready
#     1   One or more gates failed
#     2   Usage error / required tool missing
#
# This script is the runtime mirror of docs/policy/honesty-over-polish.md —
# it makes the verification gates auditable rather than self-reported.

set -uo pipefail   # NOT -e; we want to run ALL gates and report all failures

# ─── colors (off if not TTY) ────────────────────────────────────────────────
if [ -t 1 ]; then
    R='\033[0;31m'
    G='\033[0;32m'
    Y='\033[0;33m'
    B='\033[0;34m'
    NC='\033[0m'
else
    R=''
    G=''
    Y=''
    B=''
    NC=''
fi

# ─── arg parse ──────────────────────────────────────────────────────────────
SKIP_TS=0
SKIP_BANNED=0
SKIP_PNPM=0
JSON_OUTPUT=0

for arg in "$@"; do
    case $arg in
        --help|-h)
            grep '^#' "$0" | head -25 | sed 's/^# //; s/^#//'
            exit 0
            ;;
        --skip-ts)
            SKIP_TS=1
            shift
            ;;
        --skip-banned)
            SKIP_BANNED=1
            shift
            ;;
        --skip-pnpm)
            SKIP_PNPM=1
            shift
            ;;
        --json)
            JSON_OUTPUT=1
            shift
            ;;
        *)
            echo "Unknown arg: $arg" >&2
            echo "Run --help for usage." >&2
            exit 2
            ;;
    esac
done

# ─── repo root detection ────────────────────────────────────────────────────
if ! command -v git >/dev/null 2>&1; then
    echo "git not found" >&2
    exit 2
fi
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    echo "Not in a git repo" >&2
    exit 2
fi
cd "$REPO_ROOT"

# ─── per-gate state ─────────────────────────────────────────────────────────
declare -A RESULTS
declare -A DURATIONS
declare -A OUTPUTS_TAIL

run_gate() {
    local name="$1"
    local cmd="$2"
    local start_ts
    start_ts=$(date +%s)

    if [ "$JSON_OUTPUT" -eq 0 ]; then
        printf "${B}▸${NC} %-30s " "$name"
    fi

    local output
    if output=$(bash -c "$cmd" 2>&1); then
        local exit_code=0
    else
        local exit_code=$?
    fi

    local elapsed=$(( $(date +%s) - start_ts ))
    DURATIONS[$name]=$elapsed

    # Capture last 5 lines for context on failure
    OUTPUTS_TAIL[$name]=$(echo "$output" | tail -5)

    if [ $exit_code -eq 0 ]; then
        RESULTS[$name]="PASS"
        [ "$JSON_OUTPUT" -eq 0 ] && printf "${G}PASS${NC}  (%ds)\n" "$elapsed"
    else
        RESULTS[$name]="FAIL"
        [ "$JSON_OUTPUT" -eq 0 ] && printf "${R}FAIL${NC}  (%ds)\n" "$elapsed"
    fi
}

skip_gate() {
    local name="$1"
    local reason="$2"
    RESULTS[$name]="SKIP"
    DURATIONS[$name]=0
    OUTPUTS_TAIL[$name]="skipped: $reason"
    if [ "$JSON_OUTPUT" -eq 0 ]; then
        printf "${Y}▸${NC} %-30s ${Y}SKIP${NC}  (%s)\n" "$name" "$reason"
    fi
}

# ─── gate definitions ───────────────────────────────────────────────────────
[ "$JSON_OUTPUT" -eq 0 ] && echo "ARC Studio release check  ─  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ "$JSON_OUTPUT" -eq 0 ] && echo "Repo: $REPO_ROOT"
[ "$JSON_OUTPUT" -eq 0 ] && echo

# ─── Python ─────────────────────────────────────────────────────────────────
if [ -d "python" ] && command -v uv >/dev/null 2>&1; then
    run_gate "python:pytest" \
        "cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1"
    run_gate "python:ruff" \
        "cd python && uv run ruff check src tests 2>&1"
else
    skip_gate "python:pytest" "no python/ dir OR uv not installed"
    skip_gate "python:ruff" "no python/ dir OR uv not installed"
fi

# ─── TypeScript / pnpm ──────────────────────────────────────────────────────
if [ "$SKIP_TS" -eq 1 ] || [ "$SKIP_PNPM" -eq 1 ]; then
    skip_gate "ts:test" "--skip-ts or --skip-pnpm requested"
    skip_gate "ts:coverage" "--skip-ts or --skip-pnpm requested"
elif command -v pnpm >/dev/null 2>&1; then
    if [ -d "packages/arc-protocol-ts" ]; then
        run_gate "ts:test" \
            "pnpm --filter arc-protocol-ts test 2>&1"
        run_gate "ts:coverage" \
            "pnpm --filter arc-protocol-ts test --coverage 2>&1"
    else
        skip_gate "ts:test" "no packages/arc-protocol-ts dir"
        skip_gate "ts:coverage" "no packages/arc-protocol-ts dir"
    fi
else
    skip_gate "ts:test" "pnpm not installed"
    skip_gate "ts:coverage" "pnpm not installed"
fi

if [ "$SKIP_PNPM" -eq 1 ]; then
    skip_gate "pnpm:build" "--skip-pnpm requested"
    skip_gate "pnpm:build:prod" "--skip-pnpm requested"
    skip_gate "pnpm:typecheck" "--skip-pnpm requested"
elif command -v pnpm >/dev/null 2>&1; then
    run_gate "pnpm:build" "pnpm build 2>&1"
    # Validate the actual release artifact: the browser app in production mode.
    run_gate "pnpm:build:prod" "pnpm --filter @arc-studio/browser build:prod 2>&1"
    run_gate "pnpm:typecheck" "pnpm typecheck 2>&1"
else
    skip_gate "pnpm:build" "pnpm not installed"
    skip_gate "pnpm:build:prod" "pnpm not installed"
    skip_gate "pnpm:typecheck" "pnpm not installed"
fi

# ─── Banned claims ──────────────────────────────────────────────────────────
if [ "$SKIP_BANNED" -eq 1 ]; then
    skip_gate "banned-claims" "--skip-banned requested"
elif [ -x "scripts/check-banned-claims.sh" ]; then
    BANNED_TARGETS=(AGENTS.md README.md)
    [ -f "docs/roadmap.md" ] && BANNED_TARGETS+=(docs/roadmap.md)
    [ -f "docs/phases.md" ] && BANNED_TARGETS+=(docs/phases.md)
    [ -f "docs/release/checklist.md" ] && BANNED_TARGETS+=(docs/release/checklist.md)
    run_gate "banned-claims" \
        "bash scripts/check-banned-claims.sh ${BANNED_TARGETS[*]} 2>&1"
else
    skip_gate "banned-claims" "scripts/check-banned-claims.sh not found"
fi

# ─── Mobile SDK gates (native-safety + SBOM + compliance) ───────────────────
if command -v uv >/dev/null 2>&1 && [ -d "runtimes/mobile" ]; then
    run_gate "mobile:native-safety" \
        "cd python && uv run pytest -q tests/test_mobile_expo_scaffold.py tests/test_mobile_expo_example.py tests/test_mobile_rn.py tests/test_mobile_flutter.py 2>&1"
    run_gate "mobile:sbom" \
        "cd python && uv run arc mobile sbom --json 2>&1 | grep -q CycloneDX"
    run_gate "mobile:compliance" \
        "cd python && uv run arc mobile generate compliance-report --json 2>&1 | grep -q requires_human_review"
    run_gate "mobile:deps-audit" \
        "bash scripts/mobile-deps-audit.sh"
    run_gate "mobile:provenance" \
        "cd python && uv run arc mobile provenance --json 2>&1 | grep -q arc-mobile-provenance"
else
    skip_gate "mobile:native-safety" "uv not installed or no runtimes/mobile"
    skip_gate "mobile:sbom" "uv not installed or no runtimes/mobile"
    skip_gate "mobile:compliance" "uv not installed or no runtimes/mobile"
    skip_gate "mobile:deps-audit" "uv not installed or no runtimes/mobile"
    skip_gate "mobile:provenance" "uv not installed or no runtimes/mobile"
fi

# ─── Spec citation verification ─────────────────────────────────────────────
if [ -x "scripts/spec_verify.py" ] || [ -f "scripts/spec_verify.py" ]; then
    SPEC_FILES=()
    if [ -d "docs/spec" ]; then
        while IFS= read -r -d '' f; do
            # Skip TEMPLATE.md (it has intentional placeholders)
            [[ "$(basename "$f")" == "TEMPLATE.md" ]] && continue
            SPEC_FILES+=("$f")
        done < <(find docs/spec -maxdepth 1 -name '*.md' -print0)
    fi
    if [ ${#SPEC_FILES[@]} -gt 0 ]; then
        run_gate "spec:citations" \
            "python3 scripts/spec_verify.py ${SPEC_FILES[*]} --quiet 2>&1"
    else
        skip_gate "spec:citations" "no docs/spec/*.md files"
    fi
else
    skip_gate "spec:citations" "scripts/spec_verify.py not found"
fi

# ─── Import-guard tests (CoSAI / local-first compliance) ────────────────────
# Run if specific test files exist (per docs/policy/cosai-llm-in-path.md and
# docs/policy/local-first.md). These are explicit policy enforcement tests.
if [ -d "python" ] && command -v uv >/dev/null 2>&1; then
    POLICY_TESTS=()
    [ -f "python/tests/policy/test_no_llm_imports.py" ] && POLICY_TESTS+=("python/tests/policy/test_no_llm_imports.py")
    [ -f "python/tests/policy/test_no_telemetry_imports.py" ] && POLICY_TESTS+=("python/tests/policy/test_no_telemetry_imports.py")
    [ -f "python/tests/policy/test_local_first_compliance.py" ] && POLICY_TESTS+=("python/tests/policy/test_local_first_compliance.py")

    if [ ${#POLICY_TESTS[@]} -gt 0 ]; then
        run_gate "policy:import-guards" \
            "cd python && uv run pytest -q ${POLICY_TESTS[*]/#python\//} 2>&1"
    else
        skip_gate "policy:import-guards" "no python/tests/policy/test_no_*_imports.py files"
    fi
fi

# ─── Protocol coverage (per docs/policy/protocol-additive-only.md) ──────────
if [ -d "python" ] && command -v uv >/dev/null 2>&1; then
    if [ -f "python/tests/protocol/test_typed_event_coverage.py" ]; then
        run_gate "policy:protocol-coverage" \
            "cd python && uv run pytest -q tests/protocol/test_typed_event_coverage.py 2>&1"
    else
        skip_gate "policy:protocol-coverage" "no test_typed_event_coverage.py"
    fi
fi

# ─── git cleanliness check ──────────────────────────────────────────────────
GIT_STATUS=$(git status --porcelain 2>&1)
if [ -z "$GIT_STATUS" ]; then
    RESULTS["git:clean"]="PASS"
    DURATIONS["git:clean"]=0
    [ "$JSON_OUTPUT" -eq 0 ] && printf "${B}▸${NC} %-30s ${G}PASS${NC}  (working tree clean)\n" "git:clean"
else
    RESULTS["git:clean"]="WARN"
    DURATIONS["git:clean"]=0
    OUTPUTS_TAIL["git:clean"]="uncommitted changes present"
    [ "$JSON_OUTPUT" -eq 0 ] && printf "${Y}▸${NC} %-30s ${Y}WARN${NC}  (uncommitted changes)\n" "git:clean"
fi

# ─── summary ────────────────────────────────────────────────────────────────
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
WARN_COUNT=0
FAILED_GATES=()

for gate in "${!RESULTS[@]}"; do
    case "${RESULTS[$gate]}" in
        PASS) ((PASS_COUNT++)) ;;
        FAIL) ((FAIL_COUNT++)); FAILED_GATES+=("$gate") ;;
        SKIP) ((SKIP_COUNT++)) ;;
        WARN) ((WARN_COUNT++)) ;;
    esac
done

if [ "$JSON_OUTPUT" -eq 1 ]; then
    # JSON output
    echo "{"
    echo "  \"summary\": {"
    echo "    \"pass\": $PASS_COUNT,"
    echo "    \"fail\": $FAIL_COUNT,"
    echo "    \"skip\": $SKIP_COUNT,"
    echo "    \"warn\": $WARN_COUNT"
    echo "  },"
    echo "  \"gates\": {"
    first=1
    for gate in "${!RESULTS[@]}"; do
        if [ $first -eq 0 ]; then
            echo ","
        fi
        first=0
        # Escape for JSON; this is naive but sufficient for known gate output
        tail_escaped=$(echo "${OUTPUTS_TAIL[$gate]}" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n' | sed 's/\\n$//')
        printf '    "%s": {"result": "%s", "duration_s": %d, "tail": "%s"}' \
            "$gate" "${RESULTS[$gate]}" "${DURATIONS[$gate]}" "$tail_escaped"
    done
    echo
    echo "  }"
    echo "}"
else
    echo
    echo "─────────────────────────────────────────────────────────────"
    printf "Summary: ${G}%d pass${NC}, ${R}%d fail${NC}, ${Y}%d skip${NC}, ${Y}%d warn${NC}\n" \
        "$PASS_COUNT" "$FAIL_COUNT" "$SKIP_COUNT" "$WARN_COUNT"

    if [ $FAIL_COUNT -gt 0 ]; then
        echo
        echo -e "${R}Failed gates:${NC}"
        for gate in "${FAILED_GATES[@]}"; do
            echo
            echo -e "  ${R}✗ $gate${NC}"
            echo "${OUTPUTS_TAIL[$gate]}" | sed 's/^/      /'
        done
    fi
fi

# ─── exit ───────────────────────────────────────────────────────────────────
if [ $FAIL_COUNT -gt 0 ]; then
    exit 1
fi
exit 0
