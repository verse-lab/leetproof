#!/bin/bash
set -euo pipefail

# =============================================================================
# LLoom Setup Script
# Idempotent — safe to re-run. Each step checks if already done.
#
# This handles everything from a fresh clone:
#   1. System deps + uv + Python deps
#   2. elan + Lean toolchain
#   3. Git submodules + Lean project build
#   4. Search data + embedding models (via cli.py setup)
#   5. .env file
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LEAN_VERSION="v4.24.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "\n${BLUE}==> $1${NC}"; }
ok()   { echo -e "${GREEN}    OK: $1${NC}"; }
warn() { echo -e "${YELLOW}    WARN: $1${NC}"; }
err()  { echo -e "${RED}    ERROR: $1${NC}"; }

# =============================================================================
# 1. Check system dependencies
# =============================================================================
step "Checking system dependencies"

for cmd in git curl; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd found"
    else
        err "$cmd not found. Please install it first."
        exit 1
    fi
done

# =============================================================================
# 2. Install uv (Python package manager)
# =============================================================================
step "Checking uv"

if command -v uv &>/dev/null; then
    ok "uv found ($(uv --version))"
else
    echo "    Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    ok "uv installed ($(uv --version))"
fi

# =============================================================================
# 3. Install Python dependencies
# =============================================================================
step "Installing Python dependencies"

if [ -d ".venv" ] && uv run python -c "import langchain" &>/dev/null; then
    ok "Python dependencies already installed"
else
    echo "    Running uv sync..."
    uv sync
    ok "Python dependencies installed"
fi

# =============================================================================
# 4. Install elan + Lean toolchain
# =============================================================================
step "Checking elan and Lean"

if command -v elan &>/dev/null; then
    ok "elan found ($(elan --version 2>/dev/null | head -1))"
else
    echo "    Installing elan (Lean version manager)..."
    curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y --default-toolchain "leanprover/lean4:${LEAN_VERSION}"
    export PATH="$HOME/.elan/bin:$PATH"
    ok "elan installed"
fi

if lean --version 2>/dev/null | grep -q "${LEAN_VERSION}"; then
    ok "Lean ${LEAN_VERSION} available"
else
    echo "    Installing Lean ${LEAN_VERSION} toolchain..."
    elan toolchain install "leanprover/lean4:${LEAN_VERSION}"
    ok "Lean ${LEAN_VERSION} installed"
fi

# =============================================================================
# 5. Initialize git submodules (llmgen-experiments/)
# =============================================================================
step "Checking git submodules"

LEAN_PROJECT_DIR="llmgen-experiments"

if [ -f "$LEAN_PROJECT_DIR/lakefile.lean" ] || [ -f "$LEAN_PROJECT_DIR/lakefile.toml" ]; then
    ok "$LEAN_PROJECT_DIR/ submodule present"
else
    echo "    Initializing git submodules..."
    git submodule update --init --recursive
    if [ -f "$LEAN_PROJECT_DIR/lakefile.lean" ] || [ -f "$LEAN_PROJECT_DIR/lakefile.toml" ]; then
        ok "$LEAN_PROJECT_DIR/ submodule initialized"
    else
        err "$LEAN_PROJECT_DIR/lakefile.{lean|toml} not found after submodule init"
        exit 1
    fi
fi

# =============================================================================
# 6. Build Lean project
# =============================================================================
step "Building Lean project ($LEAN_PROJECT_DIR/)"

if [ -d "$LEAN_PROJECT_DIR/.lake/build" ] && [ -d "$LEAN_PROJECT_DIR/.lake/packages" ]; then
    ok "Lean project already built"
else
    echo "    Fetching Mathlib cache (avoids compiling from source)..."
    (cd "$LEAN_PROJECT_DIR" && lake exe cache get)
    echo "    Building Lean project (may take 15-30 minutes on first run)..."
    (cd "$LEAN_PROJECT_DIR" && lake build)
    ok "Lean project built"
fi

# =============================================================================
# 7. Setup search data + embedding models
# =============================================================================
step "Setting up search tools and models"

echo "    This downloads Loogle (~100MB), LeanExplore (~8GB), and BGE model (~400MB)"
uv run python cli.py setup

# =============================================================================
# 8. Create .env file
# =============================================================================
step "Checking .env file"

if [ -f ".env" ]; then
    ok ".env file exists"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        ok "Created .env from .env.example"
        warn "Edit .env and add your API key(s) before running the pipeline"
    else
        warn "No .env.example found, skipping"
    fi
fi

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your LLM provider API key"
echo "  2. Run the pipeline:"
echo "     uv run lloom-agent pipeline \\"
echo "       --project llmgen-experiments \\"
echo "       --input-file <problem.txt> \\"
echo "       --output-file llmgen-experiments/<output.lean> \\"
echo "       --provider anthropic --model claude-sonnet-4-5-20250929"
echo ""
echo "  Or build the binary:"
echo "     make build"
echo "     ./dist/lloom-agent --help"
