#!/usr/bin/env bash
set -euo pipefail

# ARC Offline CI Guardrails — advisory local checks, no uploads, no provider calls.
# Intended for both local dev and CI workflows.

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

export HOME="$tmp/home"
export ARC_SANDBOX_AUDIT_DIR="$tmp/audit"
# Ensure sandbox/container/microVM gates are off
export ARC_ENABLE_CONTAINER_SANDBOX=""
export ARC_MICROVM_INTEGRATION=""
export ARC_MICROVM_EXEC_ENABLED=""

mkdir -p "$HOME" "$ARC_SANDBOX_AUDIT_DIR"

ARC_BIN="${ARC_BIN:-$(command -v arc || echo './python/.venv/bin/arc')}"

echo "::group::ARC sandbox run (seed audit)"
"$ARC_BIN" sandbox run --policy local-safe --json -- pwd > "$tmp/sandbox-run.json" 2>/dev/null || true
echo "::endgroup::"

echo "::group::ARC CI check"
"$ARC_BIN" ci check --json --private --audit-dir "$ARC_SANDBOX_AUDIT_DIR" > "$tmp/ci-check.json" 2>/dev/null || true
echo "::endgroup::"

echo "::group::ARC CI audit verify"
"$ARC_BIN" ci verify-audit --json --audit-dir "$ARC_SANDBOX_AUDIT_DIR" > "$tmp/ci-audit.json" 2>/dev/null || true
echo "::endgroup::"

echo "::group::ARC CI summary"
"$ARC_BIN" ci summary --format markdown --audit-dir "$ARC_SANDBOX_AUDIT_DIR" > "$tmp/ci-summary.md" 2>/dev/null || true

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat "$tmp/ci-summary.md" >> "$GITHUB_STEP_SUMMARY"
fi
echo "::endgroup::"
