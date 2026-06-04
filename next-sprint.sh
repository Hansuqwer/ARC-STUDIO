#!/usr/bin/env bash
# next-sprint.sh — runs the four post-v0.2.0-alpha follow-ups in order
# with safety rails. Run section-by-section, NOT all at once.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ─────────────────────────────────────────────────────────────────
# 0. Preflight — confirm we're on a clean main at v0.2.0-alpha
# ─────────────────────────────────────────────────────────────────
preflight() {
    git fetch --tags origin
    [ "$(git branch --show-current)" = "main" ] || {
        echo "✗ not on main"; exit 1; }
    git diff --quiet HEAD || { echo "✗ uncommitted changes"; exit 1; }
    git tag --list | grep -q "^v0.2.0-alpha$" || {
        echo "✗ v0.2.0-alpha tag missing"; exit 1; }
    git log -1 --format='%H %s' | head -1
    echo "✓ preflight clean"
}

# Helper: extract just the prompt body from a wrapper doc
extract_prompt() {
    local file="$1"
    sed -n '/^## 📋 PROMPT — copy from here ⤵$/,/^## 📋 END PROMPT ⤴$/p' "$file"
}

# ─────────────────────────────────────────────────────────────────
# 1. Housekeeping — fix check-pr.sh false positive (5 min)
# ─────────────────────────────────────────────────────────────────
housekeeping() {
    git checkout -b chore/check-pr-false-positive
    grep -n 'OPENAI_API_KEY\|ANTHROPIC_API_KEY\|env\|secret' scripts/check-pr.sh \
        | head -20
    # Open in your editor and add an exclusion for ${...} env-refs.
    # Typical pattern: -e '\$\{[A-Z_][A-Z0-9_]*\}'
    "$EDITOR" scripts/check-pr.sh
    # Verify the change actually fixes it:
    bash scripts/check-pr.sh 2>&1 | tail -5
    git diff scripts/check-pr.sh
    read -rp "Looks right? Commit? [y/N] " ok
    [ "$ok" = "y" ] || { echo "aborted"; git checkout -- scripts/check-pr.sh; exit 1; }
    git add scripts/check-pr.sh
    git commit -m "chore(check-pr): exclude \${ENV_VAR} references from secret scan

Pre-existing false positive on vendor/copilot-arena-server/docker-compose.yml
where \${OPENAI_API_KEY} (an env-var reference, not a leaked secret) tripped
the regex. Tracked in docs/handover/CHECK_PR_FALSE_POSITIVE.md."
    git checkout main
    git merge --no-ff chore/check-pr-false-positive \
        -m "chore: fix check-pr.sh env-var false positive"
    git branch -d chore/check-pr-false-positive
    echo "✓ housekeeping merged on main"
}

# ─────────────────────────────────────────────────────────────────
# 2. Theia consumer follow-up (1 day)
# ─────────────────────────────────────────────────────────────────
theia_consumer() {
    git checkout main && git pull --ff-only origin main 2>/dev/null || true
    git checkout -b feat/theia-consume-typed-events

    # Feed the spec to your CLI. The follow-up doc IS the spec.
    claude < docs/handover/THEIA_CONSUMER_FOLLOWUP.md

    # After the agent reports green, verify ourselves:
    cd python
    uv run pytest tests/test_tui_core.py tests/tui -q 2>&1 | tail -5
    cd ..
    pnpm --filter arc-extension test 2>&1 | tail -5
    pnpm build && pnpm typecheck 2>&1 | tail -3

    # Confirm the actual wire happened:
    echo "=== verifying typed events are now rendered ==="
    grep -rn "CAPABILITY_CARD_DECISION\|MCP_CALL_DECISION" \
        packages/arc-extension/src/browser/ | head -10
    # If zero hits, the agent didn't actually wire it — STOP.

    read -rp "All green and grep shows hits? Merge? [y/N] " ok
    [ "$ok" = "y" ] || { echo "aborted, branch retained"; exit 1; }
    git checkout main
    git merge --no-ff feat/theia-consume-typed-events \
        -m "feat(arc-extension): consume CAPABILITY_CARD_DECISION + MCP_CALL_DECISION

Renders capability-card decisions in AssuranceTab and a live MCP outbound
decision stream in McpWorkbenchTab. Closes the only remaining audit-trail
UX gap from the v0.2.0-alpha sprint."
    git tag -a v0.2.1-alpha -m "Theia consumer follow-up: typed event rendering"
    git push origin main v0.2.1-alpha
    echo "✓ v0.2.1-alpha tagged and pushed"
}

