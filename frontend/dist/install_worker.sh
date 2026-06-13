#!/usr/bin/env bash
# ================================================================
#  SUSTech RAG - Worker 一键安装 & 启动
#  用法:
#    curl -sSL https://urjjlhfvjzyi.sealosgzg.site/install_worker.sh | bash
#    bash install_worker.sh --relay wss://xx/ws/worker
#  环境变量: RELAY_URL, WORKER_ID
# ================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[worker]${NC} $1"; }
warn() { echo -e "${YELLOW}[worker]${NC} $1"; }
err()  { echo -e "${RED}[worker]${NC} $1"; exit 1; }

RELAY_URL="${RELAY_URL:-}"
WORKER_ID="${WORKER_ID:-}"
CONFIG_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --relay) RELAY_URL="$2"; shift 2 ;;
        --worker-id) WORKER_ID="$2"; shift 2 ;;
        --config) CONFIG_PATH="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# ============================================================
# Step 1: 系统检测
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
        err "请手动安装 Python 3.11+: https://www.python.org/downloads/"
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
# Step 4: 下载 worker 代码
# ============================================================
WORKER_DIR="${WORKER_DIR:-$HOME/sustech-rag-worker}"
if [[ ! -d "$WORKER_DIR/backend" ]]; then
    log "Downloading worker code..."
    mkdir -p "$WORKER_DIR"
    if command -v git &>/dev/null; then
        git clone --depth 1 https://github.com/dove667/SUSTech-RAG.git "$WORKER_DIR" 2>/dev/null || true
    fi
    if [[ ! -d "$WORKER_DIR/backend" ]]; then
        log "Downloading from public URL..."
        curl -LsSf -o /tmp/sustech-rag.zip \
            "https://github.com/dove667/SUSTech-RAG/archive/refs/heads/main.zip"
        unzip -qo /tmp/sustech-rag.zip -d /tmp/
        mv /tmp/SUSTech-RAG-main "$WORKER_DIR"
    fi
fi

cd "$WORKER_DIR/backend"

# ============================================================
# Step 5: 安装依赖
# ============================================================
log "Installing Python dependencies (5-15 min)..."
uv sync 2>&1 | tail -5
log "Dependencies ready."

# ============================================================
# Step 6: 模型（可选提示）
# ============================================================
if [[ ! -f "data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf" ]]; then
    warn "模型尚未下载，请运行:"
    echo "  cd $WORKER_DIR/backend"
    echo "  uv run sustech-rag download-model"
    echo "  uv run sustech-rag download-llama"
fi

# ============================================================
# Step 7: 启动
# ============================================================
if [[ -z "$RELAY_URL" ]]; then
    warn "未指定 --relay。手动启动:"
    echo "  cd $WORKER_DIR/backend"
    echo "  uv run sustech-rag worker --relay wss://xxx/ws/worker"
    exit 0
fi

log "Connecting to $RELAY_URL ..."
WORKER_ARGS="--relay $RELAY_URL"
[[ -n "$WORKER_ID" ]] && WORKER_ARGS="$WORKER_ARGS --worker-id $WORKER_ID"
[[ -n "$CONFIG_PATH" ]] && WORKER_ARGS="$WORKER_ARGS --config $CONFIG_PATH"

exec uv run sustech-rag worker $WORKER_ARGS
