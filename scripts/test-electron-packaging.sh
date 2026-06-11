#!/usr/bin/env bash
# ─── Test: Electron Packaging Spike ─────────────────────────────────────────
set -euo pipefail

echo "=== Test: Electron Packaging Spike ==="

# 1. Verify the spike script exists and is executable
echo "--- Test 1: Spike script exists and is executable ---"
if [ -x "scripts/electron-packaging-spike.sh" ]; then
  echo "  PASS: scripts/electron-packaging-spike.sh is present and executable"
else
  echo "  FAIL: scripts/electron-packaging-spike.sh is not executable"
  ls -la scripts/electron-packaging-spike.sh
  exit 1
fi

# 2. Verify the daemon manager TypeScript source exists
echo "--- Test 2: DaemonManager source exists ---"
if [ -f "applications/electron/src/daemon-manager.ts" ]; then
  echo "  PASS: applications/electron/src/daemon-manager.ts exists"
else
  echo "  FAIL: daemon-manager.ts not found"
  exit 1
fi

# 3. Verify daemon manager compiles basic patterns
echo "--- Test 3: DaemonManager pattern check ---"
DM_SOURCE="applications/electron/src/daemon-manager.ts"
if grep -q "class DaemonManager" "${DM_SOURCE}" \
  && grep -q "start()" "${DM_SOURCE}" \
  && grep -q "stop()" "${DM_SOURCE}" \
  && grep -q "health()" "${DM_SOURCE}" \
  && grep -q "waitForReady()" "${DM_SOURCE}"; then
  echo "  PASS: DaemonManager has required methods"
else
  echo "  FAIL: DaemonManager missing required methods"
  exit 1
fi

# 4. Verify daemon manager handles dev mode and production paths
echo "--- Test 4: Dev vs production path detection ---"
if grep -q "ARC_DEV_MODE" "${DM_SOURCE}" && grep -q "process.resourcesPath" "${DM_SOURCE}"; then
  echo "  PASS: Dev and production paths distinguished"
else
  echo "  FAIL: Missing dev/production path distinction"
  exit 1
fi

# 5. Verify release config signing keys are intact
echo "--- Test 5: Release config signing keys ---"
RELEASE_CONFIG="applications/electron/electron-builder.release.yml"
for pattern in 'forceCodeSigning:\s*true' 'hardenedRuntime:\s*true' 'gatekeeperAssess:\s*false' 'entitlements:\s*"resources/entitlements\.mac\.plist"' 'entitlementsInherit:\s*"resources/entitlements\.mac\.plist"' 'afterSign:\s*"scripts/notarize\.mjs"' 'verifyUpdateCodeSignature:\s*true' 'signAndEditExecutable:\s*true' 'requestedExecutionLevel:\s*"asInvoker"'; do
  if grep -qE "${pattern}" "${RELEASE_CONFIG}"; then
    echo "  PASS: ${pattern}"
  else
    echo "  FAIL: Missing ${pattern} in ${RELEASE_CONFIG}"
    exit 1
  fi
done

# 6. Verify signing preflight exists
echo "--- Test 6: Signing preflight ---"
if [ -f "scripts/require-electron-signing.mjs" ]; then
  echo "  PASS: scripts/require-electron-signing.mjs exists"
else
  echo "  FAIL: require-electron-signing.mjs not found"
  exit 1
fi

# 7. Verify ADR-008 exists
echo "--- Test 7: ADR-008 daemon bundling plan ---"
if [ -f "docs/adr/008-daemon-bundling.md" ]; then
  echo "  PASS: docs/adr/008-daemon-bundling.md exists"
else
  echo "  FAIL: ADR-008 not found"
  exit 1
fi

# 8. Run the check-pr.sh signing validation (subset)
echo "--- Test 8: PR hygiene check (signing subset) ---"
SIGNING_PATTERNS=(
  'forceCodeSigning:\s*true'
  'hardenedRuntime:\s*true'
  'gatekeeperAssess:\s*false'
  'entitlements:\s*"resources/entitlements\.mac\.plist"'
  'entitlementsInherit:\s*"resources/entitlements\.mac\.plist"'
  'afterSign:\s*"scripts/notarize\.mjs"'
  'verifyUpdateCodeSignature:\s*true'
  'signAndEditExecutable:\s*true'
  'requestedExecutionLevel:\s*"asInvoker"'
)
for pat in "${SIGNING_PATTERNS[@]}"; do
  if ! grep -qE "$pat" "$RELEASE_CONFIG"; then
    echo "  FAIL: Release config missing: $pat"
    exit 1
  fi
done
echo "  PASS: All signing keys present in release config"

echo ""
echo "=== All electron packaging tests passed ==="
