#!/usr/bin/env bash
# ARC Studio Bootstrap Script
# Sets up the complete development environment from scratch.
# Run: bash scripts/bootstrap.sh

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}ARC Studio — Bootstrap${NC}"
echo "======================================"

# ── Check Node.js ──────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[1/5] Checking Node.js...${NC}"
NODE_VERSION=$(node --version 2>/dev/null || echo "missing")
if [[ "$NODE_VERSION" == "missing" ]]; then
    echo -e "${RED}✗ Node.js not found. Install Node.js 20+ from https://nodejs.org${NC}"
    exit 1
fi
MAJOR=${NODE_VERSION#v}; MAJOR=${MAJOR%%.*}
if [[ "$MAJOR" -lt 20 ]]; then
    echo -e "${YELLOW}⚠ Node.js $NODE_VERSION found, but Theia requires >=20. Consider upgrading.${NC}"
fi
echo -e "${GREEN}✓ Node.js $NODE_VERSION${NC}"

# ── Check pnpm ────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[2/5] Checking pnpm...${NC}"
if ! command -v pnpm &>/dev/null; then
    echo "  Installing pnpm via npm..."
    npm install -g pnpm@9 --prefix "$HOME/.local" 2>/dev/null || \
    corepack enable pnpm 2>/dev/null || \
    npm install -g pnpm@9 2>/dev/null || true
fi
PNPM_VERSION=$(pnpm --version 2>/dev/null || echo "missing")
if [[ "$PNPM_VERSION" == "missing" ]]; then
    echo -e "${RED}✗ pnpm installation failed. Try: npm install -g pnpm${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pnpm $PNPM_VERSION${NC}"

# ── Check Python / uv ─────────────────────────────────────────────────────────
echo -e "\n${BOLD}[3/5] Checking Python & uv...${NC}"
PYTHON_VERSION=$(python3 --version 2>/dev/null || echo "missing")
if [[ "$PYTHON_VERSION" == "missing" ]]; then
    echo -e "${RED}✗ Python 3.11+ required. Install from https://python.org${NC}"
    exit 1
fi
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

if ! command -v uv &>/dev/null; then
    echo "  Installing uv..."
    pip install uv --user 2>/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV_VERSION=$(uv --version 2>/dev/null || echo "missing")
if [[ "$UV_VERSION" == "missing" ]]; then
    echo -e "${YELLOW}⚠ uv not found. Using pip directly.${NC}"
    (cd python && pip install -e ".[dev]" --quiet)
else
    echo -e "${GREEN}✓ uv $UV_VERSION${NC}"
    echo "  Installing Python dependencies..."
    (cd python && uv sync --all-extras --dev 2>&1 | tail -5)
fi

# ── Install Node.js deps ───────────────────────────────────────────────────────
echo -e "\n${BOLD}[4/5] Installing Node.js dependencies...${NC}"
echo "  This may take a few minutes (Theia is large)..."
if ! pnpm install --frozen-lockfile; then
    echo -e "${YELLOW}⚠ 'pnpm install --frozen-lockfile' failed — pnpm-lock.yaml is out of sync with package.json.${NC}"
    echo -e "${YELLOW}  Falling back to a non-frozen install; commit the updated pnpm-lock.yaml afterward.${NC}"
    pnpm install
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[5/5] Bootstrap complete!${NC}"
echo ""
echo -e "${GREEN}✓ ARC Studio is ready.${NC}"
echo ""
echo "  Next steps:"
echo "    pnpm build          # Build all extensions and apps"
echo "    pnpm start:browser  # Start browser IDE on http://localhost:3000"
echo "    uv run arc --help   # Test Python CLI"
echo "    uv run arc serve    # Start Python daemon on port 7777"
echo ""
