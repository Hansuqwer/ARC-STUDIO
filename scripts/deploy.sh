#!/bin/bash
set -e

echo "=== ARC Studio Production Deployment ==="

# Build
echo "Building production bundle..."
cd packages/arc-browser-app
NODE_ENV=production pnpm build:prod

# Verify build
echo "Verifying build..."
if [ ! -d "lib/frontend" ]; then
    echo "ERROR: Build output not found"
    exit 1
fi

# Check bundle size
BUNDLE_SIZE=$(du -sm lib/frontend/ | cut -f1)
echo "Bundle size: ${BUNDLE_SIZE} MB"

if [ "$BUNDLE_SIZE" -gt 100 ]; then
    echo "WARNING: Bundle size exceeds 100 MB"
fi

echo "=== Build Complete ==="
echo "Start with: NODE_ENV=production pnpm start:prod"
