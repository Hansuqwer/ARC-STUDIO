#!/bin/bash
# Bootstrap Development Environment
# Sets up the project for development

set -e

echo "=================================================="
echo "ARC Studio Bootstrap"
echo "=================================================="
echo ""

# Check environment first
echo "Running environment check..."
bash scripts/check-env.sh
echo ""

# Install Node dependencies
echo "Installing Node.js dependencies..."
pnpm install
echo "✅ Node.js dependencies installed"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
cd python
if command -v uv &> /dev/null; then
    uv pip install -e ".[dev]"
else
    pip install -e ".[dev]"
fi
cd ..
echo "✅ Python dependencies installed"
echo ""

# Build packages
echo "Building packages..."
pnpm run build
echo "✅ Packages built"
echo ""

echo "=================================================="
echo "Bootstrap Complete"
echo "=================================================="
echo ""
echo "Development environment is ready!"
echo ""
echo "Available commands:"
echo "  pnpm start:browser  - Start browser application"
echo "  pnpm start:electron - Start Electron application"
echo "  pnpm test          - Run tests"
echo "  pnpm build         - Build all packages"
echo ""
