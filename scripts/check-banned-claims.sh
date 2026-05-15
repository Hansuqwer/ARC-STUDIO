#!/usr/bin/env bash
# scripts/check-banned-claims.sh
# Scans files/directories for banned product claims.
# Usage: ./scripts/check-banned-claims.sh [--fix] <file-or-dir> [...]

set -euo pipefail

FIX_MODE=false
if [[ "${1:-}" == "--fix" ]]; then
    FIX_MODE=true
    shift
fi

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [--fix] <file-or-dir> [...]"
    echo ""
    echo "Scans for banned product claims in documentation and source files."
    echo "Exit 1 if any banned claims are found."
    echo ""
    echo "Options:"
    echo "  --fix    Show suggested replacements instead of just reporting"
    exit 1
fi

BANNED_PHRASES=(
    "SwarmGraph adoption for CrewAI"
    "SwarmGraph adoption for LangGraph"
    "SwarmGraph adoption for OpenAI Agents"
    "SwarmGraph adoption for AG2"
    "SwarmGraph adoption for LlamaIndex"
    "live streaming"
    "signed audit trails"
    "signed audit chain"
    "HMAC-SHA256 audit chain in ARC"
    "AG2 support"
    "OpenAI Agents project support"
    "OpenAI Agents SDK full support"
    "LM Arena live mode"
    "Production ready"
    "multi-user"
    "tenant-isolated"
    "Combo runtime = SwarmGraph composition"
    "packages/arc-extension is not used"
    "arc-extension is not used"
    "arc-extension is dead"
    "100% stub"
    "Support for LlamaIndex"
    "SwarmGraph adoption layer"
    "HMAC audit"
)

SUGGESTIONS=(
    "Use 'SwarmGraph adoption for CrewAI (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for LangGraph (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for OpenAI Agents (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for AG2 (not yet implemented)' or add test proof"
    "Use 'SwarmGraph adoption for LlamaIndex (not yet implemented)' or add test proof"
    "Use 'SSE trace replay' instead of 'live streaming' unless endpoint delivers live events"
    "Use 'SHA-256 hash chain' instead of 'signed audit trails' unless HMAC is wired"
    "Use 'SHA-256 hash chain' instead of 'signed audit chain' unless HMAC is wired"
    "Use 'ARC hash chain (SHA-256)' — HMAC exists only in vendored SwarmGraph"
    "Use 'AG2 adapter (not registered)' until adapter is wired into registry"
    "Use 'OpenAI Agents adapter (partial, hardcoded agent)' until export target is implemented"
    "Use 'OpenAI Agents adapter (partial)' until user-supplied export target works"
    "Use 'LM Arena: stub-default with gated live mode' instead of 'live mode' as product feature"
    "Use 'pre-release v0.1.0-alpha' instead of 'Production ready'"
    "Use 'single-user, loopback-only' instead of 'multi-user' until auth is implemented"
    "Use 'single-user, loopback-only' instead of 'tenant-isolated' until isolation is implemented"
    "Use 'sequential combo execution' instead of 'SwarmGraph composition'"
    "DELETE: packages/arc-extension IS the canonical extension — this claim is false"
    "DELETE: arc-extension IS the canonical extension — this claim is false"
    "DELETE: arc-extension is actively maintained — this claim is false"
    "Use 'stub-default with gated live mode' instead of '100% stub' for LM Arena"
    "Use 'LlamaIndex: detection only' until run_workflow is implemented"
    "Use 'SwarmGraph adoption layer (planned)' or 'not yet implemented'"
    "Use 'SwarmGraph HMAC audit (vendored)' to distinguish from ARC's SHA-256 chain"
)

# ---------------------------------------------------------------------------
# Allowlisted section headers – matches under these headings are skipped.
# This prevents the script from self-flagging its own policy/reference docs.
# ---------------------------------------------------------------------------
ALLOWLISTED_SECTION_HEADERS=(
    "Do Not Overclaim"
    "Fiction List"
    "Banned Claims"
    "Banned phrases"
    "Banned Phrase"
    "Claims Safe to Make"
    "Claims to Remove"
    "Safe language"
)

# Historical/planning docs are useful context, not release-facing product claims.
# Keep public release checks focused on current docs unless these files are
# explicitly promoted back into the release surface.
SKIP_PATH_PATTERNS=(
    "docs/archive/"
    "docs/adr/"
    "docs/CLI_IDE_GAP_ANALYSIS.md"
    "docs/PLAN_COMPLETION_AUDIT.md"
    "docs/SPIKE_SWARMGRAPH_IMPORT.md"
)

