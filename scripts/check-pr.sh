#!/usr/bin/env bash
set -euo pipefail

echo "Checking PR hygiene..."

bash scripts/check-artifacts.sh
bash scripts/check-licenses.sh

if git grep -nE 'mockFallback|MOCK_DATA|fake_success' -- \
  ':(exclude)*.md' \
  ':(exclude)docs/**' \
  ':(exclude)tests/**' \
  ':(exclude)python/tests/**' \
  ':(exclude)packages/arc-test-fixtures/**' \
  ':(exclude)applications/electron/electron-builder.smoke.yml' \
  ':(exclude)scripts/check-pr.sh'; then
  echo "ERROR: Product code contains prohibited mock/fake-success patterns."
  exit 1
fi

if git grep -nE 'MOCK_REASON|REMOVE_BEFORE' -- \
  ':(exclude)*.md' \
  ':(exclude)docs/**' \
  ':(exclude)tests/**' \
  ':(exclude)python/tests/**' \
  ':(exclude)packages/arc-test-fixtures/**' \
  ':(exclude)applications/electron/electron-builder.smoke.yml' \
  ':(exclude)scripts/check-pr.sh'; then
  echo "ERROR: Product code contains MOCK_REASON/REMOVE_BEFORE markers. Move fixture notes to docs/tests."
  exit 1
fi

if git grep -nE 'forceCodeSigning:[[:space:]]*false' -- \
  'applications/electron/electron-builder.release.yml' \
  'applications/electron/package.json'; then
  echo "ERROR: Release packaging has disabled signing."
  exit 1
fi

# Validate release config has required signing keys (mirrors require-electron-signing.mjs release_config check)
RELEASE_CONFIG='applications/electron/electron-builder.release.yml'
SIGNING_PATTERNS=(
  'forceCodeSigning:\s*true'
  'hardenedRuntime:\s*true'
  'gatekeeperAssess:\s*false'
  'verifyUpdateCodeSignature:\s*true'
  'signAndEditExecutable:\s*true'
  'requestedExecutionLevel:\s*"asInvoker"'
)
for pat in "${SIGNING_PATTERNS[@]}"; do
  if ! grep -qE "$pat" "$RELEASE_CONFIG"; then
    echo "ERROR: Release config missing required signing key: $pat"
    exit 1
  fi
done

if git grep -n 'swarmgraph-stub.sh' -- \
  ':(exclude).github/workflows/e2e.yml' \
  ':(exclude)docs/**' \
  ':(exclude)tests/e2e/**' \
  ':(exclude)scripts/start-browser-stub.mjs' \
  ':(exclude)scripts/check-pr.sh'; then
  echo "ERROR: Product code references the E2E SwarmGraph stub."
  exit 1
fi

if git grep -nE '(sk-(ant-|or-)?[A-Za-z0-9_-]{20,}|Authorization:[[:space:]]*Bearer|OPENAI_API_KEY=[^[:space:]]+|ANTHROPIC_API_KEY=[^[:space:]]+|QWEN_API_KEY=[^[:space:]]+|MOONSHOT_API_KEY=[^[:space:]]+)' -- \
  ':(exclude)*.md' \
  ':(exclude)docs/**' \
  ':(exclude)tests/**' \
  ':(exclude)python/tests/**' \
  ':(exclude)**/__tests__/**' \
  ':(exclude)**/*.test.ts' \
  ':(exclude)**/*.test.tsx' \
  ':(exclude)**/*.spec.ts' \
  ':(exclude)**/*.spec.tsx' \
  ':(exclude)python/test_security_manual.py' \
  ':(exclude)python/src/agent_runtime_cockpit/web/server.py' \
  ':(exclude)examples/**' \
  ':(exclude)runtimes/swarmgraph/**' \
  ':(exclude)scripts/check-pr.sh'; then
  echo "ERROR: Product code contains potential secret material."
  exit 1
fi

if git grep -nE '"arc-[^"]+"[[:space:]]*:[[:space:]]*"(file:|link:|[0-9^~])' -- \
  'applications/**/package.json' \
  'packages/**/package.json'; then
  echo "ERROR: ARC local package dependencies must use workspace:* references."
  exit 1
fi

# --- BEGIN: phase-3 secret scan additions ---
SECRET_PATTERNS=(
  'G4F_API_KEY[[:space:]]*=[[:space:]]*[A-Za-z0-9_\-]{16,}'
  '[A-Z0-9_]*API_KEY[[:space:]]*=[[:space:]]*[A-Za-z0-9_\-]{16,}'
  '[A-Z0-9_]*SECRET[[:space:]]*=[[:space:]]*[A-Za-z0-9_\-]{16,}'
  'AKIA[0-9A-Z]{16}'                     # AWS access key
  'ghp_[A-Za-z0-9]{36,}'                 # GitHub PAT
  'sk-[A-Za-z0-9]{20,}'                  # OpenAI / Anthropic style
)
EXCLUDE_FILES='\.env\.example|\.env\.sample|docs/history/|docs/archive/|(^|/)__tests__/|(^|/)tests?/|(^|/)fixtures?/|(^|/)examples?/|packages/arc-test-fixtures/|python/test_security_manual\.py|python/src/agent_runtime_cockpit/web/server\.py|runtimes/swarmgraph/'

for pat in "${SECRET_PATTERNS[@]}"; do
  hits=$(git ls-files | grep -vE "$EXCLUDE_FILES" | xargs grep -EnH "$pat" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "❌ Potential secret matched /$pat/:"
    echo "$hits"
    exit 1
  fi
done

# Block any tracked .env file
if git ls-files | grep -E '^(.*/)?\.env$' >/dev/null; then
  echo "❌ A .env file is tracked. Run: git rm --cached <file>"
  exit 1
fi
# --- END: phase-3 secret scan additions ---

echo "PR hygiene check passed."
