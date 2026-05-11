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
  ':(exclude)scripts/check-pr.sh'; then
  echo "ERROR: Product code contains prohibited mock/fake-success patterns."
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
