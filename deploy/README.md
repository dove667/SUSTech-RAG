# deploy/

云端 Relay 和本地 Worker 的部署辅助脚本。这些脚本服务于分布式部署模式（Relay-Worker），不用于本地单机 `serve` 模式。两种模式的区别见 [docs/RUNBOOK.md](../docs/RUNBOOK.md)。

## 脚本说明

### `start_relay.sh` — 云端 Relay 入口

在应用盒（Sealos 等 PaaS）上启动中继服务。会拉起两个进程：
- `relay_entry.py`：FastAPI Relay 服务（`:3000`），无模型，仅做 WebSocket 连接管理和 SSE 转发，同时托管前端静态文件
- `tcp_proxy.py`：TCP 端口转发（`:8080` → `:3000`），用于 PaaS 平台的端口映射

用法（由 PaaS 平台调用，通常不需要手动执行）：

```bash
bash deploy/start_relay.sh
```

### `setup_deps.sh` / `setup_deps.ps1` — 本地 Worker 环境安装

在本地 GPU 机器上检查运行环境、安装依赖，完成后打印 Worker 启动命令。适用于 llama.cpp 后端（模型存放在 `backend/data/models/`）。

前提：已 clone 本仓库，并将模型文件放置到 `backend/data/models/`。

```bash
# Linux / macOS
bash deploy/setup_deps.sh

# Windows (PowerShell)
.\deploy\setup_deps.ps1
```

脚本会依次：
1. 检查 Python 3.11+（不满足时尝试自动安装）
2. 检查并安装 `uv`
3. 在 `backend/` 下执行 `uv sync`
4. 验证 GGUF 模型文件存在
5. 打印 Worker 启动命令

脚本完成后，手动执行输出的启动命令连接 Relay：

```bash
cd backend
uv run sustech-rag worker --relay wss://<relay-host>/ws/worker [--config <yaml>] [--worker-id <id>]
```

vLLM 后端的模型权重通常挂载在独立数据盘，不在本脚本的检查范围内，需手动确认路径后直接运行 `worker` 命令。
