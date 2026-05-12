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

if git grep -n 'swarmgraph-stub.sh' -- \
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
  ':(exclude)examples/**' \
  ':(exclude)scripts/check-pr.sh'; then
  echo "ERROR: Product code contains potential secret material."
  exit 1
fi

if git grep -nE '"arc-[^"]+"[[:space:]]*:[[:space:]]*"(file:|link:|[0-9^~])' -- \
  'applications/**/package.json' \
  'theia-extensions/**/package.json' \
  'packages/**/package.json'; then
  echo "ERROR: ARC local package dependencies must use workspace:* references."
  exit 1
fi

echo "PR hygiene check passed."
