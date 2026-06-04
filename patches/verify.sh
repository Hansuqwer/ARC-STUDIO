#!/usr/bin/env bash
# verify.sh — apply all patches and verify locally
set -euo pipefail

cd "$(dirname "$0")/.."
echo "=== Applying post-merge wiring patches ==="
for p in patches/post-merge/*.patch; do
    [ -f "$p" ] || continue
    echo "==> $p"
    git apply --check --whitespace=nowarn "$p"
    git apply --whitespace=nowarn "$p"
done

echo "=== Applying UX patches in phase order ==="
for phase in p0-polish p1-modes-approvals p2-components-ia p3-themes-a11y; do
    dir="patches/ux/$phase"
    [ -d "$dir" ] || continue
    for p in "$dir"/*.patch; do
        [ -f "$p" ] || continue
        echo "==> $p"
        git apply --check --whitespace=nowarn "$p"
        git apply --whitespace=nowarn "$p"
    done
done

echo "=== Verifying ==="
export PATH="$HOME/.local/bin:$PATH"
cd python
uv sync --all-extras --dev
uv run ruff check src/agent_runtime_cockpit/tui src/agent_runtime_cockpit/adapters src/agent_runtime_cockpit/mcp tests/tui
uv run pytest tests/test_tui_core.py tests/tui tests/capabilities tests/mcp tests/adapters tests/security -q
echo "=== ALL GREEN ==="
