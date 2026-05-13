#!/bin/bash
# Environment Check Script
# Verifies all required dependencies are installed

set -e

echo "=================================================="
echo "ARC Studio Environment Check"
echo "=================================================="
echo ""

# Check Node.js
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js: $NODE_VERSION"
else
    echo "❌ Node.js not found"
    exit 1
fi

# Check pnpm
echo "Checking pnpm..."
if command -v pnpm &> /dev/null; then
    PNPM_VERSION=$(pnpm --version)
    echo "✅ pnpm: $PNPM_VERSION"
else
    echo "❌ pnpm not found"
    echo "Install with: npm install -g pnpm"
    exit 1
fi

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python: $PYTHON_VERSION"
else
    echo "❌ Python 3 not found"
    exit 1
fi

# Check uv
echo "Checking uv..."
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    echo "✅ uv: $UV_VERSION"
else
    echo "⚠️  uv not found (optional but recommended)"
    echo "Install with: pip install uv"
fi

# Check git
echo "Checking git..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    echo "✅ git: $GIT_VERSION"
else
    echo "❌ git not found"
    exit 1
fi

# Check SwarmGraph
echo "Checking SwarmGraph..."
if [ -f "./swarmgraph" ]; then
    echo "✅ SwarmGraph executable found"
else
    echo "⚠️  SwarmGraph executable not found in current directory"
fi

echo ""
echo "=================================================="
echo "Environment Check Complete"
echo "=================================================="
echo ""
echo "All required dependencies are installed."
echo "Run 'bash scripts/bootstrap-dev.sh' to set up the project."
