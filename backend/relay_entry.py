"""中继服务独立入口 — FastAPI 中继 + 前端静态文件托管。"""
from __future__ import annotations

import os
import sys

import uvicorn
from fastapi.staticfiles import StaticFiles

# 确保能找到 sustech_rag 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sustech_rag.relay.server import create_relay_app

app = create_relay_app()

# 托管前端静态文件（dist 目录）
_static_dir = os.environ.get(
    "RELAY_STATIC_DIR",
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"),
)
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
    print(f"[relay] serving static files from {_static_dir}", flush=True)


def main() -> None:
    host = os.environ.get("RELAY_HOST", "0.0.0.0")
    port = int(os.environ.get("RELAY_PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
