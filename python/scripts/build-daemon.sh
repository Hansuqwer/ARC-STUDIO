#!/usr/bin/env bash
# scripts/build-daemon.sh
# Phase 1 packaging spike: Build self-contained daemon binary via PyInstaller.
# Per ADR-008 Option A — this is one of three candidates to compare.
# Run from repo root: bash python/scripts/build-daemon.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_DIR="$REPO_ROOT/python"
OUTPUT_DIR="$REPO_ROOT/python/dist/daemon"

echo "=== ARC Daemon PyInstaller Build Spike ==="

# 1. Ensure PyInstaller is available
if ! uv run python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    cd "$PYTHON_DIR" && uv pip install pyinstaller
fi

# 2. Build the daemon binary
echo "Building daemon binary with PyInstaller..."
cd "$PYTHON_DIR"
uv run pyinstaller \
    --name arc-daemon \
    --onefile \
    --distpath "$OUTPUT_DIR" \
    --specpath "$OUTPUT_DIR/.spec" \
    --workpath "$OUTPUT_DIR/.build" \
    --hidden-import aiohttp \
    --hidden-import aiohttp.web \
    --hidden-import aiofiles \
    --hidden-import pydantic \
    --hidden-import typer \
    --hidden-import rich \
    --hidden-import yaml \
    --add-data "$PYTHON_DIR/src/agent_runtime_cockpit:agent_runtime_cockpit" \
    src/agent_runtime_cockpit/__daemon_main__.py

echo "=== Build complete ==="
echo "Binary at: $OUTPUT_DIR/arc-daemon"
ls -lh "$OUTPUT_DIR/arc-daemon" 2>/dev/null || ls -lh "$OUTPUT_DIR/arc-daemon.exe" 2>/dev/null || echo "(binary not found; check output)"

# 3. Verify the binary runs briefly (smoke test)
echo "Running smoke test..."
if "$OUTPUT_DIR/arc-daemon" --help 2>&1 | head -5; then
    echo "=== Smoke test passed ==="
else
    echo "=== Smoke test failed (binary may not exist or errored) ==="
fi
