#!/usr/bin/env bash
set -euo pipefail

echo "==> 1. Remove leaked secret + debris"
git rm --cached -f .env 2>/dev/null || true
echo ".env" >> .gitignore
git rm -f packages/arc-extension/src/node/arc-backend-service.ts.backup 2>/dev/null || true
git rm -f packages/arc-browser-app/fix-webpack-v3.py 2>/dev/null || true
find packages/arc-browser-app -name "*.bak*" -o -name "*.backup" | xargs -r git rm -f

echo "==> 2. Remove empty Theia extension scaffolds (keep only arc-core if you prefer)"
for ext in arc-adapters arc-audit arc-context arc-event-stream arc-health \
           arc-product arc-runs arc-schemas arc-settings arc-workflows; do
  git rm -rf "theia-extensions/${ext}" 2>/dev/null || true
done

echo "==> 3. Archive redundant docs"
mkdir -p docs/history
git mv docs/FINAL_HANDOVER.md         docs/history/ 2>/dev/null || true
git mv docs/FINAL_STATUS.md           docs/history/ 2>/dev/null || true
git mv docs/HANDOFF.md                docs/history/ 2>/dev/null || true
git mv docs/KNOWLEDGE_TRANSFER.md     docs/history/ 2>/dev/null || true
git mv docs/ORCHESTRATOR_HANDOVER_PROMPT.md docs/history/ 2>/dev/null || true
git mv docs/BUG_BASH_REPORT.md        docs/history/ 2>/dev/null || true
git mv SECURITY_AUDIT_REPORT.md       docs/history/ 2>/dev/null || true

echo "==> 4. Create new files (see patch pack)"
echo "    Apply the contents of each ### block below manually or via your IDE."

echo "==> Done. Review 'git status' before committing."
