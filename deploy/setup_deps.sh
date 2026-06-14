#!/usr/bin/env bash
# ================================================================
#  SUSTech RAG - Worker environment check & dependency setup
#  Prerequisite: repo cloned, model files placed in backend/data/models/
#  Usage:
#    bash deploy/install_worker.sh
# ================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[worker]${NC} $1"; }
err()  { echo -e "${RED}[worker]${NC} $1"; exit 1; }

WORKER_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ============================================================
# Step 1: System detection
# ============================================================
OS="$(uname -s)"
log "System: $OS $(uname -m)"

# ============================================================
# Step 2: Python
# ============================================================
PYTHON=""
for py in python3.11 python3.12 python3.13 python3; do
    if command -v $py &>/dev/null; then
        ver=$($py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        if [[ "$ver" > "3.10" ]]; then PYTHON=$py; break; fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    log "Installing Python 3.11..."
    if command -v apt-get &>/dev/null && sudo -n true 2>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq python3.11 python3.11-venv
        PYTHON=python3.11
    elif command -v brew &>/dev/null; then
        brew install python@3.11
        PYTHON=python3.11
    else
        err "Please install Python 3.11+ manually: https://www.python.org/downloads/"
    fi
fi
log "Python: $($PYTHON --version)"

# ============================================================
# Step 3: uv
# ============================================================
if ! command -v uv &>/dev/null; then
    log "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi
log "uv: $(uv --version)"

# ============================================================
# Step 4: Install dependencies
# ============================================================
cd "$WORKER_DIR/backend"
log "Installing Python dependencies..."
uv sync 2>&1 | tail -5
log "Dependencies ready."

# ============================================================
# Step 5: Check models
# ============================================================
if [[ ! -f "data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf" ]]; then
    err "Model file not found: backend/data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf
Please download the model first, then re-run this script:
  cd $WORKER_DIR/backend
  uv run sustech-rag download-model
  uv run sustech-rag download-llama"
fi
log "Model OK."

log "Environment ready. Start:"
echo "  cd $WORKER_DIR/backend"
echo "  uv run sustech-rag worker --relay wss://<relay-host>/ws/worker    # relay worker"
echo "  uv run sustech-rag serve                                         # local API server"