# ─────────────────────────────────────────────────────────────────
# 3. Token-saving research (1-2 h of agent time, no production code)
# ─────────────────────────────────────────────────────────────────
token_research() {
    git checkout main && git pull --ff-only origin main 2>/dev/null || true
    git checkout -b research/token-saving-plan

    # Extract just the prompt body — safer than feeding the whole file:
    extract_prompt TOKEN_SAVING_RESEARCH_PROMPT.md | claude

    # The agent should commit docs/research/TOKEN_SAVING_PLAN.md itself.
    # Verify:
    test -f docs/research/TOKEN_SAVING_PLAN.md || {
        echo "✗ research doc not produced"; exit 1; }
    wc -l docs/research/TOKEN_SAVING_PLAN.md  # expect 800-1500 lines
    git log -1 --format='%H %s' research/token-saving-plan

    echo ""
    echo "→ Now READ docs/research/TOKEN_SAVING_PLAN.md."
    echo "→ When you're satisfied, run the continuation prompt at the"
    echo "  BOTTOM of TOKEN_SAVING_RESEARCH_PROMPT.md to generate"
    echo "  TOKEN_SAVING_EXECUTION_PROMPT.md."
    echo ""
    echo "→ Then run section 4 below."
}

# ─────────────────────────────────────────────────────────────────
# 4. Token-saving P0 implementation (3-5 days)
# ─────────────────────────────────────────────────────────────────
token_p0() {
    git checkout main && git pull --ff-only origin main 2>/dev/null || true
    git checkout -b feat/token-saving-p0

    test -f TOKEN_SAVING_EXECUTION_PROMPT.md || {
        echo "✗ run section 3 + the continuation prompt first"; exit 1; }

    extract_prompt TOKEN_SAVING_EXECUTION_PROMPT.md | claude

    # Same gate as every previous sprint:
    cd python
    uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -5
    uv run ruff check src tests 2>&1 | tail -3
    uv run mypy src 2>&1 | tail -3
    cd ..
    pnpm build && pnpm typecheck && pnpm check:pr 2>&1 | tail -3
    bash scripts/check-banned-claims.sh \
        AGENTS.md README.md docs/roadmap.md docs/phases.md \
        docs/release/checklist.md 2>&1 | tail -3

    echo "→ If all green, merge with the same --no-ff pattern as v0.2.0-alpha."
    echo "→ Tag candidate after merge: v0.3.0-alpha (token-saving)"
}

# ─────────────────────────────────────────────────────────────────
# Dispatch — pick a section, run it, then exit.
# ─────────────────────────────────────────────────────────────────
case "${1:-help}" in
    preflight)     preflight ;;
    housekeeping)  preflight; housekeeping ;;
    theia)         preflight; theia_consumer ;;
    research)      preflight; token_research ;;
    token-p0)      preflight; token_p0 ;;
    *)
        cat <<EOF
Usage: $0 <section>

Sections (run in order, NOT all at once):
  preflight     Verify we're on clean main at v0.2.0-alpha
  housekeeping  Fix scripts/check-pr.sh false positive (5 min)
  theia         Run Theia consumer follow-up (1 day → v0.2.1-alpha)
  research      Run token-saving deep research (1-2 h agent time)
  token-p0      Implement token-saving P0 (3-5 days → v0.3.0-alpha)

After each section, you'll be at a known state on main. Pause, sanity
check the diff and the agent's report, then run the next one.
EOF
        ;;
esac
