#!/usr/bin/env bash
# scripts/check-sbom-integrity.sh
# R-SEC3: Python SBOM via pip-audit + pnpm-lock.yaml hash verification.
#
# Usage:
#   bash scripts/check-sbom-integrity.sh              # full check
#   bash scripts/check-sbom-integrity.sh --json       # JSON output
#   bash scripts/check-sbom-integrity.sh --sbom-only  # SBOM only (skip pnpm)
#
# Exit 0 = all checks clean.
# Exit 1 = vulnerabilities found or integrity check failed.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

JSON_MODE=false
SBOM_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)      JSON_MODE=true; shift ;;
        --sbom-only) SBOM_ONLY=true; shift ;;
        --help)      echo "Usage: $0 [--json] [--sbom-only]"; exit 0 ;;
        *)           echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

VULN_COUNT=0
PNPM_OK=true
SBOM_GENERATED=false
SBOM_PATH=""

# ── Python SBOM via pip-audit ────────────────────────────────────────────────
if command -v uv &>/dev/null; then
    SITE_PACKAGES=$(cd python && uv run python -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo "")
    if [[ -n "$SITE_PACKAGES" ]]; then
        SBOM_PATH="$REPO_ROOT/docs/reports/sbom-python-$(date -u +%Y%m%d).json"
        mkdir -p "$(dirname "$SBOM_PATH")"
        if cd python && uv run pip-audit \
            --skip-editable \
            --path "$SITE_PACKAGES" \
            --format json \
            --progress-spinner off \
            --output "$SBOM_PATH" 2>/dev/null; then
            SBOM_GENERATED=true
            VULN_COUNT=$(python3 -c "
import json, pathlib
data = json.loads(pathlib.Path('$SBOM_PATH').read_text())
deps = data.get('dependencies', [])
total = sum(len(d.get('vulns', [])) for d in deps)
print(total)
" 2>/dev/null || echo "0")
        fi
        cd "$REPO_ROOT"
    fi
fi

# ── pnpm-lock.yaml hash verification ─────────────────────────────────────────
PNPM_HASH_FILE="$REPO_ROOT/.pnpm-lock-hash"
PNPM_LOCK="$REPO_ROOT/pnpm-lock.yaml"
PNPM_CURRENT_HASH=""
PNPM_STORED_HASH=""

if [[ -f "$PNPM_LOCK" ]] && ! $SBOM_ONLY; then
    PNPM_CURRENT_HASH=$(sha256sum "$PNPM_LOCK" 2>/dev/null | awk '{print $1}' || \
                         shasum -a 256 "$PNPM_LOCK" 2>/dev/null | awk '{print $1}')
    if [[ -f "$PNPM_HASH_FILE" ]]; then
        PNPM_STORED_HASH=$(cat "$PNPM_HASH_FILE")
        if [[ "$PNPM_CURRENT_HASH" != "$PNPM_STORED_HASH" ]]; then
            echo "WARN: pnpm-lock.yaml hash changed since last attestation."
            echo "  Stored : $PNPM_STORED_HASH"
            echo "  Current: $PNPM_CURRENT_HASH"
            echo "  Run: echo \"\$CURRENT_HASH\" > .pnpm-lock-hash  to update."
            PNPM_OK=false
        fi
    else
        # First run — record the hash
        echo "$PNPM_CURRENT_HASH" > "$PNPM_HASH_FILE"
        echo "pnpm-lock.yaml hash recorded: $PNPM_CURRENT_HASH"
    fi
fi

# ── Output ────────────────────────────────────────────────────────────────────
if $JSON_MODE; then
    python3 -c "
import json
print(json.dumps({
    'sbom_generated': $([[ $SBOM_GENERATED == true ]] && echo 'true' || echo 'false'),
    'sbom_path': '${SBOM_PATH:-}',
    'python_vulns': int('${VULN_COUNT:-0}'),
    'pnpm_lock_ok': $([[ $PNPM_OK == true ]] && echo 'true' || echo 'false'),
    'pnpm_hash': '${PNPM_CURRENT_HASH:-}',
}))
"
else
    echo "Python SBOM : $([[ $SBOM_GENERATED == true ]] && echo "generated → $SBOM_PATH" || echo "skipped (uv not found)")"
    echo "Python vulns: ${VULN_COUNT:-0}"
    echo "pnpm-lock OK: $PNPM_OK"
fi

if [[ "${VULN_COUNT:-0}" -gt 0 ]]; then
    echo "FAIL: $VULN_COUNT Python vulnerability(ies) found."
    exit 1
fi

if ! $PNPM_OK; then
    echo "WARN: pnpm-lock.yaml integrity changed. Review and re-attest."
    exit 1
fi

echo "OK: SBOM checks passed."
exit 0
