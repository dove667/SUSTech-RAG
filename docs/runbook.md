# Backend Runbook

完整操作手册，覆盖从零开始到服务上线的全流程。命令均在 `backend/` 目录下执行。

## 服务模式

后端有两种独立的服务模式，选其一启动即可：

**单机模式（`serve`）**：一条命令在本机同时运行 RAG 管线和推理服务，通过 FastAPI + SSE 对外提供 HTTP API，前端直连后端。适合本地开发和单机部署。

```
前端 → FastAPI (serve) → RetrievalEngine + LlamaCppBackend / VLLMBackend
```

**分布式模式（Relay-Worker）**：推理服务运行在本地 GPU 机器（Worker），通过 WebSocket 连接到公有云上的无模型中继（Relay），前端只访问 Relay。适合云端暴露公网、本地 GPU 做推理的场景。

```
前端 → Relay（公有云，无模型）→ WebSocket → Worker（本地 GPU）→ RetrievalEngine + LLM
```

两种模式使用相同的配置文件和知识库，推理后端（llama.cpp / vLLM）均可与任一服务模式组合使用。



## 1. 准备环境

```bash
cd backend
uv sync                    # 安装依赖（Linux 同时安装 vllm）
uv sync --extra dev        # 含测试和 lint 工具
```

## 2. 准备推理后端

**llama.cpp 后端**（默认，`configs/default.yaml`）：

```bash
uv run sustech-rag download-llama          # 安装 llama-server 到默认目录
uv run sustech-rag download-model          # 下载 embedding / reranker / GGUF
```

`download-llama` 若提示安装目录不在 PATH 中，按输出添加后再启动后端。

**vLLM 后端**（`configs/vllm.linux.yaml`）：

模型权重需提前下载并放到 `local_path` 指定的路径（通常是独立数据盘）。详见 [VLLM-LINUX-DEPLOY.md](VLLM-LINUX-DEPLOY.md)。

## 3. 检查路径

```bash
uv run sustech-rag paths [--config <yaml>]
```

输出 `data_dir`、`vector_store.persist_dir`、`configs/` 的绝对路径，用于确认配置生效。

## 4. 构建知识库

```bash
uv run sustech-rag crawl [--config <yaml>]
uv run sustech-rag preprocess [--config <yaml>]
uv run sustech-rag index [--config <yaml>]
uv run sustech-rag index --rebuild [--config <yaml>]   # 清空后重建
```

## 5. 验证端到端

```bash
uv run sustech-rag query "南科大有哪些学院？" [--config <yaml>]
```

`query` 临时启停推理服务，完成一次检索 + rerank + 生成后退出，适合冒烟测试。

## 6. 启动 API 服务

```bash
uv run sustech-rag serve [--host 0.0.0.0] [--port 8001] [--config <yaml>]
```

健康检查：

```bash
curl http://127.0.0.1:8001/api/health
```

## 7. 前端联调

```bash
cd ../frontend && npm install && npm run dev
```

前端默认把 `/api` 代理到 `127.0.0.1:8001`，访问 `http://127.0.0.1:3000`。

## 8. 分布式部署（Relay-Worker）

公有云启动 Relay（无模型，仅路由 + 前端静态托管）：

```bash
# 通过 deploy/ 脚本（在 repo root 执行）
bash deploy/start_relay.sh

# 或直接用 CLI
uv run sustech-rag relay [--host 0.0.0.0] [--port 8080]
```

GPU 机器连接 Relay：

```bash
# 先检查环境
bash deploy/setup_deps.sh          # Linux/macOS
.\deploy\setup_deps.ps1            # Windows

# 再启动 Worker
uv run sustech-rag worker --relay ws://<relay-host>:8080/ws/worker \
    [--config <yaml>] [--worker-id <id>]
```

单机调试时可以让 Worker 连回 `ws://127.0.0.1:8080/ws/worker`。

## 9. 测试与质量检查

```bash
uv run pytest
uv run ruff check .
```

索引测试依赖本地 embedding 模型，模型不存在时会跳过。

## 10. 常见故障

`llama-server binary not found`：运行 `download-llama` 并确认安装目录在 PATH 中。

`GGUF model not found`：运行 `download-model`，或把 `llm.model_path` 指向已有 GGUF 文件。

`components not ready (503)`：确认 Chroma collection 已通过 `index` 构建，reranker 和模型路径存在。

前端跨域失败：把前端 origin 加到环境变量 `SUSTECH_RAG_CORS_ORIGINS`（逗号分隔）。

vLLM 相关故障见 [VLLM-LINUX-DEPLOY.md](VLLM-LINUX-DEPLOY.md)。
