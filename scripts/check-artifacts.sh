#!/bin/bash
# Check Build Artifacts
# Verifies that all packages have been built correctly

set -e

echo "=================================================="
echo "ARC Studio Artifact Check"
echo "=================================================="
echo ""

ERRORS=0

# Check arc-extension
echo "Checking arc-extension..."
if [ -d "packages/arc-extension/lib" ]; then
    echo "✅ arc-extension built"
else
    echo "❌ arc-extension not built"
    ERRORS=$((ERRORS + 1))
fi

# Check arc-browser-app
echo "Checking arc-browser-app..."
if [ -d "packages/arc-browser-app/lib" ]; then
    echo "✅ arc-browser-app built"
else
    echo "⚠️  arc-browser-app not built (run pnpm build)"
fi

# Check Python package
echo "Checking Python package..."
if [ -f "python/src/routes.py" ]; then
    echo "✅ Python backend exists"
else
    echo "❌ Python backend missing"
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All artifacts present"
    exit 0
else
    echo "❌ $ERRORS artifact(s) missing"
    exit 1
fi
