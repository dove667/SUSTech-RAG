#!/bin/bash
# ============================================================
#  SUSTech RAG - Entrypoint (Application Box)
#  :3000 = API + 前端 + Worker WS
#  :8080 → :3000 (TCP 代理)
# ============================================================
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

echo "============================================"
echo "  SUSTech RAG"
echo "  Dir: $APP_DIR"
echo "============================================"

# ---- 安装 Python 依赖（离线） ----
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[setup] installing..."
    python3 backend/get-pip.py --no-setuptools --no-wheel --break-system-packages 2>/dev/null || true
    python3 -m pip install --break-system-packages --no-index \
        --find-links="$APP_DIR/backend/relay_wheels" \
        pip setuptools wheel fastapi uvicorn websockets pyyaml pydantic pydantic-settings typer \
        2>&1 | grep -E "(Successfully|ERROR)" || true
    echo "[setup] done"
else
    echo "[setup] deps OK"
fi

# ---- 中继服务 :3000 ----
echo "[relay] :3000"
cd "$APP_DIR/backend"
export RELAY_STATIC_DIR="$APP_DIR/frontend/dist"
export RELAY_CORS_ORIGINS="*"
export RELAY_PORT=3000
export PYTHONPATH="$APP_DIR/backend/src"

python3 relay_entry.py &
RELAY_PID=$!
sleep 3

if ! kill -0 $RELAY_PID 2>/dev/null; then
    echo "[FATAL] relay failed"
    exit 1
fi

# ---- TCP 代理 :8080 → :3000 ----
echo "[proxy] :8080 → :3000"
python3 tcp_proxy.py &
PROXY_PID=$!
sleep 1

echo ""
echo "============================================"
echo "  ALL SERVICES RUNNING"
echo "  Public frontend : https://urjjlhfvjzyi.sealosgzg.site"
echo "  Worker WS       : wss://iehoxwivyjic.sealosgzg.site/ws/worker"
echo "  Internal relay  : :3000"
echo "  Internal proxy  : :8080 → :3000"
echo "============================================"

cleanup() {
    echo "[entrypoint] stopping..."
    kill $RELAY_PID $PROXY_PID 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n $RELAY_PID $PROXY_PID
cleanup
