#!/usr/bin/env bash
# Mobile-package dependency vulnerability scan (R79.5 / Batch 7 T4).
#
# Best-effort scan of the mobile package trees under runtimes/mobile for known-vulnerable deps:
#   • JS packages (Expo / React Native): `pnpm audit` or `npm audit` (needs a lockfile).
#   • Flutter package: OSV-Scanner over pubspec.lock (Dart has no built-in audit).
#
# Skips cleanly (exit 0) when runtimes/mobile, the toolchains, or lockfiles are absent — runtimes/
# is gitignored, so this activates wherever the packages + tools are actually present. Fails
# (exit 1) only when a high/critical advisory is found. Override level with ARC_MOBILE_AUDIT_LEVEL.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOBILE="$ROOT/runtimes/mobile"
LEVEL="${ARC_MOBILE_AUDIT_LEVEL:-high}"
status=0
scanned=0

if [ ! -d "$MOBILE" ]; then
    echo "mobile-deps-audit: runtimes/mobile absent — skip"
    exit 0
fi

JS=""
if command -v pnpm >/dev/null 2>&1; then JS="pnpm"; elif command -v npm >/dev/null 2>&1; then JS="npm"; fi

# JS packages — audit only where a resolved lockfile exists.
while IFS= read -r pkg; do
    dir="$(dirname "$pkg")"
    if [ -z "$JS" ]; then echo "  skip $dir (no npm/pnpm)"; continue; fi
    if ! ls "$dir"/package-lock.json "$dir"/pnpm-lock.yaml "$dir"/npm-shrinkwrap.json >/dev/null 2>&1; then
        echo "  skip $dir (no lockfile)"; continue
    fi
    scanned=$((scanned + 1))
    echo "  audit ($JS, level=$LEVEL) $dir"
    if [ "$JS" = "pnpm" ]; then
        ( cd "$dir" && pnpm audit --audit-level "$LEVEL" ) || status=1
    else
        ( cd "$dir" && npm audit --audit-level="$LEVEL" ) || status=1
    fi
done < <(find "$MOBILE" -type d -name node_modules -prune -o -name package.json -print 2>/dev/null)

# Flutter — OSV-Scanner over pubspec.lock if available.
if command -v osv-scanner >/dev/null 2>&1; then
    while IFS= read -r lock; do
        scanned=$((scanned + 1))
        echo "  osv-scan $(dirname "$lock")"
        osv-scanner --lockfile="$lock" || status=1
    done < <(find "$MOBILE/flutter" -name pubspec.lock 2>/dev/null)
else
    echo "  flutter: osv-scanner not installed — skip pub audit"
fi

if [ "$scanned" -eq 0 ]; then
    echo "mobile-deps-audit: nothing to scan (no lockfiles/toolchains) — skip"
    exit 0
fi
if [ "$status" -eq 0 ]; then
    echo "mobile-deps-audit: OK (no ${LEVEL}+ advisories across $scanned package(s))"
else
    echo "mobile-deps-audit: FAILED (${LEVEL}+ advisories found)"
fi
exit "$status"