should_skip_file() {
    local file="$1"
    for pattern in "${SKIP_PATH_PATTERNS[@]}"; do
        if [[ "$file" == *"$pattern"* ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# get_skip_ranges  file
# Prints space-separated "start_line end_line" pairs for lines to skip:
#   - Lines inside fenced code blocks (```...```)
#   - Lines inside allowlisted policy/reference sections
# ---------------------------------------------------------------------------
get_skip_ranges() {
    local file="$1"
    local ranges=""
    local current_section=""
    local section_start=0
    local section_level=0
    local line_num=0
    local in_code_block=0
    local code_start=0

    while IFS= read -r file_line; do
        line_num=$((line_num + 1))

        # Track fenced code blocks (three or more backticks)
        if [[ "$file_line" == \`\`\`* ]]; then
            if [[ $in_code_block -eq 0 ]]; then
                in_code_block=1
                code_start=$line_num
            else
                # Close code block range
                ranges="$ranges $((code_start + 1)) $((line_num - 1))"
                in_code_block=0
            fi
        fi

        # Skip lines inside code blocks for section tracking
        if [[ $in_code_block -eq 1 ]]; then
            continue
        fi

        # Match markdown headings: ##, ###, etc.
        # (Skip level-1 # headings since those also match shell comments)
        if [[ "$file_line" =~ ^(#{2,6})\ +(.+)$ ]]; then
            local heading_level=${#BASH_REMATCH[1]}
            local heading="${BASH_REMATCH[2]}"

            # If we were tracking an allowlisted section, close it only if
            # the new heading is the SAME or HIGHER level (i.e. smaller number)
            if [[ -n "$current_section" && "$heading_level" -le "$section_level" ]]; then
                ranges="$ranges $section_start $((line_num - 1))"
                current_section=""
            fi

            # Check if this heading is allowlisted
            if [[ -z "$current_section" ]]; then
                for hdr in "${ALLOWLISTED_SECTION_HEADERS[@]}"; do
                    if [[ "$heading" == *"$hdr"* ]]; then
                        current_section="$hdr"
                        section_start=$((line_num + 1))
                        section_level="$heading_level"
                        break
                    fi
                done
            fi
        fi
    done < "$file"
    # Close trailing section if any
    if [[ -n "$current_section" ]]; then
        ranges="$ranges $section_start $line_num"
    fi
    # Close trailing code block if any (unclosed at EOF)
    if [[ $in_code_block -eq 1 ]]; then
        ranges="$ranges $((code_start + 1)) $line_num"
    fi

    echo "$ranges"
}

# ---------------------------------------------------------------------------
# is_in_skip_range  file  line
# Returns 0 (true) if the given line should be skipped (inside code block
# or allowlisted section).
# ---------------------------------------------------------------------------
is_in_skip_range() {
    local file="$1"
    local line="$2"

    local ranges
    ranges=$(get_skip_ranges "$file")
    if [[ -z "$ranges" ]]; then
        return 1
    fi

    # ranges is a space-separated list of "start end start end ..." pairs
    set -- $ranges
    while [[ $# -ge 2 ]]; do
        local s=$1
        local e=$2
        shift 2
        if [[ "$line" -ge "$s" && "$line" -le "$e" ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# is_table_row  line_content
# Returns 0 if the line looks like a markdown table row.
# Table rows describing current-vs-claimed status are reference material,
# not violations — even when they mention a banned phrase to describe
# what is NOT true.
# ---------------------------------------------------------------------------
is_table_row() {
    local content="$1"
    local trimmed="${content## }"
    if [[ "$trimmed" == \|* ]]; then
        return 0
    fi
    return 1
}

TOTAL_MATCHES=0

for target in "$@"; do
    for i in "${!BANNED_PHRASES[@]}"; do
        phrase="${BANNED_PHRASES[$i]}"
        suggestion="${SUGGESTIONS[$i]}"

        matches=$(grep -rn --include="*.md" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" --include="*.yaml" --include="*.yml" -F "$phrase" "$target" 2>/dev/null || true)

        if [[ -n "$matches" ]]; then
            while IFS= read -r match_line; do
                # Parse file:line:content
                file_and_line=$(echo "$match_line" | cut -d: -f1-2)
                match_file=$(echo "$match_line" | cut -d: -f1)
                match_num=$(echo "$match_line" | cut -d: -f2)
                content=$(echo "$match_line" | cut -d: -f3-)

                if should_skip_file "$match_file"; then
                    continue
                fi

                # Skip if inside a code block or allowlisted policy/reference section
                if [[ -f "$match_file" ]] && is_in_skip_range "$match_file" "$match_num"; then
                    continue
                fi

                # Skip if the line is a markdown table row (reference material)
                if is_table_row "$content"; then
                    continue
                fi

                TOTAL_MATCHES=$((TOTAL_MATCHES + 1))
                echo "BANNED: $file_and_line"
                echo "  Found: \"$phrase\""
                echo "  Context: $content"
                if [[ "$FIX_MODE" == true ]]; then
                    echo "  Suggestion: $suggestion"
                fi
                echo ""
            done <<< "$matches"
        fi
    done
done

if [[ $TOTAL_MATCHES -gt 0 ]]; then
    echo "---"
    echo "Found $TOTAL_MATCHES banned claim(s)."
    if [[ "$FIX_MODE" == true ]]; then
        echo "Re-run without --fix to see file:line locations."
    else
        echo "Re-run with --fix to see suggested replacements."
    fi
    exit 1
else
    echo "OK: No banned claims found."
    exit 0
fi
